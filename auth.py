"""
Auth blueprint — replaces the client-side hardcoded login in the
Bethel Boutique mockup with real server-side authentication.

Wire it into your existing Flask app with:

    from auth import auth_bp
    app.register_blueprint(auth_bp)
    app.secret_key = os.environ["FLASK_SECRET_KEY"]  # required for sessions

Passwords are hashed with werkzeug's generate_password_hash (PBKDF2) —
never stored or compared as plaintext. Role checks happen here, on the
server, on every request — not by hiding buttons in the browser.
"""

from functools import wraps

from flask import Blueprint, request, session, jsonify

from werkzeug.security import check_password_hash

import config
import sheets_db as db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    matches = db.find_where(config.TAB_USERS, email=email)
    user = matches[0] if matches else None

    if user is None or str(user.get("active", "1")) in ("0", "False", "false"):
        return jsonify({"error": "Invalid email or password."}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    # Everything the frontend needs to render UI, and nothing more —
    # no password hash, no internal sheet row data.
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "role": user["role"],
    })


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/api/me", methods=["GET"])
def me():
    if "user_id" in session:
        return jsonify({
            "authenticated": True,
            "type": "staff",
            "id": session["user_id"],
            "name": session["name"],
            "role": session["role"],
        })
    if "customer_id" in session:
        return jsonify({
            "authenticated": True,
            "type": "customer",
            "id": session["customer_id"],
            "name": session["customer_name"],
            "role": "customer",
        })
    return jsonify({"authenticated": False}), 401


def login_required(view_func):
    """Reject the request unless a session exists. Use on every route
    that returns account-specific or business data."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required."}), 401
        return view_func(*args, **kwargs)
    return wrapped


def role_required(*allowed_roles):
    """Reject the request unless session role is one of allowed_roles.
    Use on admin-only routes (reports, staff management, settings) —
    this is the server-side check that replaces hiding buttons in the
    browser. Always combine with login_required (or put login_required
    first in the decorator stack)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Authentication required."}), 401
            if session.get("role") not in allowed_roles:
                return jsonify({"error": "Forbidden."}), 403
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def customer_required(view_func):
    """Reject the request unless a customer session exists — separate
    from login_required/role_required, which are for staff/admin
    sessions (session['user_id']). Customers use session['customer_id']
    instead, and should never be granted access to staff-only routes."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "customer_id" not in session:
            return jsonify({"error": "Authentication required."}), 401
        return view_func(*args, **kwargs)
    return wrapped
