import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'civic.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name  TEXT    DEFAULT '',
        last_name   TEXT    DEFAULT '',
        dob         TEXT    DEFAULT '',
        phone       TEXT    DEFAULT '',
        username    TEXT    NOT NULL UNIQUE,
        email       TEXT    NOT NULL UNIQUE,
        password    TEXT    NOT NULL,
        is_admin    INTEGER DEFAULT 0,
        created_at  TEXT    DEFAULT (datetime('now','localtime'))
    )
''')

    # Complaints table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            complaint_text TEXT    NOT NULL,
            category       TEXT    DEFAULT 'General',
            priority       TEXT    DEFAULT 'Medium',
            status         TEXT    DEFAULT 'Pending',
            location       TEXT    DEFAULT '',
            image_path     TEXT    DEFAULT '',
            is_duplicate   INTEGER DEFAULT 0,
            created_at     TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Status history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            old_status   TEXT    NOT NULL,
            new_status   TEXT    NOT NULL,
            changed_by   INTEGER NOT NULL,
            changed_at   TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (changed_by)   REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def create_admin():
    from werkzeug.security import generate_password_hash
    conn = get_db()
    cursor = conn.cursor()
    existing = cursor.execute(
        'SELECT id FROM users WHERE username = ?', ('admin',)
    ).fetchone()
    if not existing:
        cursor.execute('''
            INSERT INTO users (username, email, password, is_admin)
            VALUES (?, ?, ?, 1)
        ''', ('admin', 'admin@civic.com',
              generate_password_hash('admin123')))
        conn.commit()
        print("Admin user created! username: admin  password: admin123")
    else:
        print("Admin already exists.")
    conn.close()

if __name__ == '__main__':
    init_db()
    create_admin()