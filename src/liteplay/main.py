"""Application entry point for LitePlay."""

import sys
from pathlib import Path

# Support running this file directly, as well as through the installed entry point.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from liteplay.data.database import Database
from liteplay.services.game_launcher import GameLauncherService
from liteplay.ui.main_window import MainWindow
from liteplay.ui.styles import APP_STYLESHEET


def main() -> int:
    """Start the LitePlay desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("LitePlay")
    app.setStyleSheet(APP_STYLESHEET)
    database = Database()
    try:
        launcher = GameLauncherService(database)
        window = MainWindow(database, launcher)
        window.show()
        return app.exec()
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
