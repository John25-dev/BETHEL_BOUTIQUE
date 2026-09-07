"""
Column definitions for each tab. init_sheets.py uses these to create the
tabs with the right headers; sheets_db.py uses them to validate rows.

Every table has an `id` column we manage ourselves (Sheets has no
auto-increment) and a `created_at` timestamp. Passwords are never stored
in plaintext — only `password_hash`.
"""

from config import (
    TAB_USERS,
    TAB_PRODUCTS,
    TAB_CUSTOMERS,
    TAB_ORDERS,
    TAB_ORDER_ITEMS,
    TAB_STOCK_LEDGER,
)

SCHEMAS = {
    TAB_USERS: [
        "id", "name", "email", "password_hash", "role",
        "active", "google_id", "created_at",
    ],
    TAB_PRODUCTS: [
        "id", "name", "sku", "category", "price",
        "stock_qty", "status", "created_at",
    ],
    TAB_CUSTOMERS: [
        "id", "name", "phone", "email", "google_id", "total_spent", "created_at",
    ],
    TAB_ORDERS: [
        "id", "customer_id", "staff_id", "status",
        "subtotal", "tax", "total", "created_at",
    ],
    TAB_ORDER_ITEMS: [
        "id", "order_id", "product_id", "qty", "unit_price",
    ],
    TAB_STOCK_LEDGER: [
        "id", "product_id", "change_qty", "reason",
        "ref_order_id", "created_at",
    ],
}
