import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

app.template_folder = str(ROOT / "templates")
app.root_path = str(ROOT)


class _FixPath:
    """Make Flask see the original URL path under Vercel rewrites."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Prefer the original path Vercel received
        original = environ.get("HTTP_X_VERCEL_PATH") or environ.get("RAW_URI") or ""
        path_info = environ.get("PATH_INFO") or ""

        # If Vercel sent us to /api or /api/index, restore real path from headers
        if path_info in ("/api", "/api/", "/api/index", "/api/index.py"):
            # x-invoke-path / x-matched-path sometimes hold the browser path
            for key in (
                "HTTP_X_INVOKE_PATH",
                "HTTP_X_MATCHED_PATH",
                "HTTP_X_REAL_URL",
                "HTTP_X_VERCEL_PATH",
            ):
                val = environ.get(key)
                if val and not val.startswith("/api/index"):
                    environ["PATH_INFO"] = val.split("?")[0]
                    break
            else:
                # Fallback: root
                if path_info.startswith("/api"):
                    environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


app.wsgi_app = _FixPath(app.wsgi_app)


@app.route("/api/health")
def health():
    return {"status": "ok"}
