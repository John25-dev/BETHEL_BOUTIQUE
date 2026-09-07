"""
Configuration for the Google Sheets-backed data layer.

Nothing here is a secret by itself — the actual service account JSON key
file stays on disk (outside version control) and is never sent to the
frontend. Only the file PATH and the sheet name/id are configured here.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads a local .env file if present; no-op on most hosts
except ImportError:
    pass

# Path to the service account JSON key you downloaded from Google Cloud.
# Keep the actual file outside of git — e.g. in an `instance/` folder that's
# in your .gitignore.
GOOGLE_SHEETS_CREDS_PATH = os.environ.get(
    "GOOGLE_SHEETS_CREDS_PATH", "instance/gsheets-creds.json"
)

# Alternative to the file path: paste the ENTIRE contents of the JSON key
# file as a single environment variable. Use this on hosts where you can
# set env vars but can't easily commit/upload a file (Render, Railway,
# etc.) — sheets_db.py prefers this over the file path when it's set.
GOOGLE_SHEETS_CREDS_JSON = os.environ.get("GOOGLE_SHEETS_CREDS_JSON", "")

# Required for Flask sessions (login cookies) to be secure. Generate one
# with: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "")

# Sales tax rate applied in the POS / order totals.
TAX_RATE = float(os.environ.get("TAX_RATE", "0.16"))

# Google Sign-In (OAuth) — separate from the Sheets service account above.
# Create these under APIs & Services > Credentials > OAuth Client ID.
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

# Either the human-readable Sheet name (must be exact) or, more reliably,
# the Sheet's ID (the long string in its URL between /d/ and /edit).
# Prefer the ID once you have it — names can be renamed accidentally.
GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME", "ZionBoutique Database")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")  # optional, preferred

# Scopes gspread needs to read/write Sheets and locate them via Drive.
GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Tab names — one per "table". Keep these in sync with init_sheets.py.
TAB_USERS = "Users"
TAB_PRODUCTS = "Products"
TAB_CUSTOMERS = "Customers"
TAB_ORDERS = "Orders"
TAB_ORDER_ITEMS = "OrderItems"
TAB_STOCK_LEDGER = "StockLedger"
