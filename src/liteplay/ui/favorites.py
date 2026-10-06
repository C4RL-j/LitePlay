"""Database-backed favorite games page."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from liteplay.data.database import Database
from liteplay.models.game import Game
from liteplay.services.game_launcher import GameLauncherService
from liteplay.ui.game_display import (
    ElidedLabel,
    executable_icon,
    format_last_played,
    format_playtime,
)


class FavoritesPage(QWidget):
    """Display favorited games using shared database and launcher state."""

    def __init__(
        self,
        database: Database,
        launcher: GameLauncherService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._launcher = launcher
        self._games: list[Game] = []
        self._icon_provider = QFileIconProvider()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Favorites")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Your favorite games")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        layout.addLayout(heading)

        self.content_stack = QStackedWidget()
        self.empty_state = self._build_empty_state()
        self.list_scroll = QScrollArea()
        self.list_scroll.setObjectName("libraryScroll")
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_content = QWidget()
        self.list_content.setObjectName("libraryContent")
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_scroll.setWidget(self.list_content)
        self.content_stack.addWidget(self.empty_state)
        self.content_stack.addWidget(self.list_scroll)
        layout.addWidget(self.content_stack, 1)

        launcher.game_started.connect(self._on_game_state_changed)
        launcher.game_finished.connect(self._on_game_finished)
        self.refresh()

    def _build_empty_state(self) -> QWidget:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 40, 0, 40)
        wrapper_layout.addStretch()
        card = QFrame()
        card.setObjectName("emptyState")
        card.setMaximumWidth(460)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        star_icon = QLabel("★")
        star_icon.setObjectName("emptyStateStarIcon")
        star_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(star_icon)
        empty_title = QLabel("No favorites yet.")
        empty_title.setObjectName("emptyStateTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(empty_title)
        empty_text = QLabel("Star a game in your library to access it quickly from here.")
        empty_text.setObjectName("emptyStateText")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(empty_text)
        wrapper_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        wrapper_layout.addStretch()
        return wrapper

    def refresh(self) -> None:
        self._games = self._database.get_favorite_games()
        self._clear_layout()
        for game in self._games:
            self.list_layout.addWidget(self._game_row(game))
        self.list_layout.addStretch()
        self.content_stack.setCurrentWidget(
            self.list_scroll if self._games else self.empty_state
        )

    def _game_row(self, game: Game) -> QFrame:
        running = game.id is not None and self._launcher.is_running(game.id)
        row = QFrame()
        row.setObjectName("gameRow")
        row.setProperty("running", "true" if running else "false")
        row.setFixedHeight(56)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 8, 14, 8)
        row_layout.setSpacing(14)

        icon = QLabel()
        icon_size = 36
        icon.setFixedSize(icon_size, icon_size)
        icon.setPixmap(
            executable_icon(self._icon_provider, self.style(), game.exe_path).pixmap(
                QSize(icon_size, icon_size)
            )
        )
        row_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)

        name = ElidedLabel(game.name)
        name.setObjectName("gameName")
        name.setToolTip(f"{game.name}\n{game.exe_path}")

        meta = QLabel(
            f"Last played: {format_last_played(game.last_played)}   ·   "
            f"Playtime: {format_playtime(game.total_play_seconds)}"
        )
        meta.setObjectName("gameMeta")
        info.addWidget(name)
        info.addWidget(meta)
        row_layout.addLayout(info, 1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        favorite = QPushButton("★")
        favorite.setObjectName("favoriteButton")
        favorite.setProperty("active", "true")
        favorite.setToolTip("Unfavorite")
        favorite.setCursor(Qt.CursorShape.PointingHandCursor)
        favorite.clicked.connect(
            lambda checked=False, item=game: self._unfavorite(item)
        )
        actions_layout.addWidget(favorite, 0, Qt.AlignmentFlag.AlignVCenter)

        launch = QPushButton("Running" if running else "Launch")
        launch.setObjectName("launchButton")
        launch.setProperty("running", "true" if running else "false")
        launch.setEnabled(not running)
        launch.setToolTip("Game is running" if running else f"Launch {game.name}")
        launch.setCursor(
            Qt.CursorShape.ArrowCursor
            if running
            else Qt.CursorShape.PointingHandCursor
        )
        launch.clicked.connect(
            lambda checked=False, item=game: self._launcher.launch(item)
        )
        actions_layout.addWidget(launch, 0, Qt.AlignmentFlag.AlignVCenter)

        row_layout.addLayout(actions_layout, 0)
        return row

    def _unfavorite(self, game: Game) -> None:
        if game.id is not None and self._database.set_favorite(game.id, False):
            self.refresh()

    def _clear_layout(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _on_game_state_changed(self, game_id: int) -> None:
        self.refresh()

    def _on_game_finished(self, game_id: int, duration_seconds: int) -> None:
        self.refresh()
