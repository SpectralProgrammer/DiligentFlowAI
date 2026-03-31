from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

try:
    from app.main import app
except ModuleNotFoundError:  # pragma: no cover - depends on execution directory
    from backend.app.main import app
