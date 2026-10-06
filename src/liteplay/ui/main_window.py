"""Main application window and navigation shell."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from liteplay.data.database import Database
from liteplay.services.game_launcher import GameLauncherService
from liteplay.ui.dashboard import DashboardPage
from liteplay.ui.favorites import FavoritesPage
from liteplay.ui.library import LibraryPage
from liteplay.ui.settings import SettingsPage


class MainWindow(QMainWindow):
    """LitePlay's primary window with persistent sidebar navigation."""

    def __init__(self, database: Database, launcher: GameLauncherService) -> None:
        super().__init__()
        self._launcher = launcher
        self.setWindowTitle("LitePlay")
        self.resize(1100, 700)
        self.setMinimumSize(850, 550)

        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_sidebar())

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        self.pages = (
            DashboardPage(database, launcher),
            LibraryPage(database, launcher),
            FavoritesPage(database, launcher),
            SettingsPage(),
        )
        for page in self.pages:
            self.page_stack.addWidget(page)
        root_layout.addWidget(self.page_stack, 1)
        self.page_stack.currentChanged.connect(self._refresh_page)
        self._launcher.launch_failed.connect(self._show_launch_error)

        self.nav_buttons[0].setChecked(True)
        self.page_stack.setCurrentIndex(0)

    def _refresh_page(self, page_index: int) -> None:
        page = self.pages[page_index]
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    def _show_launch_error(self, game_id: int, message: str) -> None:
        QMessageBox.critical(self, "Game Launch Error", message)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Warn before detaching from running games and finalize tracked time."""
        if not self._launcher.active_game_ids:
            event.accept()
            return
        count = len(self._launcher.active_game_ids)
        title = "Game Still Running" if count == 1 else "Games Still Running"
        subject = "a running game" if count == 1 else f"{count} running games"
        it_they = "it" if count == 1 else "them"
        answer = QMessageBox.warning(
            self,
            title,
            f"LitePlay is currently tracking {subject}.\n\n"
            f"Exiting LitePlay will not close {it_they}, but LitePlay will stop "
            f"tracking additional playtime after it exits.\n\n"
            "Do you want to exit LitePlay?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        try:
            self._launcher.finalize_active_sessions()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Could Not Finish Session",
                f"LitePlay could not safely save the active session:\n{error}",
            )
            event.ignore()
            return
        event.accept()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 22, 12, 18)
        layout.setSpacing(4)

        brand_container = QVBoxLayout()
        brand_container.setSpacing(1)
        brand_container.setContentsMargins(6, 0, 6, 0)

        brand = QLabel("LitePlay")
        brand.setObjectName("brandLabel")
        brand_sub = QLabel("Game Manager")
        brand_sub.setObjectName("brandSubtitle")

        brand_container.addWidget(brand)
        brand_container.addWidget(brand_sub)
        layout.addLayout(brand_container)

        layout.addSpacing(20)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []

        nav_items = ("Dashboard", "Library", "Favorites", "Settings")
        for index, label in enumerate(nav_items):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, page_index=index: self.page_stack.setCurrentIndex(
                    page_index
                )
            )
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()
        return sidebar
