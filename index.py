"""
Vercel serverless entrypoint.
Re-exports the Flask app so Vercel's Python runtime can serve it.
"""
import sys
from pathlib import Path

# Ensure the project root is on the path so `import app` works
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402

# Vercel looks for a variable named `app` (or `handler` for some runtimes)
# The Flask instance is already called `app` in app.py.
