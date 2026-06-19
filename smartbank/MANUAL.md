# SmartBank — Complete Manual
### Intelligent Banking Management System
*Flask · MySQL · scikit-learn · Bootstrap 5*

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Folder Structure](#2-folder-structure)
3. [Setup & Installation](#3-setup--installation)
4. [Application Flow](#4-application-flow)
5. [Feature Reference](#5-feature-reference)
6. [OOP Concepts Demonstrated](#6-oop-concepts-demonstrated)
7. [ML Fraud Detection](#7-ml-fraud-detection)
8. [Database Schema](#8-database-schema)
9. [API Endpoints](#9-api-endpoints)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Project Overview

SmartBank is a full-stack banking management web application built with Python/Flask. It demonstrates core software engineering principles including OOP, relational databases, REST APIs, and machine learning for fraud detection.

**Tech Stack**

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3.0 |
| Database | MySQL 8 (via XAMPP) |
| ORM/Driver | Flask-MySQLdb, mysqlclient |
| ML | scikit-learn (Random Forest) |
| Frontend | Bootstrap 5.3, Chart.js 4, Bootstrap Icons |
| Auth | Werkzeug password hashing, Flask sessions |

**Academic Concepts Covered**

- OOP: Encapsulation, Inheritance, Polymorphism (models.py)
- DBMS: Normalized schema, FK constraints, ENUM types
- ML: Supervised classification, feature engineering, model persistence
- Web: MVC-like structure, session management, CSRF-safe forms

---

## 2. Folder Structure

```
smartbank/
├── app.py                  ← Flask routes (main entry point)
├── config.py               ← DB credentials, secret key
├── database.py             ← DB connection + table creation
├── models.py               ← OOP account classes
├── requirements.txt        ← Python dependencies
│
├── ml/
│   ├── __init__.py
│   └── fraud_model.py      ← Random Forest fraud detector
│
├── templates/
│   ├── base.html           ← Navbar, flash messages, footer
│   ├── index.html          ← Landing page
│   ├── login.html          ← Login form
│   ├── register.html       ← Registration form
│   ├── dashboard.html      ← Main dashboard with charts
│   ├── deposit.html        ← Deposit form
│   ├── withdraw.html       ← Withdrawal form
│   ├── transfer.html       ← Fund transfer form
│   ├── history.html        ← Transaction history with filters
│   ├── profile.html        ← User profile editor
│   └── notifications.html  ← In-app notifications
│
├── static/
│   ├── css/style.css       ← Custom design system
│   └── js/main.js          ← Theme toggle, flash auto-dismiss
│
└── exports/                ← CSV statement downloads (auto-created)
```

---

## 3. Setup & Installation

### Prerequisites
- Python 3.10 or newer
- XAMPP (for MySQL) — download at apachefriends.org
- Git (optional)

### Step-by-Step

**Step 1 — Start XAMPP MySQL**
1. Open XAMPP Control Panel
2. Click **Start** next to MySQL
3. Confirm port 3306 is active

**Step 2 — Clone / place the project**
```bash
# If you have the zip, extract it. Otherwise:
cd Desktop
mkdir smartbank && cd smartbank
# place all files here
```

**Step 3 — Create a virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

**Step 4 — Install dependencies**
```bash
pip install -r requirements.txt
```

> **Windows note:** If `mysqlclient` fails, install it via:
> `pip install mysqlclient --only-binary :all:`
> or download the wheel from [Christoph Gohlke's site](https://www.lfd.uci.edu/~gohlke/pythonlibs/).

**Step 5 — Configure the database**

Open `config.py` and verify:
```python
DB_HOST     = "localhost"
DB_USER     = "root"
DB_PASSWORD = ""          # blank for XAMPP default
DB_NAME     = "smartbank"
```

The database and all tables are created automatically on first run.

**Step 6 — Run the application**
```bash
python app.py
```

Visit: **http://127.0.0.1:5000**

The app will print:
```
[SmartBank] ✅ Database initialised successfully.
[SmartBank ML] ✅ Fraud model trained and saved.
 * Running on http://0.0.0.0:5000
```

---

## 4. Application Flow

```
Browser
  │
  ▼
GET /              → Landing page (index.html)
  │
  ├── GET /register → register.html
  │   POST /register → validate → create user + account → redirect /login
  │
  ├── GET /login    → login.html
  │   POST /login   → verify hash → set session → redirect /dashboard
  │
  └── (logged in) ──────────────────────────────────────────────────────┐
                                                                        │
  GET  /dashboard   → fetch account + stats + chart data → dashboard.html
  GET  /deposit     → deposit.html
  POST /deposit     → validate → fraud_check → UPDATE balance → INSERT tx
  GET  /withdraw    → withdraw.html
  POST /withdraw    → validate (overdraft rules) → fraud_check → UPDATE balance
  GET  /transfer    → transfer.html
  POST /transfer    → validate → fraud_check → debit sender + credit receiver
  GET  /history     → filter params → SELECT transactions → history.html
  GET  /export/csv  → stream CSV file download
  GET  /profile     → profile.html
  POST /profile     → UPDATE user name/password
  GET  /notifications → mark all read → notifications.html
  GET  /api/balance → JSON {balance: float}   (AJAX polling)
  GET  /logout      → session.clear() → redirect /login
```

### Session lifecycle

| Event | Session |
|---|---|
| Successful login | `user_id`, `user_name` set; `permanent=True` |
| Session timeout | 2 hours (configurable in app.py) |
| Logout | `session.clear()` |
| Protected routes | `@login_required` decorator — redirects to /login |

---

## 5. Feature Reference

### Registration
- Collects: full name, email, password, account type (savings/current)
- Password hashed with `werkzeug.security.generate_password_hash` (PBKDF2-HMAC-SHA256)
- Unique 12-digit account number generated: `SB` + 10 random digits
- Default balance: ₹0.00
- Welcome notification sent automatically

### Login
- Email + password checked against hash
- Session permanent for 2 hours
- Wrong credentials: generic "Invalid email or password" (no enumeration)

### Dashboard
- Shows current balance, total deposits, total withdrawals, account number
- Monthly bar chart (last 6 months) + doughnut chart
- Recent 5 transactions
- Live balance polling every 30 seconds via `/api/balance`

### Deposit
- Any positive amount
- Fraud check runs; suspicious deposits are flagged (status = `suspicious`, flagged = 1)
- Notification generated

### Withdrawal
- **Savings accounts**: cannot exceed current balance
- **Current accounts**: can overdraw up to `overdraft_limit` (₹10,000 default)
- Fraud check applies

### Transfer
- Sends between any two SmartBank accounts
- Validates receiver exists and is not the sender
- Atomic: debit sender + credit receiver in same transaction
- Both parties receive a notification
- Fraud check on sender's transaction

### Transaction History
- Filters: keyword search, type, date range
- Shows: type, amount, balance after, description, status (success/suspicious)
- Export to CSV via `/export/csv`

### Profile
- Edit display name
- Change password (min 8 chars)
- Email is immutable

### Notifications
- Auto-generated for: account creation, deposits, withdrawals, transfers received
- Bell icon shows unread count
- All marked read when page is visited

### Dark / Light Mode
- Toggle in navbar
- Preference saved to `localStorage`

---

## 6. OOP Concepts Demonstrated

### `models.py` Class Hierarchy

```
Account  (base class)
├── SavingsAccount   (Inheritance)
└── CurrentAccount   (Inheritance + Polymorphism)
```

**Encapsulation**
- `_balance` is a private attribute (name-mangled)
- External code reads balance via `get_balance()` only
- `_record_transaction()` is a private helper

**Inheritance**
- `SavingsAccount` and `CurrentAccount` both inherit `deposit()`, `transfer()`, `display_details()` from `Account`
- Each adds its own methods: `SavingsAccount.calculate_interest()`, `SavingsAccount.apply_interest()`

**Polymorphism**
- Both subclasses override `withdraw()` with different rules:
  - `Account.withdraw()` — strict: balance must cover amount
  - `CurrentAccount.withdraw()` — allows overdraft up to `overdraft_limit`
- Calling `account.withdraw(amount)` triggers the correct version at runtime

**Factory Pattern**
- `account_factory(account_type, ...)` returns the correct subclass instance without the caller knowing the concrete type

---

## 7. ML Fraud Detection

**File:** `ml/fraud_model.py`

**Algorithm:** Random Forest Classifier (100 trees)

**Features used per transaction:**

| Feature | Description |
|---|---|
| `amount` | Transaction amount (₹) |
| `hour_of_day` | Hour 0–23 when transaction occurs |
| `tx_count_last_hour` | Number of transactions by this account in the past hour |
| `avg_tx_amount` | Historical average transaction amount for this account |

**Training data:** 3,000 normal + 600 suspicious synthetic transactions  
- Normal: log-normal amounts, business hours (8–22), low frequency  
- Suspicious: very large amounts, late-night hours (0–6, 22–24), high frequency

**Threshold:** Flagged if P(suspicious) ≥ 0.55

**Model persistence:** Trained model saved as `fraud_model.pkl` + `scaler.pkl`. Re-used on subsequent starts. Delete both `.pkl` files to retrain.

**Output:**
```python
{
    "label":       "Suspicious",   # or "Normal"
    "probability": 72.4,           # percent
    "flagged":     True
}
```

**Graceful degradation:** If scikit-learn is not installed, all transactions pass as Normal (no crash).

---

## 8. Database Schema

**Database:** `smartbank` (UTF-8 MB4)

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INT PK AUTO | |
| full_name | VARCHAR(120) | |
| email | VARCHAR(180) UNIQUE | |
| password_hash | VARCHAR(256) | PBKDF2 |
| created_at | DATETIME | DEFAULT NOW() |

### `accounts`
| Column | Type | Notes |
|---|---|---|
| id | INT PK AUTO | |
| user_id | INT FK → users.id | CASCADE DELETE |
| account_number | VARCHAR(20) UNIQUE | Format: SB0000000000 |
| account_type | ENUM('savings','current') | |
| balance | DECIMAL(15,2) | |
| interest_rate | DECIMAL(5,2) | Default 3.50% |
| overdraft_limit | DECIMAL(15,2) | 0 for savings, 10000 for current |
| created_at | DATETIME | |

### `transactions`
| Column | Type | Notes |
|---|---|---|
| id | INT PK AUTO | |
| account_id | INT FK → accounts.id | CASCADE DELETE |
| type | ENUM('deposit','withdrawal','transfer_in','transfer_out') | |
| amount | DECIMAL(15,2) | |
| balance_after | DECIMAL(15,2) | Snapshot at time of tx |
| description | VARCHAR(255) | Optional |
| receiver_account | VARCHAR(20) | Transfers only |
| status | ENUM('success','failed','suspicious') | |
| flagged | TINYINT(1) | 1 = ML flagged |
| created_at | DATETIME | |

### `notifications`
| Column | Type | Notes |
|---|---|---|
| id | INT PK AUTO | |
| user_id | INT FK → users.id | CASCADE DELETE |
| message | VARCHAR(512) | |
| is_read | TINYINT(1) | 0 = unread |
| created_at | DATETIME | |

---

## 9. API Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Landing page |
| GET/POST | `/register` | No | Create account |
| GET/POST | `/login` | No | Sign in |
| GET | `/logout` | Yes | Sign out |
| GET | `/dashboard` | Yes | Main dashboard |
| GET/POST | `/deposit` | Yes | Deposit funds |
| GET/POST | `/withdraw` | Yes | Withdraw funds |
| GET/POST | `/transfer` | Yes | Transfer funds |
| GET | `/history` | Yes | Transaction history (filterable) |
| GET | `/export/csv` | Yes | Download CSV statement |
| GET/POST | `/profile` | Yes | View/edit profile |
| GET | `/notifications` | Yes | View notifications |
| GET | `/api/balance` | Yes | JSON balance (AJAX) |

---

## 10. Troubleshooting

**`mysqlclient` install fails on Windows**
```bash
pip install mysqlclient --only-binary :all:
```
If that fails, download the correct `.whl` from Gohlke's Python packages page.

**`1045 Access denied for user 'root'@'localhost'`**
Open `config.py` and set `DB_PASSWORD` to your MySQL root password (XAMPP default is blank `""`).

**`ModuleNotFoundError: No module named 'ml.fraud_model'`**
Ensure `ml/__init__.py` exists (empty file is fine). Run app from the project root directory.

**Fraud model not training / sklearn error**
```bash
pip install scikit-learn numpy pandas
```

**Port 5000 already in use**
```bash
# Change port in app.py bottom:
app.run(debug=True, host="0.0.0.0", port=5001)
```
Or kill the process using port 5000.

**Transactions show wrong balance**
The `balance_after` column is a snapshot taken at transaction time. Current balance in `accounts.balance` is always authoritative.

**Reset everything (fresh start)**
1. Stop the app
2. In phpMyAdmin: drop the `smartbank` database
3. Delete `ml/fraud_model.pkl` and `ml/scaler.pkl` if they exist
4. Restart `python app.py` — DB and model are recreated automatically

---

*SmartBank — Built with Flask · Developed for academic demonstration of OOP, DBMS, and ML concepts*
