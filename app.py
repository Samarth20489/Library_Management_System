# =====================================================================
# app.py - Flask Web Application Controller
# Advanced Database System (ADS) Mini-Project: Library Management System
# =====================================================================

from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from db import execute_query, call_procedure
import os

app = Flask(__name__)
app.config.from_object(Config)

# =====================================================================
# 1. Dashboard Route (Overview & Analytics)
# =====================================================================
@app.route('/')
@app.route('/dashboard')
def dashboard():
    """
    Renders the system dashboard with aggregated statistics,
    recent activity, and overdue alerts using SQL aggregate functions and Views.
    """
    try:
        # Aggregated stats via SQL Aggregations (COUNT, SUM, AVG)
        book_stats = execute_query("""
            SELECT 
                COUNT(*) AS total_books,
                COALESCE(SUM(total_copies), 0) AS total_copies,
                COALESCE(SUM(available_copies), 0) AS available_copies,
                COALESCE(AVG(total_copies), 0) AS avg_copies
            FROM Books;
        """, fetch='one')

        student_stats = execute_query("""
            SELECT COUNT(*) AS total_students FROM Students;
        """, fetch='one')

        active_stats = execute_query("""
            SELECT COUNT(*) AS active_issues FROM vw_active_issues;
        """, fetch='one')

        overdue_stats = execute_query("""
            SELECT COUNT(*) AS overdue_count FROM vw_overdue_books;
        """, fetch='one')

        stats = {
            'total_books': book_stats['total_books'] or 0,
            'total_copies': int(book_stats['total_copies'] or 0),
            'available_copies': int(book_stats['available_copies'] or 0),
            'avg_copies': float(book_stats['avg_copies'] or 0.0),
            'total_students': student_stats['total_students'] or 0,
            'active_issues': active_stats['active_issues'] or 0,
            'overdue_count': overdue_stats['overdue_count'] or 0
        }

        # Query recent issues via Database View `vw_active_issues`
        recent_issues = execute_query("""
            SELECT issue_id, student_id, student_name, department, 
                   book_id, book_title, book_author, issue_date, 
                   due_date, overdue_days, issue_status
            FROM vw_active_issues
            ORDER BY issue_date DESC, issue_id DESC
            LIMIT 6;
        """, fetch='all')

        # Query overdue books via Database View `vw_overdue_books`
        overdue_list = execute_query("""
            SELECT issue_id, student_name, department, book_title, 
                   issue_date, due_date, overdue_days
            FROM vw_overdue_books
            ORDER BY overdue_days DESC
            LIMIT 5;
        """, fetch='all')

        return render_template('dashboard.html', 
                               stats=stats, 
                               recent_issues=recent_issues, 
                               overdue_list=overdue_list)

    except Exception as e:
        flash(f"Database error while loading dashboard: {str(e)}", "danger")
        return render_template('dashboard.html', 
                               stats={'total_books': 0, 'total_copies': 0, 'available_copies': 0, 'avg_copies': 0, 'total_students': 0, 'active_issues': 0, 'overdue_count': 0}, 
                               recent_issues=[], 
                               overdue_list=[])

# =====================================================================
# Route Stubs for Book, Student, Issue, Return, and Reports
# (These will be expanded comprehensively in Stages 7, 8, 9, 10)
# =====================================================================

# =====================================================================
# 2. Book Management Routes (CRUD Operations)
# =====================================================================

@app.route('/books')
def books():
    """Display all books with optional search filtering by title, author, category, or ID."""
    search_query = request.args.get('search', '').strip()
    try:
        if search_query:
            # Check if search term is numeric (potential book ID)
            if search_query.isdigit():
                sql = """
                    SELECT * FROM Books 
                    WHERE book_id = %s OR title LIKE %s OR author LIKE %s OR category LIKE %s
                    ORDER BY title ASC;
                """
                like_term = f"%{search_query}%"
                book_list = execute_query(sql, (int(search_query), like_term, like_term, like_term), fetch='all')
            else:
                sql = """
                    SELECT * FROM Books 
                    WHERE title LIKE %s OR author LIKE %s OR category LIKE %s
                    ORDER BY title ASC;
                """
                like_term = f"%{search_query}%"
                book_list = execute_query(sql, (like_term, like_term, like_term), fetch='all')
        else:
            book_list = execute_query("SELECT * FROM Books ORDER BY book_id ASC;", fetch='all')

        return render_template('books.html', books=book_list, search_query=search_query)
    except Exception as e:
        flash(f"Error fetching books: {str(e)}", "danger")
        return render_template('books.html', books=[], search_query=search_query)

@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    """Add a new book title to inventory."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', 'General').strip() or 'General'
        isbn = request.form.get('isbn', '').strip() or None
        total_copies_raw = request.form.get('total_copies', '1').strip()

        # Validation
        if not title or not author:
            flash("Book title and author are required fields.", "warning")
            return render_template('book_form.html', book=None)

        try:
            total_copies = int(total_copies_raw)
            if total_copies < 1:
                flash("Total copies must be at least 1.", "warning")
                return render_template('book_form.html', book=None)
        except ValueError:
            flash("Invalid quantity for total copies.", "warning")
            return render_template('book_form.html', book=None)

        try:
            # When adding a new book, available_copies initially equals total_copies
            sql = """
                INSERT INTO Books (title, author, category, isbn, total_copies, available_copies)
                VALUES (%s, %s, %s, %s, %s, %s);
            """
            execute_query(sql, (title, author, category, isbn, total_copies, total_copies), commit=True)
            flash(f"Book '{title}' added successfully to catalog with {total_copies} copies!", "success")
            return redirect(url_for('books'))
        except Exception as e:
            flash(f"Database error adding book: {str(e)}", "danger")
            return render_template('book_form.html', book=None)

    return render_template('book_form.html', book=None)

@app.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """Edit existing book details and safely adjust inventory stock."""
    # Fetch existing record
    existing_book = execute_query("SELECT * FROM Books WHERE book_id = %s;", (book_id,), fetch='one')
    if not existing_book:
        flash(f"Book #{book_id} not found.", "warning")
        return redirect(url_for('books'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', 'General').strip() or 'General'
        isbn = request.form.get('isbn', '').strip() or None
        total_copies_raw = request.form.get('total_copies', '').strip()

        if not title or not author:
            flash("Title and author cannot be empty.", "warning")
            return render_template('book_form.html', book=existing_book)

        try:
            new_total = int(total_copies_raw)
            old_total = existing_book['total_copies']
            old_available = existing_book['available_copies']
            currently_issued = old_total - old_available

            # Check constraint: Cannot reduce total below currently borrowed copies
            if new_total < currently_issued:
                flash(f"Cannot reduce total copies to {new_total}. There are currently {currently_issued} copies issued to students.", "warning")
                return render_template('book_form.html', book=existing_book)

            # Adjust available copies based on stock diff
            new_available = new_total - currently_issued

            sql = """
                UPDATE Books 
                SET title = %s, author = %s, category = %s, isbn = %s, 
                    total_copies = %s, available_copies = %s 
                WHERE book_id = %s;
            """
            execute_query(sql, (title, author, category, isbn, new_total, new_available, book_id), commit=True)
            flash(f"Book '{title}' updated successfully!", "success")
            return redirect(url_for('books'))
        except ValueError:
            flash("Total copies must be a valid number.", "warning")
            return render_template('book_form.html', book=existing_book)
        except Exception as e:
            flash(f"Database error updating book: {str(e)}", "danger")
            return render_template('book_form.html', book=existing_book)

    return render_template('book_form.html', book=existing_book)

@app.route('/books/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    """Safely delete book enforcing referential integrity constraints."""
    try:
        # Check 1: Are there active issues for this book?
        active_issue = execute_query(
            "SELECT COUNT(*) AS cnt FROM Book_Issues WHERE book_id = %s AND return_date IS NULL;",
            (book_id,), fetch='one'
        )
        if active_issue and active_issue['cnt'] > 0:
            flash(f"Cannot delete Book #{book_id}: There are {active_issue['cnt']} active copies currently issued to students. Process returns first.", "danger")
            return redirect(url_for('books'))

        # Check 2: Are there historical issues referencing this book (Referential Integrity Check)?
        history_issue = execute_query(
            "SELECT COUNT(*) AS cnt FROM Book_Issues WHERE book_id = %s;",
            (book_id,), fetch='one'
        )
        if history_issue and history_issue['cnt'] > 0:
            flash(f"Cannot delete Book #{book_id}: Borrowing history exists referencing this book (Protected by Foreign Key Constraint ON DELETE RESTRICT).", "warning")
            return redirect(url_for('books'))

        # Safe to delete
        execute_query("DELETE FROM Books WHERE book_id = %s;", (book_id,), commit=True)
        flash(f"Book #{book_id} was deleted successfully from catalog.", "success")
    except Exception as e:
        flash(f"Database error deleting book: {str(e)}", "danger")

    return redirect(url_for('books'))

# =====================================================================
# 3. Student Management Routes
# =====================================================================
@app.route('/students')
def students():
    """Display registered students with search by name, department, or ID."""
    search_query = request.args.get('search', '').strip()
    try:
        if search_query:
            if search_query.isdigit():
                sql = """
                    SELECT s.*, 
                           COUNT(CASE WHEN bi.return_date IS NULL AND bi.issue_id IS NOT NULL THEN 1 END) AS active_issues_count
                    FROM Students s
                    LEFT JOIN Book_Issues bi ON s.student_id = bi.student_id
                    WHERE s.student_id = %s OR s.name LIKE %s OR s.department LIKE %s OR s.email LIKE %s
                    GROUP BY s.student_id
                    ORDER BY s.name ASC;
                """
                like_term = f"%{search_query}%"
                student_list = execute_query(sql, (int(search_query), like_term, like_term, like_term), fetch='all')
            else:
                sql = """
                    SELECT s.*, 
                           COUNT(CASE WHEN bi.return_date IS NULL AND bi.issue_id IS NOT NULL THEN 1 END) AS active_issues_count
                    FROM Students s
                    LEFT JOIN Book_Issues bi ON s.student_id = bi.student_id
                    WHERE s.name LIKE %s OR s.department LIKE %s OR s.email LIKE %s
                    GROUP BY s.student_id
                    ORDER BY s.name ASC;
                """
                like_term = f"%{search_query}%"
                student_list = execute_query(sql, (like_term, like_term, like_term), fetch='all')
        else:
            sql = """
                SELECT s.*, 
                       COUNT(CASE WHEN bi.return_date IS NULL AND bi.issue_id IS NOT NULL THEN 1 END) AS active_issues_count
                FROM Students s
                LEFT JOIN Book_Issues bi ON s.student_id = bi.student_id
                GROUP BY s.student_id
                ORDER BY s.student_id ASC;
            """
            student_list = execute_query(sql, fetch='all')

        return render_template('students.html', students=student_list, search_query=search_query)
    except Exception as e:
        flash(f"Error fetching students: {str(e)}", "danger")
        return render_template('students.html', students=[], search_query=search_query)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    """Register a new student enforcing unique email constraint."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None

        if not name or not department or not email:
            flash("Name, department, and email are mandatory fields.", "warning")
            return render_template('student_form.html', student=None)

        try:
            # Check for duplicate email address before inserting
            existing = execute_query("SELECT student_id FROM Students WHERE email = %s;", (email,), fetch='one')
            if existing:
                flash(f"A student with email '{email}' is already registered (Student #{existing['student_id']}).", "warning")
                return render_template('student_form.html', student=None)

            execute_query(
                "INSERT INTO Students (name, department, email, phone) VALUES (%s, %s, %s, %s);",
                (name, department, email, phone), commit=True
            )
            flash(f"Student '{name}' registered successfully!", "success")
            return redirect(url_for('students'))
        except Exception as e:
            flash(f"Database error registering student: {str(e)}", "danger")
            return render_template('student_form.html', student=None)

    return render_template('student_form.html', student=None)

@app.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student profile details."""
    student = execute_query("SELECT * FROM Students WHERE student_id = %s;", (student_id,), fetch='one')
    if not student:
        flash(f"Student #{student_id} not found.", "warning")
        return redirect(url_for('students'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None

        if not name or not department or not email:
            flash("Name, department, and email cannot be empty.", "warning")
            return render_template('student_form.html', student=student)

        try:
            # Check unique email excluding current student
            dup = execute_query("SELECT student_id FROM Students WHERE email = %s AND student_id != %s;", (email, student_id), fetch='one')
            if dup:
                flash(f"Email '{email}' is already assigned to another student (#{dup['student_id']}).", "warning")
                return render_template('student_form.html', student=student)

            execute_query(
                "UPDATE Students SET name = %s, department = %s, email = %s, phone = %s WHERE student_id = %s;",
                (name, department, email, phone, student_id), commit=True
            )
            flash(f"Student '{name}' profile updated successfully!", "success")
            return redirect(url_for('students'))
        except Exception as e:
            flash(f"Database error updating student: {str(e)}", "danger")
            return render_template('student_form.html', student=student)

    return render_template('student_form.html', student=student)

@app.route('/students/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    """Safely delete student enforcing referential integrity."""
    try:
        active = execute_query(
            "SELECT COUNT(*) AS cnt FROM Book_Issues WHERE student_id = %s AND return_date IS NULL;",
            (student_id,), fetch='one'
        )
        if active and active['cnt'] > 0:
            flash(f"Cannot delete Student #{student_id}: Currently has {active['cnt']} unreturned books. Return books first.", "danger")
            return redirect(url_for('students'))

        history = execute_query(
            "SELECT COUNT(*) AS cnt FROM Book_Issues WHERE student_id = %s;",
            (student_id,), fetch='one'
        )
        if history and history['cnt'] > 0:
            flash(f"Cannot delete Student #{student_id}: Borrowing history records reference this student (Protected by Foreign Key Constraint ON DELETE RESTRICT).", "warning")
            return redirect(url_for('students'))

        execute_query("DELETE FROM Students WHERE student_id = %s;", (student_id,), commit=True)
        flash(f"Student #{student_id} was removed successfully.", "success")
    except Exception as e:
        flash(f"Database error deleting student: {str(e)}", "danger")

    return redirect(url_for('students'))

# =====================================================================
# 4. Book Issue Route (Stored Procedure sp_issue_book)
# =====================================================================
@app.route('/issue', methods=['GET', 'POST'])
def issue_book():
    """Issue a book to a registered student using atomic stored procedure."""
    if request.method == 'POST':
        student_id_raw = request.form.get('student_id', '').strip()
        book_id_raw = request.form.get('book_id', '').strip()
        due_days_raw = request.form.get('due_days', '14').strip()

        if not student_id_raw or not book_id_raw:
            flash("Please select both a student and a book to issue.", "warning")
            return redirect(url_for('issue_book'))

        try:
            student_id = int(student_id_raw)
            book_id = int(book_id_raw)
            due_days = int(due_days_raw) if due_days_raw.isdigit() else 14

            # Invoke MySQL Stored Procedure `sp_issue_book`
            result = call_procedure('sp_issue_book', [student_id, book_id, due_days, '', ''])
            status_code = result[3]
            status_message = result[4]

            if status_code == 'SUCCESS':
                flash(f"Book Issued Successfully: {status_message}", "success")
                return redirect(url_for('dashboard'))
            else:
                flash(f"Issue Failed ({status_code}): {status_message}", "warning")
                return redirect(url_for('issue_book'))
        except Exception as e:
            flash(f"Error processing book issue: {str(e)}", "danger")
            return redirect(url_for('issue_book'))

    # GET: Fetch available options for the form
    try:
        students_list = execute_query("SELECT student_id, name, department, email FROM Students ORDER BY name ASC;", fetch='all')
        books_list = execute_query("SELECT book_id, title, author, available_copies, total_copies FROM Books ORDER BY title ASC;", fetch='all')
        return render_template('issue_book.html', students=students_list, books=books_list)
    except Exception as e:
        flash(f"Database error loading issue form: {str(e)}", "danger")
        return render_template('issue_book.html', students=[], books=[])

# =====================================================================
# 5. Book Return Route (Stored Procedure sp_return_book)
# =====================================================================
@app.route('/return', methods=['GET', 'POST'])
def return_book():
    """Search and return active issued books."""
    if request.method == 'POST':
        issue_id_raw = request.form.get('issue_id', '').strip()
        if not issue_id_raw or not issue_id_raw.isdigit():
            flash("Please enter a valid numeric Issue ID.", "warning")
            return redirect(url_for('return_book'))

        try:
            issue_id = int(issue_id_raw)
            result = call_procedure('sp_return_book', [issue_id, '', ''])
            status_code = result[1]
            status_message = result[2]

            if status_code == 'SUCCESS':
                flash(f"Book Returned Successfully: {status_message}", "success")
            else:
                flash(f"Return Failed ({status_code}): {status_message}", "warning")
        except Exception as e:
            flash(f"Error processing return: {str(e)}", "danger")

        return redirect(url_for('return_book'))

    # GET: Display all active issues
    search_query = request.args.get('search', '').strip()
    try:
        if search_query:
            sql = """
                SELECT * FROM vw_active_issues 
                WHERE student_name LIKE %s OR book_title LIKE %s OR department LIKE %s
                ORDER BY due_date ASC;
            """
            like_term = f"%{search_query}%"
            active_list = execute_query(sql, (like_term, like_term, like_term), fetch='all')
        else:
            active_list = execute_query("SELECT * FROM vw_active_issues ORDER BY due_date ASC;", fetch='all')

        return render_template('return_book.html', active_issues=active_list, search_query=search_query)
    except Exception as e:
        flash(f"Error loading returns: {str(e)}", "danger")
        return render_template('return_book.html', active_issues=[], search_query=search_query)

@app.route('/return/<int:issue_id>')
def return_book_action(issue_id):
    """Direct return shortcut action from dashboard and reports."""
    try:
        result = call_procedure('sp_return_book', [issue_id, '', ''])
        status_code = result[1]
        status_message = result[2]
        if status_code == 'SUCCESS':
            flash(f"Success: {status_message}", "success")
        else:
            flash(f"Return Failed ({status_code}): {status_message}", "warning")
    except Exception as e:
        flash(f"Error processing return: {str(e)}", "danger")

    return redirect(request.referrer or url_for('dashboard'))

# =====================================================================
# 6. Reports & Advanced ADS Analytics Route
# =====================================================================
@app.route('/reports')
def reports():
    """Generates analytical reports using SQL Views, Aggregations, GROUP BY, and Triggers."""
    try:
        overdue_books = execute_query("SELECT * FROM vw_overdue_books ORDER BY overdue_days DESC;", fetch='all')
        active_issues = execute_query("SELECT * FROM vw_active_issues ORDER BY due_date ASC;", fetch='all')
        student_summary = execute_query("SELECT * FROM vw_student_borrowing_summary ORDER BY total_borrowed DESC;", fetch='all')

        dept_stats = execute_query("""
            SELECT 
                s.department,
                COUNT(DISTINCT s.student_id) AS student_count,
                COUNT(bi.issue_id) AS total_loans,
                SUM(CASE WHEN bi.return_date IS NULL AND bi.issue_id IS NOT NULL THEN 1 ELSE 0 END) AS active_loans
            FROM Students s
            LEFT JOIN Book_Issues bi ON s.student_id = bi.student_id
            GROUP BY s.department
            HAVING COUNT(DISTINCT s.student_id) >= 1
            ORDER BY total_loans DESC;
        """, fetch='all')

        audit_logs = execute_query("""
            SELECT * FROM Issue_Audit_Log 
            ORDER BY log_id DESC 
            LIMIT 50;
        """, fetch='all')

        return render_template('reports.html',
                               overdue_books=overdue_books,
                               active_issues=active_issues,
                               student_summary=student_summary,
                               dept_stats=dept_stats,
                               audit_logs=audit_logs)
    except Exception as e:
        flash(f"Error generating reports: {str(e)}", "danger")
        return render_template('reports.html', overdue_books=[], active_issues=[], student_summary=[], dept_stats=[], audit_logs=[])

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    flash("The requested page does not exist.", "warning")
    return redirect(url_for('dashboard'))

@app.errorhandler(500)
def internal_server_error(e):
    flash("Internal server error. Please verify database connection.", "danger")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Running locally in debug mode on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
