"""
SmartBank - Database Configuration & Initialization
Connects to MySQL via XAMPP (localhost:3306)
Creates all necessary tables on first run.
"""

import MySQLdb
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def get_connection():
    """Return a fresh MySQL connection."""
    return MySQLdb.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        db=DB_NAME
    )


def init_db():
    """
    Bootstrap the database.
    Creates the smartbank schema if it doesn't exist, then creates all tables.
    Safe to call on every startup — uses IF NOT EXISTS guards.
    """
    # First connect without specifying a database to create it
    conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PASSWORD)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.close()
    conn.close()

    # Now connect with the database selected
    conn = get_connection()
    cur = conn.cursor()

    # ─── users ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            full_name     VARCHAR(120)  NOT NULL,
            email         VARCHAR(180)  NOT NULL UNIQUE,
            password_hash VARCHAR(256)  NOT NULL,
            created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    """)

    # ─── accounts ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            user_id        INT           NOT NULL,
            account_number VARCHAR(20)   NOT NULL UNIQUE,
            account_type   ENUM('savings','current') NOT NULL DEFAULT 'savings',
            balance        DECIMAL(15,2) NOT NULL DEFAULT 0.00,
            interest_rate  DECIMAL(5,2)  NOT NULL DEFAULT 3.50,
            overdraft_limit DECIMAL(15,2) NOT NULL DEFAULT 0.00,
            created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    """)

    # ─── transactions ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            account_id       INT           NOT NULL,
            type             ENUM('deposit','withdrawal','transfer_in','transfer_out') NOT NULL,
            amount           DECIMAL(15,2) NOT NULL,
            balance_after    DECIMAL(15,2) NOT NULL,
            description      VARCHAR(255),
            receiver_account VARCHAR(20),
            status           ENUM('success','failed','suspicious') NOT NULL DEFAULT 'success',
            flagged          TINYINT(1)    NOT NULL DEFAULT 0,
            created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    """)

    # ─── notifications ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT          NOT NULL,
            message    VARCHAR(512) NOT NULL,
            is_read    TINYINT(1)   NOT NULL DEFAULT 0,
            created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[SmartBank] ✅ Database initialised successfully.")
