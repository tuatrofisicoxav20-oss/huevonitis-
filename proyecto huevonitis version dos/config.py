from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
AUTOSAVE_DIR = DATA_DIR / "autosave"
BACKUPS_DIR = DATA_DIR / "backups"
EXPORTS_DIR = DATA_DIR / "exports"
PREVIEWS_DIR = DATA_DIR / "previews"
HANDWRITING_DIR = DATA_DIR / "generated_handwriting"

ASSETS_DIR = BASE_DIR / "assets"
PAPERS_DIR = ASSETS_DIR / "papers"

DEFAULT_PAGE_WIDTH = 900
DEFAULT_PAGE_HEIGHT = 1200

DEFAULT_MARGIN_TOP = 80
DEFAULT_MARGIN_LEFT = 70
DEFAULT_MARGIN_RIGHT = 70
DEFAULT_MARGIN_BOTTOM = 80

APP_TITLE = "Huevonitis 2.0 - Prioridad S"
AUTOSAVE_INTERVAL_MS = 15000


def ensure_directories() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    HANDWRITING_DIR.mkdir(parents=True, exist_ok=True)
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)