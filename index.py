import sys
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

app.template_folder = str(ROOT / "templates")
app.root_path = str(ROOT)


class RestorePath:
    """Restore the real browser path from ?path= (set by vercel.json rewrites)."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = environ.get("QUERY_STRING", "")
        params = parse_qs(qs)
        if "path" in params and params["path"]:
            original = params["path"][0] or "/"
            if not original.startswith("/"):
                original = "/" + original
            environ["PATH_INFO"] = original
            # Remove path= from query so Flask/forms are unaffected
            other = []
            for part in qs.split("&"):
                if part and not part.startswith("path="):
                    other.append(part)
            environ["QUERY_STRING"] = "&".join(other)
        return self.wsgi_app(environ, start_response)


app.wsgi_app = RestorePath(app.wsgi_app)


@app.route("/api/health")
def health():
    return {"status": "ok"}
