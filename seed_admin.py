"""
Run once after init_sheets.py, to create the first admin account.
Without this there's no way to log in, since the Users tab starts empty.

    python seed_admin.py

You'll be prompted for name, email, and password — the password is never
printed or stored anywhere except as a hash in the sheet.
"""

import getpass

from werkzeug.security import generate_password_hash

import config
import sheets_db as db


def main():
    existing_admins = db.find_where(config.TAB_USERS, role="admin")
    if existing_admins:
        print("An admin already exists:", [u["email"] for u in existing_admins])
        proceed = input("Create another admin anyway? (y/N): ").strip().lower()
        if proceed != "y":
            return

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords didn't match — nothing created.")
        return

    db.insert(config.TAB_USERS, {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "role": "admin",
        "active": "1",
    })
    print(f"Admin account created for {email}.")


if __name__ == "__main__":
    main()
