import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

app.template_folder = str(ROOT / "templates")
app.root_path = str(ROOT)


@app.route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@app.route("/api/index", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@app.route("/api/index/", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@app.route("/api/index/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def debug_path(subpath=None):
    from flask import request
    return {
        "request.path": request.path,
        "request.url": request.url,
        "request.full_path": request.full_path,
        "subpath": subpath,
        "args": dict(request.args),
        "method": request.method,
        "headers": {k: v for k, v in request.headers.items()},
    }
