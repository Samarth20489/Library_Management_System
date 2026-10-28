# =====================================================================
# db.py - Database Connection Manager & Query Helpers
# Advanced Database System (ADS) Project: Library Management System
# Handles connection lifecycle, transactions, and stored procedure calls
# =====================================================================

import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
from config import Config

# Initialize connection pool to handle multiple concurrent requests efficiently
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="library_pool",
        pool_size=5,
        pool_reset_session=True,
        **Config.get_db_config()
    )
except Error as err:
    connection_pool = None
    # We will handle fallback on demand in get_db_connection()

def get_db_connection():
    """
    Retrieves a MySQL connection from the connection pool,
    or falls back to a direct connection if the pool is uninitialized.
    """
    global connection_pool
    try:
        if connection_pool:
            conn = connection_pool.get_connection()
            if conn.is_connected():
                return conn
        # Fallback direct connection
        return mysql.connector.connect(**Config.get_db_config())
    except Error as err:
        print(f"[DB ERROR] Failed to connect to MySQL: {err}")
        raise err

@contextmanager
def get_db_cursor(commit=False, dictionary=True):
    """
    Context manager for database cursor operations.
    Ensures safe resource cleanup, automatic rollback on exception,
    and optional explicit commit.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def execute_query(sql, params=None, fetch=None, dictionary=True, commit=False):
    """
    Executes a parameterized SQL query.
    
    :param sql: SQL statement with '%s' placeholders
    :param params: Tuple or list of parameters (prevents SQL injection)
    :param fetch: 'all' for all rows, 'one' for single row, None for INSERT/UPDATE/DELETE
    :param dictionary: If True, rows returned as dictionaries {col: val}
    :param commit: If True, commits the transaction immediately
    :return: List of dicts, single dict, or cursor info (lastrowid / rowcount)
    """
    with get_db_cursor(commit=commit, dictionary=dictionary) as (conn, cursor):
        cursor.execute(sql, params or ())
        if fetch == 'all':
            return cursor.fetchall()
        elif fetch == 'one':
            return cursor.fetchone()
        else:
            return {'lastrowid': cursor.lastrowid, 'rowcount': cursor.rowcount}

def call_procedure(proc_name, args):
    """
    Calls a MySQL Stored Procedure with IN and OUT parameters.
    
    :param proc_name: Name of stored procedure (e.g. 'sp_issue_book')
    :param args: List of arguments including placeholders for OUT parameters
    :return: Tuple containing the returned OUT parameter values
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        result_args = cursor.callproc(proc_name, args)
        conn.commit()
        # Newer mysql-connector versions return a dict; normalize to list for uniform indexing
        if isinstance(result_args, dict):
            return list(result_args.values())
        return list(result_args)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def test_connection():
    """
    Diagnostics tool: verifies MySQL connection, queries schema counts,
    and prints a clear verification summary for students.
    """
    print("=" * 65)
    print("  LIBRARY MANAGEMENT SYSTEM - DATABASE CONNECTION DIAGNOSTIC")
    print("=" * 65)
    print(f"Connecting to: {Config.DB_USER}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}...")

    try:
        conn = get_db_connection()
        if conn.is_connected():
            db_info = conn.server_info
            print(f"[SUCCESS] Connected to MySQL Server version {db_info}")
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT DATABASE() AS current_db;")
            res = cursor.fetchone()
            print(f"[SUCCESS] Active Database: {res['current_db']}")

            # Verify table counts
            tables = ['Students', 'Books', 'Book_Issues', 'Users', 'Issue_Audit_Log']
            print("\nVerifying Table Record Counts:")
            print("-" * 45)
            for tbl in tables:
                cursor.execute(f"SELECT COUNT(*) AS cnt FROM {tbl};")
                cnt = cursor.fetchone()['cnt']
                print(f"  • {tbl.ljust(20)}: {cnt} records")
            print("-" * 45)

            # Verify views
            cursor.execute("SELECT COUNT(*) AS cnt FROM vw_active_issues;")
            active_cnt = cursor.fetchone()['cnt']
            cursor.execute("SELECT COUNT(*) AS cnt FROM vw_overdue_books;")
            overdue_cnt = cursor.fetchone()['cnt']
            print(f"  • Active Issues (View): {active_cnt} records")
            print(f"  • Overdue Issues (View): {overdue_cnt} records")
            print("-" * 45)

            cursor.close()
            conn.close()
            print("\n[READY] Database connection and schema verification PASSED!\n")
            return True
    except Error as e:
        print(f"\n[FAILED] Connection Error: {e}")
        print("\nTroubleshooting Tips:")
        print(" 1. Check your .env file: ensure DB_PASSWORD matches your MySQL root password.")
        print(" 2. Verify MySQL service is running: Run `Get-Service -Name *mysql*` in PowerShell.")
        print(" 3. Verify library_db exists: Ensure you executed schema.sql in Stage 2.\n")
        return False

if __name__ == '__main__':
    test_connection()
