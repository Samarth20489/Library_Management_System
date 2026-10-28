-- =====================================================================
-- SAMPLE DATA: library_db
-- Advanced Database System (ADS) Mini-Project: Library Management System
-- Provides realistic data for college practical demo & viva evaluation
-- =====================================================================

USE library_db;

-- Clear previous sample data in reverse dependency order
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE Issue_Audit_Log;
TRUNCATE TABLE Book_Issues;
TRUNCATE TABLE Books;
TRUNCATE TABLE Students;
TRUNCATE TABLE Users;
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- 1. Insert Default Staff / Librarian Users
-- Password for 'admin' is 'admin123' (hashed using Werkzeug scrypt)
-- =====================================================================
INSERT INTO Users (user_id, username, password_hash, full_name, role) VALUES
(1, 'admin', 'scrypt:32768:8:1$Nb6CnfEFiTC5vXe6$0feac271716f82f3835912473d486dee3d8ee12773392bb3ac83cbf1e44a452a3f57d697d151d0f7a404ca29b86c10997878e6f14d8bef990c44112a23a30914', 'Head Librarian', 'Librarian'),
(2, 'assistant', 'scrypt:32768:8:1$Nb6CnfEFiTC5vXe6$0feac271716f82f3835912473d486dee3d8ee12773392bb3ac83cbf1e44a452a3f57d697d151d0f7a404ca29b86c10997878e6f14d8bef990c44112a23a30914', 'Library Assistant', 'Assistant');

-- =====================================================================
-- 2. Insert Registered Students
-- Cross-departmental representation: CSE, IT, ECE, ME, CE
-- =====================================================================
INSERT INTO Students (student_id, name, department, email, phone) VALUES
(1, 'Aarav Sharma', 'Computer Science & Engineering', 'aarav.sharma@college.edu', '+91 98765 43210'),
(2, 'Priya Patel', 'Information Technology', 'priya.patel@college.edu', '+91 98765 43211'),
(3, 'Rohan Verma', 'Computer Science & Engineering', 'rohan.verma@college.edu', '+91 98765 43212'),
(4, 'Sneha Iyer', 'Electronics & Communication', 'sneha.iyer@college.edu', '+91 98765 43213'),
(5, 'Ananya Sen', 'Computer Science & Engineering', 'ananya.sen@college.edu', '+91 98765 43214'),
(6, 'Rahul Deshmukh', 'Mechanical Engineering', 'rahul.deshmukh@college.edu', '+91 98765 43215'),
(7, 'Ishita Roy', 'Information Technology', 'ishita.roy@college.edu', '+91 98765 43216'),
(8, 'Vikram Malhotra', 'Civil Engineering', 'vikram.malhotra@college.edu', '+91 98765 43217'),
(9, 'Kavya Nair', 'Electronics & Communication', 'kavya.nair@college.edu', '+91 98765 43218'),
(10, 'Aditya Joshi', 'Computer Science & Engineering', 'aditya.joshi@college.edu', '+91 98765 43219');

-- =====================================================================
-- 3. Insert Books Catalog
-- Standard college reference textbooks across categories
-- Note: available_copies reflects (total_copies - active_issues)
-- =====================================================================
INSERT INTO Books (book_id, title, author, category, isbn, total_copies, available_copies) VALUES
(1, 'Database System Concepts', 'Abraham Silberschatz, Henry F. Korth', 'Database Systems', '978-0078022159', 5, 4),
(2, 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen, Charles E. Leiserson', 'Computer Science', '978-0262033848', 4, 3),
(3, 'Computer Networks', 'Andrew S. Tanenbaum, David J. Wetherall', 'Networking', '978-0132126953', 3, 1),
(4, 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Software Engineering', '978-0132350884', 3, 3),
(5, 'Operating System Concepts', 'Abraham Silberschatz, Peter B. Galvin', 'Operating Systems', '978-1118063330', 4, 2),
(6, 'Artificial Intelligence: A Modern Approach', 'Stuart Russell, Peter Norvig', 'Artificial Intelligence', '978-0136042594', 2, 1),
(7, 'Digital Logic and Computer Design', 'M. Morris Mano', 'Electronics', '978-9332542525', 3, 3),
(8, 'Higher Engineering Mathematics', 'B.S. Grewal', 'Mathematics', '978-8174091955', 6, 5),
(9, 'Python Crash Course', 'Eric Matthes', 'Programming', '978-1593279288', 1, 0), -- 0 copies available (Test Out-of-Stock)
(10, 'Design Patterns: Elements of Reusable Object-Oriented Software', 'Erich Gamma, Richard Helm', 'Software Engineering', '978-0201633610', 2, 2),
(11, 'Cloud Computing: Concepts, Technology & Architecture', 'Thomas Erl, Ricardo Puttini', 'Cloud Computing', '978-0133387520', 3, 3),
(12, 'Modern Control Engineering', 'Katsuhiko Ogata', 'Mechanical / Electronics', '978-0136156734', 2, 2);

-- =====================================================================
-- 4. Insert Book Issues (Active, Overdue, and Returned)
-- Demonstrates diverse query scenarios and view outputs
-- =====================================================================

-- Returned historical issues (return_date NOT NULL)
INSERT INTO Book_Issues (issue_id, student_id, book_id, issue_date, due_date, return_date, status, remarks) VALUES
(1, 1, 4, DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 16 DAY), DATE_SUB(CURDATE(), INTERVAL 15 DAY), 'RETURNED', 'Returned on time in pristine condition'),
(2, 2, 1, DATE_SUB(CURDATE(), INTERVAL 25 DAY), DATE_SUB(CURDATE(), INTERVAL 11 DAY), DATE_SUB(CURDATE(), INTERVAL 10 DAY), 'RETURNED', 'Returned on time'),
(3, 3, 7, DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_SUB(CURDATE(), INTERVAL 6 DAY), DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'RETURNED', 'Returned on time');

-- Active issues currently within loan period (return_date IS NULL, due_date > CURDATE())
INSERT INTO Book_Issues (issue_id, student_id, book_id, issue_date, due_date, return_date, status, remarks) VALUES
(4, 1, 1, DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_ADD(CURDATE(), INTERVAL 9 DAY), NULL, 'ISSUED', 'Regular course loan'),
(5, 2, 2, DATE_SUB(CURDATE(), INTERVAL 4 DAY), DATE_ADD(CURDATE(), INTERVAL 10 DAY), NULL, 'ISSUED', 'Project reference'),
(6, 3, 3, DATE_SUB(CURDATE(), INTERVAL 3 DAY), DATE_ADD(CURDATE(), INTERVAL 11 DAY), NULL, 'ISSUED', 'Lab preparation'),
(7, 5, 5, DATE_SUB(CURDATE(), INTERVAL 2 DAY), DATE_ADD(CURDATE(), INTERVAL 12 DAY), NULL, 'ISSUED', 'Semester exam study'),
(8, 7, 6, DATE_SUB(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 13 DAY), NULL, 'ISSUED', 'AI research work'),
(9, 8, 8, DATE_SUB(CURDATE(), INTERVAL 6 DAY), DATE_ADD(CURDATE(), INTERVAL 8 DAY), NULL, 'ISSUED', 'Tutorial practice'),
(10, 9, 9, DATE_SUB(CURDATE(), INTERVAL 7 DAY), DATE_ADD(CURDATE(), INTERVAL 7 DAY), NULL, 'ISSUED', 'Capstone project (all copies issued)');

-- Overdue issues (return_date IS NULL, due_date < CURDATE()) -> For testing overdue alerts & views!
INSERT INTO Book_Issues (issue_id, student_id, book_id, issue_date, due_date, return_date, status, remarks) VALUES
(11, 4, 3, DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_SUB(CURDATE(), INTERVAL 6 DAY), NULL, 'ISSUED', 'Overdue by 6 days'),
(12, 6, 5, DATE_SUB(CURDATE(), INTERVAL 25 DAY), DATE_SUB(CURDATE(), INTERVAL 11 DAY), NULL, 'ISSUED', 'Overdue by 11 days');

-- Fix AUTO_INCREMENT sequence pointers
ALTER TABLE Students AUTO_INCREMENT = 11;
ALTER TABLE Books AUTO_INCREMENT = 13;
ALTER TABLE Book_Issues AUTO_INCREMENT = 13;
ALTER TABLE Users AUTO_INCREMENT = 3;
