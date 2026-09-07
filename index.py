import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app

app.template_folder = str(ROOT / "templates")
app.root_path = str(ROOT)


@app.route("/api/health")
def health():
    return {"status": "ok"}
