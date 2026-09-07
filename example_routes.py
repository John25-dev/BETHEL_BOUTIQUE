"""
Example showing how to protect real routes with the decorators from
auth.py. Copy the pattern into your actual routes file — this isn't
meant to be run standalone.
"""

from flask import Flask, jsonify, request, session

from auth import auth_bp, login_required, role_required
import config
import sheets_db as db

app = Flask(__name__)
app.secret_key = "replace-with-a-long-random-value-from-os.urandom(24)"
app.register_blueprint(auth_bp)


# --- Products: everyone logged in can view, only admins can edit ---

@app.route("/api/products", methods=["GET"])
@login_required
def list_products():
    return jsonify(db.get_all(config.TAB_PRODUCTS))


@app.route("/api/products", methods=["POST"])
@role_required("admin")
def create_product():
    data = request.get_json()
    product = db.insert(config.TAB_PRODUCTS, {
        "name": data["name"],
        "sku": data["sku"],
        "category": data.get("category", ""),
        "price": data["price"],
        "stock_qty": data.get("stock_qty", 0),
        "status": "In Stock",
    })
    return jsonify(product), 201


# --- Reports/Staff/Settings: admin only, enforced here — not by hiding
#     the sidebar link in the browser ---

@app.route("/api/reports/summary", methods=["GET"])
@role_required("admin")
def reports_summary():
    orders = db.get_all(config.TAB_ORDERS)
    total = sum(float(o["total"]) for o in orders if o["total"])
    return jsonify({"order_count": len(orders), "total_sales": total})


@app.route("/api/staff", methods=["GET"])
@role_required("admin")
def list_staff():
    users = db.get_all(config.TAB_USERS)
    # Never return password_hash to the frontend, even to admins.
    safe = [{k: v for k, v in u.items() if k != "password_hash"} for u in users]
    return jsonify(safe)


# --- A route any logged-in staff member can use, but that only shows
#     their own sales (ownership check, not just a role check) ---

@app.route("/api/orders/mine", methods=["GET"])
@login_required
def my_orders():
    my_id = session["user_id"]
    orders = db.find_where(config.TAB_ORDERS, staff_id=my_id)
    return jsonify(orders)
