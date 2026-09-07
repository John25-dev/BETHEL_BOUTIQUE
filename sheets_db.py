"""
Generic data-access layer over a Google Sheet, used in place of
SQLAlchemy/SQLite. Every tab is treated like a table: row 1 is headers,
every other row is a record.

Import this module from your Flask routes instead of talking to gspread
directly, e.g.:

    from sheets_db import get_all, find_by_id, insert, update, delete

Connection is cached at module load so we don't re-authenticate on every
request — Sheets API has a request-per-minute quota, so avoid opening a
fresh connection per call.
"""

import datetime
import json
import threading

import gspread
from google.oauth2.service_account import Credentials

import config
from schema import SCHEMAS

_lock = threading.Lock()  # guards read-check-write sequences (see update_qty)
_client = None
_spreadsheet = None


def _get_client():
    global _client
    if _client is None:
        if config.GOOGLE_SHEETS_CREDS_JSON:
            info = json.loads(config.GOOGLE_SHEETS_CREDS_JSON)
            creds = Credentials.from_service_account_info(
                info, scopes=config.GOOGLE_SHEETS_SCOPES
            )
        else:
            creds = Credentials.from_service_account_file(
                config.GOOGLE_SHEETS_CREDS_PATH, scopes=config.GOOGLE_SHEETS_SCOPES
            )
        _client = gspread.authorize(creds)
    return _client


def _get_spreadsheet():
    global _spreadsheet
    if _spreadsheet is None:
        client = _get_client()
        if config.GOOGLE_SHEET_ID:
            _spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        else:
            _spreadsheet = client.open(config.GOOGLE_SHEET_NAME)
    return _spreadsheet


def _worksheet(tab_name):
    return _get_spreadsheet().worksheet(tab_name)


def _next_id(tab_name):
    """Simple incrementing integer ID based on the current max `id` column."""
    records = get_all(tab_name)
    if not records:
        return 1
    return max(int(r["id"]) for r in records) + 1


def get_all(tab_name):
    """Return every row in a tab as a list of dicts (header -> value)."""
    return _worksheet(tab_name).get_all_records()


def find_by_id(tab_name, record_id):
    """Return the first row whose `id` matches, or None."""
    for row in get_all(tab_name):
        if str(row.get("id")) == str(record_id):
            return row
    return None


def find_where(tab_name, **filters):
    """Return all rows matching every key/value pair given, e.g.
    find_where('Users', email='a@b.com')."""
    results = []
    for row in get_all(tab_name):
        if all(str(row.get(k)) == str(v) for k, v in filters.items()):
            results.append(row)
    return results


def insert(tab_name, data: dict):
    """Insert a new row. Auto-fills `id` and `created_at` if the schema
    has those columns and they weren't provided."""
    headers = SCHEMAS[tab_name]
    with _lock:
        if "id" in headers and "id" not in data:
            data["id"] = _next_id(tab_name)
        if "created_at" in headers and "created_at" not in data:
            data["created_at"] = datetime.datetime.utcnow().isoformat()
        row = [data.get(col, "") for col in headers]
        _worksheet(tab_name).append_row(row, value_input_option="USER_ENTERED")
    return data


def update(tab_name, record_id, updates: dict):
    """Update specific columns on the row matching `id`. Returns True if
    a row was found and updated, False otherwise."""
    ws = _worksheet(tab_name)
    headers = SCHEMAS[tab_name]
    with _lock:
        cell = ws.find(str(record_id), in_column=headers.index("id") + 1)
        if cell is None:
            return False
        row_values = ws.row_values(cell.row)
        current = dict(zip(headers, row_values))
        current.update({k: v for k, v in updates.items() if k in headers})
        new_row = [current.get(col, "") for col in headers]
        ws.update(f"A{cell.row}", [new_row], value_input_option="USER_ENTERED")
    return True


def delete(tab_name, record_id):
    """Delete the row matching `id`. Returns True if a row was removed."""
    ws = _worksheet(tab_name)
    headers = SCHEMAS[tab_name]
    with _lock:
        cell = ws.find(str(record_id), in_column=headers.index("id") + 1)
        if cell is None:
            return False
        ws.delete_rows(cell.row)
    return True


def adjust_stock(product_id, change_qty, reason, ref_order_id=""):
    """Atomically-ish adjust a product's stock and log it to StockLedger.
    Uses the module-level lock so two simultaneous sales can't both read
    the same stale stock_qty and oversell — Sheets has no row locking of
    its own, so this is enforced at the application level."""
    with _lock:
        product = find_by_id(config.TAB_PRODUCTS, product_id)
        if product is None:
            return False
        new_qty = int(product["stock_qty"]) + change_qty
        if new_qty < 0:
            return False  # would oversell — reject
        update(config.TAB_PRODUCTS, product_id, {"stock_qty": new_qty})
    insert(config.TAB_STOCK_LEDGER, {
        "product_id": product_id,
        "change_qty": change_qty,
        "reason": reason,
        "ref_order_id": ref_order_id,
    })
    return True
