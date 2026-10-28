-- =====================================================================
-- DATABASE: library_db
-- Advanced Database System (ADS) Mini-Project: Library Management System
-- Technologies: MySQL Server, MySQL Workbench, Python Flask
-- =====================================================================

-- Step 1: Create Database
DROP DATABASE IF EXISTS library_db;
CREATE DATABASE library_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE library_db;

-- =====================================================================
-- TABLE 1: Students
-- Stores registered college students with contact and department details
-- =====================================================================
CREATE TABLE Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(20) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_students_dept (department),
    INDEX idx_students_name (name)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE 2: Books
-- Stores book inventory, including total copies and available copies.
-- Enforces CHECK constraints to ensure inventory integrity.
-- =====================================================================
CREATE TABLE Books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    isbn VARCHAR(30) NULL,
    total_copies INT NOT NULL DEFAULT 1,
    available_copies INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_total_copies_non_neg CHECK (total_copies >= 0),
    CONSTRAINT chk_available_copies_valid CHECK (available_copies >= 0 AND available_copies <= total_copies),
    INDEX idx_books_title (title),
    INDEX idx_books_author (author),
    INDEX idx_books_category (category)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE 3: Users (Staff / Librarian Authentication)
-- Stores library staff credentials for secure dashboard access
-- =====================================================================
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'Librarian',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE 4: Book_Issues
-- Tracks the borrowing transaction between a student and a book.
-- Foreign keys enforce referential integrity (ON DELETE RESTRICT).
-- =====================================================================
CREATE TABLE Book_Issues (
    issue_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    book_id INT NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE NULL,
    status ENUM('ISSUED', 'RETURNED') NOT NULL DEFAULT 'ISSUED',
    remarks VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_issues_student FOREIGN KEY (student_id) 
        REFERENCES Students(student_id) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
    CONSTRAINT fk_issues_book FOREIGN KEY (book_id) 
        REFERENCES Books(book_id) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
    INDEX idx_issues_student (student_id),
    INDEX idx_issues_book (book_id),
    INDEX idx_issues_due_date (due_date),
    INDEX idx_issues_status (status)
) ENGINE=InnoDB;

-- =====================================================================
-- TABLE 5: Issue_Audit_Log (ADS Audit Trail Demonstration)
-- Automatically populated by Triggers to track every issue & return event
-- =====================================================================
CREATE TABLE Issue_Audit_Log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    student_id INT NOT NULL,
    book_id INT NOT NULL,
    action_type VARCHAR(20) NOT NULL, -- 'ISSUED' or 'RETURNED'
    action_details VARCHAR(255) NOT NULL,
    log_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================================
-- ADVANCED DATABASE CONCEPT: VIEWS
-- Simplifies complex multi-table queries for reporting and user interface
-- =====================================================================

-- View 1: Active issues with remaining days and overdue calculation
CREATE OR REPLACE VIEW vw_active_issues AS
SELECT 
    bi.issue_id,
    bi.student_id,
    s.name AS student_name,
    s.department,
    s.email AS student_email,
    bi.book_id,
    b.title AS book_title,
    b.author AS book_author,
    bi.issue_date,
    bi.due_date,
    DATEDIFF(CURDATE(), bi.due_date) AS overdue_days,
    CASE 
        WHEN CURDATE() > bi.due_date THEN 'OVERDUE'
        ELSE 'ACTIVE'
    END AS issue_status
FROM Book_Issues bi
INNER JOIN Students s ON bi.student_id = s.student_id
INNER JOIN Books b ON bi.book_id = b.book_id
WHERE bi.return_date IS NULL;

-- View 2: Overdue books report
CREATE OR REPLACE VIEW vw_overdue_books AS
SELECT 
    issue_id,
    student_id,
    student_name,
    department,
    student_email,
    book_id,
    book_title,
    book_author,
    issue_date,
    due_date,
    overdue_days
FROM vw_active_issues
WHERE issue_status = 'OVERDUE'
ORDER BY overdue_days DESC;

-- View 3: Student Borrowing Summary Report (Aggregations)
CREATE OR REPLACE VIEW vw_student_borrowing_summary AS
SELECT 
    s.student_id,
    s.name AS student_name,
    s.department,
    s.email,
    COUNT(bi.issue_id) AS total_borrowed,
    SUM(CASE WHEN bi.return_date IS NULL THEN 1 ELSE 0 END) AS currently_issued,
    SUM(CASE WHEN bi.return_date IS NOT NULL THEN 1 ELSE 0 END) AS total_returned
FROM Students s
LEFT JOIN Book_Issues bi ON s.student_id = bi.student_id
GROUP BY s.student_id, s.name, s.department, s.email;

-- =====================================================================
-- ADVANCED DATABASE CONCEPT: STORED PROCEDURES WITH TRANSACTIONS
-- Handles atomic inventory management and race condition prevention
-- =====================================================================

DELIMITER $$

-- Procedure 1: Atomic Book Issue Operation
DROP PROCEDURE IF EXISTS sp_issue_book$$
CREATE PROCEDURE sp_issue_book(
    IN p_student_id INT,
    IN p_book_id INT,
    IN p_due_days INT,
    OUT p_status_code VARCHAR(20),
    OUT p_status_message VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_available INT DEFAULT 0;
    DECLARE v_student_exists INT DEFAULT 0;
    DECLARE v_book_exists INT DEFAULT 0;
    DECLARE v_already_issued INT DEFAULT 0;
    DECLARE v_due_date DATE;

    -- Exit handler for SQL exceptions: automatically ROLLBACK on failure
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status_code = 'ERROR';
        SET p_status_message = 'Internal database error during book issue transaction. Changes rolled back.';
    END;

    -- Validate due days
    IF p_due_days <= 0 THEN
        SET p_due_days = 14; -- Default 14 days loan period
    END IF;
    SET v_due_date = DATE_ADD(CURDATE(), INTERVAL p_due_days DAY);

    -- Start Atomic Transaction
    START TRANSACTION;

    -- 1. Check if student exists
    SELECT COUNT(*) INTO v_student_exists FROM Students WHERE student_id = p_student_id;
    IF v_student_exists = 0 THEN
        ROLLBACK;
        SET p_status_code = 'NOT_FOUND';
        SET p_status_message = 'Student ID does not exist.';
        LEAVE proc_label;
    END IF;

    -- 2. Check if book exists and lock the row for update (Pessimistic Locking)
    SELECT COUNT(*), COALESCE(available_copies, 0) 
    INTO v_book_exists, v_available 
    FROM Books 
    WHERE book_id = p_book_id 
    FOR UPDATE;

    IF v_book_exists = 0 THEN
        ROLLBACK;
        SET p_status_code = 'NOT_FOUND';
        SET p_status_message = 'Book ID does not exist.';
        LEAVE proc_label;
    END IF;

    -- 3. Check stock availability
    IF v_available <= 0 THEN
        ROLLBACK;
        SET p_status_code = 'OUT_OF_STOCK';
        SET p_status_message = 'No available copies left for this book.';
        LEAVE proc_label;
    END IF;

    -- 4. Prevent duplicate active issue of the SAME book to the SAME student
    SELECT COUNT(*) INTO v_already_issued 
    FROM Book_Issues 
    WHERE student_id = p_student_id 
      AND book_id = p_book_id 
      AND return_date IS NULL;

    IF v_already_issued > 0 THEN
        ROLLBACK;
        SET p_status_code = 'DUPLICATE_ISSUE';
        SET p_status_message = 'Student already has an active issued copy of this book.';
        LEAVE proc_label;
    END IF;

    -- 5. Insert Book Issue record
    INSERT INTO Book_Issues (student_id, book_id, issue_date, due_date, status)
    VALUES (p_student_id, p_book_id, CURDATE(), v_due_date, 'ISSUED');

    -- 6. Atomically decrement available copies
    UPDATE Books 
    SET available_copies = available_copies - 1 
    WHERE book_id = p_book_id;

    -- 7. Commit Transaction
    COMMIT;
    SET p_status_code = 'SUCCESS';
    SET p_status_message = CONCAT('Book issued successfully. Due date: ', v_due_date);
END$$

-- Procedure 2: Atomic Book Return Operation
DROP PROCEDURE IF EXISTS sp_return_book$$
CREATE PROCEDURE sp_return_book(
    IN p_issue_id INT,
    OUT p_status_code VARCHAR(20),
    OUT p_status_message VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_book_id INT;
    DECLARE v_return_date DATE;
    DECLARE v_issue_exists INT DEFAULT 0;

    -- Exit handler for SQL exceptions: automatically ROLLBACK on failure
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status_code = 'ERROR';
        SET p_status_message = 'Internal database error during book return transaction. Changes rolled back.';
    END;

    -- Start Atomic Transaction
    START TRANSACTION;

    -- 1. Check if issue record exists and fetch its current return status
    SELECT COUNT(*), book_id, return_date 
    INTO v_issue_exists, v_book_id, v_return_date 
    FROM Book_Issues 
    WHERE issue_id = p_issue_id 
    GROUP BY issue_id, book_id, return_date 
    FOR UPDATE;

    IF v_issue_exists = 0 THEN
        ROLLBACK;
        SET p_status_code = 'NOT_FOUND';
        SET p_status_message = 'Issue record not found.';
        LEAVE proc_label;
    END IF;

    -- 2. Prevent returning an already returned book
    IF v_return_date IS NOT NULL THEN
        ROLLBACK;
        SET p_status_code = 'ALREADY_RETURNED';
        SET p_status_message = 'This book has already been marked as returned.';
        LEAVE proc_label;
    END IF;

    -- 3. Mark return date and status in Book_Issues
    UPDATE Book_Issues 
    SET return_date = CURDATE(), status = 'RETURNED' 
    WHERE issue_id = p_issue_id;

    -- 4. Atomically increment available copies in Books (ensuring it never exceeds total copies)
    UPDATE Books 
    SET available_copies = LEAST(total_copies, available_copies + 1) 
    WHERE book_id = v_book_id;

    -- 5. Commit Transaction
    COMMIT;
    SET p_status_code = 'SUCCESS';
    SET p_status_message = 'Book returned successfully and inventory updated.';
END$$

-- =====================================================================
-- ADVANCED DATABASE CONCEPT: DATABASE TRIGGERS
-- Auditing triggers to record issue and return events in Issue_Audit_Log
-- (Note: Inventory updates are handled atomically in Stored Procedures)
-- =====================================================================

-- Trigger 1: After Insert on Book_Issues (Log New Issue)
DROP TRIGGER IF EXISTS trg_after_issue_insert$$
CREATE TRIGGER trg_after_issue_insert
AFTER INSERT ON Book_Issues
FOR EACH ROW
BEGIN
    INSERT INTO Issue_Audit_Log (issue_id, student_id, book_id, action_type, action_details)
    VALUES (
        NEW.issue_id,
        NEW.student_id,
        NEW.book_id,
        'ISSUED',
        CONCAT('Book ID ', NEW.book_id, ' issued to Student ID ', NEW.student_id, ' due on ', NEW.due_date)
    );
END$$

-- Trigger 2: After Update on Book_Issues (Log Return)
DROP TRIGGER IF EXISTS trg_after_issue_update$$
CREATE TRIGGER trg_after_issue_update
AFTER UPDATE ON Book_Issues
FOR EACH ROW
BEGIN
    -- Log only when book transitions from unreturned to returned
    IF OLD.return_date IS NULL AND NEW.return_date IS NOT NULL THEN
        INSERT INTO Issue_Audit_Log (issue_id, student_id, book_id, action_type, action_details)
        VALUES (
            NEW.issue_id,
            NEW.student_id,
            NEW.book_id,
            'RETURNED',
            CONCAT('Book ID ', NEW.book_id, ' returned by Student ID ', NEW.student_id, ' on ', NEW.return_date)
        );
    END IF;
END$$

DELIMITER ;
