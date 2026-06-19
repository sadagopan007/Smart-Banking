"""
SmartBank – Flask Application Entry Point
Run: python app.py
"""

import os
import csv
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from decimal import Decimal

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import SECRET_KEY, EXPORT_FOLDER
from database import init_db, get_connection
from models import account_factory
from ml.fraud_model import predict_fraud

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=2)

# Initialise database tables on startup
init_db()


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def generate_account_number() -> str:
    """Generate a unique 12-digit account number prefixed with SB."""
    digits = "".join(random.choices(string.digits, k=10))
    return f"SB{digits}"


def _add_notification(user_id: int, message: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
        (user_id, message)
    )
    conn.commit()
    cur.close()
    conn.close()


def _verify_password(user_id: int, password: str) -> bool:
    """Check the supplied password against the logged-in user's stored hash."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return False
    return check_password_hash(row[0], password)


def _get_unread_count(user_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=%s AND is_read=0",
        (user_id,)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


# ══════════════════════════════════════════════════════════════════════════════
# Context processor – inject notification count into every template
# ══════════════════════════════════════════════════════════════════════════════

@app.context_processor
def inject_globals():
    notif_count = 0
    if "user_id" in session:
        notif_count = _get_unread_count(session["user_id"])
    return {"notif_count": notif_count}


# ══════════════════════════════════════════════════════════════════════════════
# Landing
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ══════════════════════════════════════════════════════════════════════════════
# Auth
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name    = request.form.get("full_name", "").strip()
        email        = request.form.get("email", "").strip().lower()
        password     = request.form.get("password", "")
        account_type = request.form.get("account_type", "savings")

        # Basic server-side validation
        if not all([full_name, email, password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html")

        conn = get_connection()
        cur  = conn.cursor()

        # Duplicate check
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("An account with that email already exists.", "danger")
            cur.close(); conn.close()
            return render_template("register.html")

        # Create user
        pwd_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
            (full_name, email, pwd_hash)
        )
        user_id = conn.insert_id()

        # Create account
        acc_number = generate_account_number()
        # Ensure uniqueness
        while True:
            cur.execute("SELECT id FROM accounts WHERE account_number=%s", (acc_number,))
            if not cur.fetchone():
                break
            acc_number = generate_account_number()

        overdraft = 10000.00 if account_type == "current" else 0.00
        cur.execute(
            """INSERT INTO accounts
               (user_id, account_number, account_type, balance, interest_rate, overdraft_limit)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (user_id, acc_number, account_type, 0.00, 3.50, overdraft)
        )

        conn.commit()
        cur.close(); conn.close()

        _add_notification(user_id, f"Welcome to SmartBank! Your account {acc_number} is ready.")
        flash(f"Account created! Your number: {acc_number} — please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT id, full_name, password_hash FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        cur.close(); conn.close()

        if row and check_password_hash(row[2], password):
            session.permanent = True
            session["user_id"]   = row[0]
            session["user_name"] = row[1]
            flash(f"Welcome back, {row[1]}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_connection()
    cur  = conn.cursor()

    # Account info
    cur.execute(
        "SELECT id, account_number, account_type, balance, interest_rate, overdraft_limit "
        "FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    acc = cur.fetchone()
    if not acc:
        cur.close(); conn.close()
        flash("No account found.", "danger")
        return redirect(url_for("logout"))

    acc_id = acc[0]

    # Aggregate stats
    cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions "
        "WHERE account_id=%s AND type IN ('deposit','transfer_in')",
        (acc_id,)
    )
    total_deposits = float(cur.fetchone()[0])

    cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions "
        "WHERE account_id=%s AND type IN ('withdrawal','transfer_out')",
        (acc_id,)
    )
    total_withdrawals = float(cur.fetchone()[0])

    # Recent 5 transactions
    cur.execute(
        "SELECT type, amount, description, status, flagged, created_at "
        "FROM transactions WHERE account_id=%s "
        "ORDER BY created_at DESC LIMIT 5",
        (acc_id,)
    )
    recent_txs = cur.fetchall()

    # Monthly chart data (last 6 months)
    chart_labels, chart_deposits, chart_withdrawals = [], [], []
    for i in range(5, -1, -1):
        d = datetime.now() - timedelta(days=30 * i)
        label = d.strftime("%b %Y")
        chart_labels.append(label)

        cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE account_id=%s AND type IN ('deposit','transfer_in') "
            "AND YEAR(created_at)=%s AND MONTH(created_at)=%s",
            (acc_id, d.year, d.month)
        )
        chart_deposits.append(float(cur.fetchone()[0]))

        cur.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE account_id=%s AND type IN ('withdrawal','transfer_out') "
            "AND YEAR(created_at)=%s AND MONTH(created_at)=%s",
            (acc_id, d.year, d.month)
        )
        chart_withdrawals.append(float(cur.fetchone()[0]))

    cur.close(); conn.close()

    return render_template("dashboard.html",
        acc=acc,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        recent_txs=recent_txs,
        chart_labels=chart_labels,
        chart_deposits=chart_deposits,
        chart_withdrawals=chart_withdrawals,
        now=datetime.now(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Deposit
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT id, account_number, account_type, balance FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    acc = cur.fetchone()

    if request.method == "POST":
        try:
            amount      = float(request.form.get("amount", 0))
            description = request.form.get("description", "Deposit").strip() or "Deposit"
            confirm_password = request.form.get("confirm_password", "")

            if amount <= 0:
                raise ValueError("Amount must be positive.")

            if not _verify_password(session["user_id"], confirm_password):
                raise ValueError("Incorrect password. Deposit cancelled.")

            # Use OOP model for validation
            acct_obj = account_factory(acc[2], acc[1], session["user_name"], float(acc[3]))
            acct_obj.deposit(amount, description)

            new_balance = float(acc[3]) + amount

            # Fraud check
            now = datetime.now()
            cur.execute(
                "SELECT COUNT(*) FROM transactions "
                "WHERE account_id=%s AND created_at >= %s",
                (acc[0], (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
            )
            tx_freq = cur.fetchone()[0]
            fraud   = predict_fraud(amount, now.hour, tx_freq, float(acc[3]))
            status  = "suspicious" if fraud["flagged"] else "success"

            cur.execute(
                """INSERT INTO transactions
                   (account_id, type, amount, balance_after, description, status, flagged)
                   VALUES (%s,'deposit',%s,%s,%s,%s,%s)""",
                (acc[0], amount, new_balance, description, status, int(fraud["flagged"]))
            )
            cur.execute(
                "UPDATE accounts SET balance=%s WHERE id=%s",
                (new_balance, acc[0])
            )
            conn.commit()

            _add_notification(session["user_id"],
                f"Deposited ₹{amount:,.2f}. New balance: ₹{new_balance:,.2f}")

            msg = f"₹{amount:,.2f} deposited successfully!"
            if fraud["flagged"]:
                msg += " ⚠️ This transaction was flagged as suspicious."
            flash(msg, "warning" if fraud["flagged"] else "success")
            cur.close(); conn.close()
            return redirect(url_for("dashboard"))

        except ValueError as e:
            flash(str(e), "danger")

    cur.close(); conn.close()
    return render_template("deposit.html", acc=acc)


# ══════════════════════════════════════════════════════════════════════════════
# Withdraw
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT id, account_number, account_type, balance, overdraft_limit "
        "FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    acc = cur.fetchone()

    if request.method == "POST":
        try:
            amount      = float(request.form.get("amount", 0))
            description = request.form.get("description", "Withdrawal").strip() or "Withdrawal"
            confirm_password = request.form.get("confirm_password", "")

            if not _verify_password(session["user_id"], confirm_password):
                raise ValueError("Incorrect password. Withdrawal cancelled.")

            acct_obj = account_factory(
                acc[2], acc[1], session["user_name"], float(acc[3]),
                overdraft_limit=float(acc[4])
            )
            acct_obj.withdraw(amount, description)   # raises on invalid

            new_balance = float(acc[3]) - amount

            now = datetime.now()
            cur.execute(
                "SELECT COUNT(*) FROM transactions "
                "WHERE account_id=%s AND created_at >= %s",
                (acc[0], (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
            )
            tx_freq = cur.fetchone()[0]

            cur.execute(
                "SELECT COALESCE(AVG(amount),0) FROM transactions WHERE account_id=%s",
                (acc[0],)
            )
            avg_amount = float(cur.fetchone()[0])

            fraud  = predict_fraud(amount, now.hour, tx_freq, avg_amount)
            status = "suspicious" if fraud["flagged"] else "success"

            cur.execute(
                """INSERT INTO transactions
                   (account_id, type, amount, balance_after, description, status, flagged)
                   VALUES (%s,'withdrawal',%s,%s,%s,%s,%s)""",
                (acc[0], amount, new_balance, description, status, int(fraud["flagged"]))
            )
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (new_balance, acc[0]))
            conn.commit()

            _add_notification(session["user_id"],
                f"Withdrew ₹{amount:,.2f}. New balance: ₹{new_balance:,.2f}")

            msg = f"₹{amount:,.2f} withdrawn successfully!"
            if fraud["flagged"]:
                msg += " ⚠️ This transaction was flagged as suspicious."
            flash(msg, "warning" if fraud["flagged"] else "success")
            cur.close(); conn.close()
            return redirect(url_for("dashboard"))

        except ValueError as e:
            flash(str(e), "danger")

    cur.close(); conn.close()
    return render_template("withdraw.html", acc=acc)


# ══════════════════════════════════════════════════════════════════════════════
# Transfer
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT id, account_number, account_type, balance FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    sender_acc = cur.fetchone()

    if request.method == "POST":
        try:
            amount           = float(request.form.get("amount", 0))
            receiver_num     = request.form.get("receiver_account", "").strip()
            description      = request.form.get("description", "Transfer").strip() or "Transfer"
            confirm_password = request.form.get("confirm_password", "")

            if amount <= 0:
                raise ValueError("Amount must be positive.")

            if not _verify_password(session["user_id"], confirm_password):
                raise ValueError("Incorrect password. Transfer cancelled.")

            # Validate sender has enough
            acct_obj = account_factory(sender_acc[2], sender_acc[1], session["user_name"], float(sender_acc[3]))
            acct_obj.transfer(amount, receiver_num)

            # Find receiver
            cur.execute(
                "SELECT id, balance, user_id FROM accounts WHERE account_number=%s",
                (receiver_num,)
            )
            recv = cur.fetchone()
            if not recv:
                raise ValueError("Receiver account not found.")
            if recv[0] == sender_acc[0]:
                raise ValueError("Cannot transfer to your own account.")

            sender_new_bal   = float(sender_acc[3]) - amount
            receiver_new_bal = float(recv[1]) + amount

            now = datetime.now()
            cur.execute(
                "SELECT COUNT(*) FROM transactions WHERE account_id=%s AND created_at >= %s",
                (sender_acc[0], (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"))
            )
            tx_freq = cur.fetchone()[0]
            cur.execute(
                "SELECT COALESCE(AVG(amount),0) FROM transactions WHERE account_id=%s",
                (sender_acc[0],)
            )
            avg_amount = float(cur.fetchone()[0])
            fraud  = predict_fraud(amount, now.hour, tx_freq, avg_amount)
            status = "suspicious" if fraud["flagged"] else "success"

            # Debit sender
            cur.execute(
                """INSERT INTO transactions
                   (account_id, type, amount, balance_after, description, receiver_account, status, flagged)
                   VALUES (%s,'transfer_out',%s,%s,%s,%s,%s,%s)""",
                (sender_acc[0], amount, sender_new_bal,
                 f"Transfer to {receiver_num}", receiver_num, status, int(fraud["flagged"]))
            )
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (sender_new_bal, sender_acc[0]))

            # Credit receiver
            cur.execute(
                """INSERT INTO transactions
                   (account_id, type, amount, balance_after, description, status, flagged)
                   VALUES (%s,'transfer_in',%s,%s,%s,'success',0)""",
                (recv[0], amount, receiver_new_bal,
                 f"Transfer from {sender_acc[1]}")
            )
            cur.execute("UPDATE accounts SET balance=%s WHERE id=%s", (receiver_new_bal, recv[0]))

            conn.commit()

            _add_notification(session["user_id"],
                f"Transferred ₹{amount:,.2f} to {receiver_num}.")
            _add_notification(recv[2],
                f"Received ₹{amount:,.2f} from {sender_acc[1]}.")

            msg = f"₹{amount:,.2f} transferred to {receiver_num}!"
            if fraud["flagged"]:
                msg += " ⚠️ Flagged as suspicious."
            flash(msg, "warning" if fraud["flagged"] else "success")
            cur.close(); conn.close()
            return redirect(url_for("dashboard"))

        except ValueError as e:
            flash(str(e), "danger")

    cur.close(); conn.close()
    return render_template("transfer.html", acc=sender_acc)


# ══════════════════════════════════════════════════════════════════════════════
# Transaction History
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/history")
@login_required
def history():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE user_id=%s", (session["user_id"],))
    acc = cur.fetchone()
    if not acc:
        cur.close(); conn.close()
        return redirect(url_for("dashboard"))

    # Filters
    search    = request.args.get("search", "")
    tx_type   = request.args.get("type", "")
    date_from = request.args.get("date_from", "")
    date_to   = request.args.get("date_to", "")

    query  = "SELECT id, type, amount, balance_after, description, status, flagged, created_at "
    query += "FROM transactions WHERE account_id=%s"
    params = [acc[0]]

    if search:
        query += " AND description LIKE %s"
        params.append(f"%{search}%")
    if tx_type:
        query += " AND type=%s"
        params.append(tx_type)
    if date_from:
        query += " AND DATE(created_at) >= %s"
        params.append(date_from)
    if date_to:
        query += " AND DATE(created_at) <= %s"
        params.append(date_to)

    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    transactions = cur.fetchall()
    cur.close(); conn.close()

    return render_template("history.html",
        transactions=transactions,
        search=search, tx_type=tx_type,
        date_from=date_from, date_to=date_to
    )


# ══════════════════════════════════════════════════════════════════════════════
# Export CSV
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/export/csv")
@login_required
def export_csv():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM accounts WHERE user_id=%s", (session["user_id"],))
    acc = cur.fetchone()

    cur.execute(
        "SELECT type, amount, balance_after, description, status, created_at "
        "FROM transactions WHERE account_id=%s ORDER BY created_at DESC",
        (acc[0],)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()

    filepath = os.path.join(EXPORT_FOLDER, f"statement_{session['user_id']}.csv")
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "Amount (₹)", "Balance After (₹)", "Description", "Status", "Date"])
        for row in rows:
            writer.writerow(row)

    return send_file(filepath, as_attachment=True,
                     download_name=f"SmartBank_Statement_{datetime.now().strftime('%Y%m%d')}.csv")


# ══════════════════════════════════════════════════════════════════════════════
# Profile
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = get_connection()
    cur  = conn.cursor()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        new_pwd   = request.form.get("new_password", "")
        if full_name:
            cur.execute("UPDATE users SET full_name=%s WHERE id=%s",
                        (full_name, session["user_id"]))
            session["user_name"] = full_name
        if new_pwd and len(new_pwd) >= 8:
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                        (generate_password_hash(new_pwd), session["user_id"]))
            flash("Password updated.", "success")
        conn.commit()
        flash("Profile updated.", "success")

    cur.execute("SELECT full_name, email, created_at FROM users WHERE id=%s",
                (session["user_id"],))
    user = cur.fetchone()

    cur.execute(
        "SELECT account_number, account_type, balance, interest_rate, overdraft_limit, created_at "
        "FROM accounts WHERE user_id=%s",
        (session["user_id"],)
    )
    acc = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions t "
        "JOIN accounts a ON a.id=t.account_id WHERE a.user_id=%s",
        (session["user_id"],)
    )
    stats = cur.fetchone()

    cur.close(); conn.close()
    return render_template("profile.html", user=user, acc=acc, stats=stats)


# ══════════════════════════════════════════════════════════════════════════════
# Notifications
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/notifications")
@login_required
def notifications():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT id, message, is_read, created_at FROM notifications "
        "WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
        (session["user_id"],)
    )
    notifs = cur.fetchall()
    cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session["user_id"],))
    conn.commit()
    cur.close(); conn.close()
    return render_template("notifications.html", notifs=notifs)


# ══════════════════════════════════════════════════════════════════════════════
# API – balance (AJAX)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/balance")
@login_required
def api_balance():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT balance FROM accounts WHERE user_id=%s", (session["user_id"],))
    row = cur.fetchone()
    cur.close(); conn.close()
    return jsonify({"balance": float(row[0]) if row else 0})


# ══════════════════════════════════════════════════════════════════════════════
# Run
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
