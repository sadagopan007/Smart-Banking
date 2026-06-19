"""
SmartBank – Central Configuration
Edit DB_PASSWORD if your XAMPP MySQL root password is different (default is blank).
"""

import os

# ── Flask ──────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SMARTBANK_SECRET", "smartbank-super-secret-key-2024")

# ── MySQL / XAMPP ──────────────────────────────────────────────────────────────
DB_HOST     = "localhost"
DB_USER     = "root"
DB_PASSWORD = ""          # XAMPP default: empty string. Change if you set a root password.
DB_NAME     = "smartbank"

# ── App ────────────────────────────────────────────────────────────────────────
EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_FOLDER, exist_ok=True)
