import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "cinematch_db")

def get_raw_connection():
    """Connect to MySQL server without specifying a database (to allow DB creation)."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )

def init_db():
    """Ensure database and users table exist."""
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
        cursor.close()
        conn.close()

        db_conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_conn.commit()
        cursor.close()
        db_conn.close()
        return True, "DB Initialized Successfully"
    except Exception as e:
        return False, str(e)

def get_db_connection():
    """Connect directly to cinematch_db."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def user_exists(email: str) -> bool:
    email_clean = email.strip().lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email_clean,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row is not None
    except Exception:
        return False

def register_user(email: str, name: str, password_hash: str) -> tuple[bool, str]:
    email_clean = email.strip().lower()
    name_clean = name.strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, full_name, password_hash) VALUES (%s, %s, %s)",
            (email_clean, name_clean, password_hash)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "User registered successfully"
    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry
            return False, "An account with this email already exists."
        return False, f"Database error: {err.msg}"
    except Exception as e:
        return False, str(e)

def get_user(email: str) -> dict | None:
    email_clean = email.strip().lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email_clean,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row
    except Exception:
        return None
