"""
Run this once after you've created the Google Sheet and shared it with
your service account's client_email (see setup steps).

    python init_sheets.py

It creates any missing tabs and writes the header row for each, based on
schema.py. Safe to re-run — it skips tabs that already exist.
"""

import config
from schema import SCHEMAS
from sheets_db import _get_client  # reuses the same file-or-env-var auth logic


def main():
    client = _get_client()

    if config.GOOGLE_SHEET_ID:
        spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    else:
        spreadsheet = client.open(config.GOOGLE_SHEET_NAME)

    existing_titles = [ws.title for ws in spreadsheet.worksheets()]

    for tab_name, headers in SCHEMAS.items():
        if tab_name in existing_titles:
            print(f"'{tab_name}' already exists — skipping.")
            continue
        ws = spreadsheet.add_worksheet(
            title=tab_name, rows=1000, cols=max(len(headers), 10)
        )
        ws.append_row(headers)
        print(f"Created '{tab_name}' with headers: {headers}")

    # Sheets always creates a default "Sheet1" — remove it if it's empty
    # and unused, so the tab list stays clean.
    default = next(
        (ws for ws in spreadsheet.worksheets() if ws.title == "Sheet1"), None
    )
    if default is not None and default.get_all_values() == []:
        spreadsheet.del_worksheet(default)
        print("Removed empty default 'Sheet1' tab.")

    print("\nDone. Tabs in spreadsheet:", [ws.title for ws in spreadsheet.worksheets()])


if __name__ == "__main__":
    main()
