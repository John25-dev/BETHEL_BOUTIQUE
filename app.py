import os

from flask import Flask, jsonify, request, session, render_template, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

import config
import sheets_db as db
from auth import auth_bp, login_required, role_required, customer_required
from google_auth import google_auth_bp, init_oauth

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY or os.urandom(24)
if not config.FLASK_SECRET_KEY:
    app.logger.warning(
        "FLASK_SECRET_KEY is not set — using a random key that changes on "
        "every restart, which will log everyone out on each deploy. Set "
        "FLASK_SECRET_KEY in your environment for production."
    )

# Vercel (and most hosts) terminate HTTPS at a proxy and forward plain
# HTTP internally. Without this, url_for(..., _external=True) generates
# http:// URLs, which Google rejects as a redirect_uri mismatch.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.register_blueprint(auth_bp)
app.register_blueprint(google_auth_bp)
init_oauth(app)


# ---------------------------------------------------------------- frontend

@app.route("/")
def index():
    return render_template(
        "index.html", tax_rate=config.TAX_RATE, oauth_error=request.args.get("error")
    )


@app.route("/customer")
def customer_portal():
    if "customer_id" not in session:
        return redirect(url_for("index"))
    return render_template("customer.html", name=session.get("customer_name", ""))


@app.route("/api/customer/orders", methods=["GET"])
@customer_required
def customer_orders():
    orders = db.find_where(config.TAB_ORDERS, customer_id=session["customer_id"])
    return jsonify(orders)


@app.route("/healthz")
def healthz():
    """Simple endpoint for the hosting platform to check the app is up.
    Does not touch Google Sheets, so it stays fast and doesn't burn quota."""
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------- products

@app.route("/api/products", methods=["GET"])
@login_required
def list_products():
    return jsonify(db.get_all(config.TAB_PRODUCTS))


@app.route("/api/products", methods=["POST"])
@role_required("admin")
def create_product():
    data = request.get_json(force=True)
    for field in ("name", "sku", "price"):
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required."}), 400
    product = db.insert(config.TAB_PRODUCTS, {
        "name": data["name"],
        "sku": data["sku"],
        "category": data.get("category", ""),
        "price": data["price"],
        "stock_qty": data.get("stock_qty", 0),
        "status": "In Stock" if int(data.get("stock_qty", 0)) > 0 else "Out of Stock",
    })
    return jsonify(product), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@role_required("admin")
def edit_product(product_id):
    data = request.get_json(force=True)
    updated = db.update(config.TAB_PRODUCTS, product_id, data)
    if not updated:
        return jsonify({"error": "Product not found."}), 404
    return jsonify(db.find_by_id(config.TAB_PRODUCTS, product_id))


# --------------------------------------------------------------- customers

@app.route("/api/customers", methods=["GET"])
@login_required
def list_customers():
    return jsonify(db.get_all(config.TAB_CUSTOMERS))


@app.route("/api/customers", methods=["POST"])
@login_required
def create_customer():
    data = request.get_json(force=True)
    if not data.get("name"):
        return jsonify({"error": "'name' is required."}), 400
    customer = db.insert(config.TAB_CUSTOMERS, {
        "name": data["name"],
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "total_spent": 0,
    })
    return jsonify(customer), 201


# ------------------------------------------------------------------ orders

@app.route("/api/orders", methods=["GET"])
@login_required
def list_orders():
    orders = db.get_all(config.TAB_ORDERS)
    if session["role"] != "admin":
        orders = [o for o in orders if str(o["staff_id"]) == str(session["user_id"])]
    return jsonify(orders)


@app.route("/api/orders", methods=["POST"])
@login_required
def create_order():
    """Body: {customer_id: optional int, items: [{product_id, qty}]}
    Computes totals server-side from current product prices (never trust
    a price sent by the client), adjusts stock, and rejects the whole
    order if any item would oversell."""
    data = request.get_json(force=True)
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "Order must have at least one item."}), 400

    line_items = []
    subtotal = 0.0
    for item in items:
        product = db.find_by_id(config.TAB_PRODUCTS, item["product_id"])
        if product is None:
            return jsonify({"error": f"Product {item['product_id']} not found."}), 404
        qty = int(item["qty"])
        if qty <= 0:
            return jsonify({"error": "Quantity must be positive."}), 400
        if int(product["stock_qty"]) < qty:
            return jsonify({"error": f"Not enough stock for {product['name']}."}), 409
        unit_price = float(product["price"])
        subtotal += unit_price * qty
        line_items.append((product, qty, unit_price))

    tax = round(subtotal * config.TAX_RATE, 2)
    total = round(subtotal + tax, 2)

    order = db.insert(config.TAB_ORDERS, {
        "customer_id": data.get("customer_id", ""),
        "staff_id": session["user_id"],
        "status": "Completed",
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": total,
    })

    for product, qty, unit_price in line_items:
        db.insert(config.TAB_ORDER_ITEMS, {
            "order_id": order["id"],
            "product_id": product["id"],
            "qty": qty,
            "unit_price": unit_price,
        })
        # Reduce stock and log to StockLedger; rejects (returns False) if
        # two requests raced past the check above — good enough for a
        # single boutique's traffic, see README for the scaling note.
        db.adjust_stock(product["id"], -qty, reason="sale", ref_order_id=order["id"])

    if data.get("customer_id"):
        customer = db.find_by_id(config.TAB_CUSTOMERS, data["customer_id"])
        if customer is not None:
            new_spent = float(customer.get("total_spent") or 0) + total
            db.update(config.TAB_CUSTOMERS, data["customer_id"], {"total_spent": new_spent})

    return jsonify(order), 201


# ------------------------------------------------------------------- staff

@app.route("/api/staff", methods=["GET"])
@role_required("admin")
def list_staff():
    users = db.get_all(config.TAB_USERS)
    safe = [{k: v for k, v in u.items() if k != "password_hash"} for u in users]
    return jsonify(safe)


# ----------------------------------------------------------------- reports

@app.route("/api/reports/summary", methods=["GET"])
@role_required("admin")
def reports_summary():
    orders = db.get_all(config.TAB_ORDERS)
    completed = [o for o in orders if o.get("status") == "Completed"]
    total_sales = sum(float(o["total"]) for o in completed if o["total"])
    avg_order = round(total_sales / len(completed), 2) if completed else 0
    products = db.get_all(config.TAB_PRODUCTS)
    low_stock = [p for p in products if int(p["stock_qty"] or 0) < 5]
    return jsonify({
        "order_count": len(completed),
        "total_sales": round(total_sales, 2),
        "avg_order_value": avg_order,
        "low_stock_count": len(low_stock),
    })


if __name__ == "__main__":
    # Local development only — a real deployment runs this through
    # gunicorn (see Procfile), which ignores this block entirely.
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
