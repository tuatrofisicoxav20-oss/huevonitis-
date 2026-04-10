import sys
from pathlib import Path

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config import ensure_directories
from ui.main_window import MainWindow


def main() -> None:
    ensure_directories()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()