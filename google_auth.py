"""
Google Sign-In for BETHEL BOUTIQUE — two distinct entry points because
they carry very different levels of trust:

- STAFF/ADMIN mode only logs in an account that ALREADY exists in the
  Users tab (matched by email). It never creates or promotes anyone —
  an admin still has to add staff members first (via seed_admin.py or
  a future staff-management screen). This is what stops anyone with a
  Google account from granting themselves staff/admin access.

- CUSTOMER mode is genuinely self-service: if the email isn't already a
  Customer, one is created automatically. Customers only ever get a
  read-only view of their own order history (see /customer route in
  app.py) — never the business dashboard, never Sheets write access
  beyond their own profile.
"""

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, session, url_for

import config
import sheets_db as db

google_auth_bp = Blueprint("google_auth", __name__)

oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=config.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=config.GOOGLE_OAUTH_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@google_auth_bp.route("/auth/google/login/<mode>")
def google_login(mode):
    if mode not in ("staff", "customer"):
        return "Invalid login mode.", 400
    session["oauth_mode"] = mode
    redirect_uri = url_for("google_auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@google_auth_bp.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or {}
    email = (userinfo.get("email") or "").strip().lower()
    name = userinfo.get("name") or email
    google_id = userinfo.get("sub", "")
    mode = session.pop("oauth_mode", "customer")

    if not email:
        return redirect(url_for("index", error="google_no_email"))

    if mode == "staff":
        matches = db.find_where(config.TAB_USERS, email=email)
        user = matches[0] if matches else None
        if user is None or str(user.get("active", "1")) in ("0", "False", "false"):
            # Deliberately vague — same message a self-registration
            # attempt would get, so this doesn't confirm/deny which
            # emails exist as staff accounts.
            return redirect(url_for("index", error="not_authorized"))
        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["name"] = user["name"]
        return redirect(url_for("index"))

    # mode == "customer" — self-service, creates the account if needed
    matches = db.find_where(config.TAB_CUSTOMERS, email=email)
    customer = matches[0] if matches else None
    if customer is None:
        customer = db.insert(config.TAB_CUSTOMERS, {
            "name": name,
            "email": email,
            "phone": "",
            "google_id": google_id,
            "total_spent": 0,
        })
    session.clear()
    session["customer_id"] = customer["id"]
    session["customer_name"] = customer["name"]
    session["role"] = "customer"
    return redirect(url_for("customer_portal"))
