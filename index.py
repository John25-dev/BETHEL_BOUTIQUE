import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

app.template_folder = str(ROOT / "templates")
app.root_path = str(ROOT)


class StripVercelPrefix:
    """
    Vercel sends PATH_INFO like /api/index/login for a browser request to /login.
    Strip the /api/index prefix so Flask routes match.
    """

    PREFIX = "/api/index"

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO") or ""
        if path == self.PREFIX or path == self.PREFIX + "/":
            environ["PATH_INFO"] = "/"
        elif path.startswith(self.PREFIX + "/"):
            environ["PATH_INFO"] = path[len(self.PREFIX):] or "/"
        return self.wsgi_app(environ, start_response)


app.wsgi_app = StripVercelPrefix(app.wsgi_app)
