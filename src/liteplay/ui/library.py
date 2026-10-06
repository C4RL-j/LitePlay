"""SQLite-backed game library page."""

from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from liteplay.data.database import Database
from liteplay.models.game import Game
from liteplay.services.game_launcher import GameLauncherService
from liteplay.ui.edit_game_dialog import EditGameDialog
from liteplay.ui.game_display import (
    ElidedLabel,
    executable_icon,
    format_last_played,
    format_playtime,
)


def default_game_name(executable_path: str) -> str:
    """Derive the initial display name from an executable filename."""
    return Path(executable_path).stem or "Game"


SORT_RECENTLY_ADDED = "recently_added"
SORT_NAME_ASCENDING = "name_ascending"
SORT_NAME_DESCENDING = "name_descending"
SORT_RECENTLY_PLAYED = "recently_played"
SORT_MOST_PLAYED = "most_played"


def filter_and_sort_games(
    games: list[Game], search_text: str, sort_mode: str
) -> list[Game]:
    """Return one deterministic filtered collection for both Library views."""
    query = search_text.strip().casefold()
    filtered = [game for game in games if query in game.name.casefold()]
    # Establish the deterministic tie-breaker before applying the stable primary sort.
    ordered = sorted(filtered, key=lambda game: game.id or 0)
    if sort_mode == SORT_NAME_ASCENDING:
        return sorted(ordered, key=lambda game: game.name.casefold())
    if sort_mode == SORT_NAME_DESCENDING:
        return sorted(ordered, key=lambda game: game.name.casefold(), reverse=True)
    if sort_mode == SORT_RECENTLY_PLAYED:
        return sorted(
            ordered,
            key=lambda game: (
                game.last_played is not None,
                game.last_played or datetime.min,
            ),
            reverse=True,
        )
    if sort_mode == SORT_MOST_PLAYED:
        return sorted(
            ordered, key=lambda game: game.total_play_seconds, reverse=True
        )
    return sorted(
        ordered,
        key=lambda game: (
            game.added_at is not None,
            game.added_at or datetime.min,
        ),
        reverse=True,
    )


class LibrarySortComboBox(QComboBox):
    """Sort selector dropdown with a subtle custom painted chevron indicator."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        arrow_x = r.right() - 11
        arrow_y = r.center().y()
        color = QColor(
            "#dbe3ee"
            if self.hasFocus()
            else ("#9aa5b5" if self.underMouse() else "#717d91")
        )
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(arrow_x - 3, arrow_y - 2, arrow_x, arrow_y + 1)
        painter.drawLine(arrow_x, arrow_y + 1, arrow_x + 3, arrow_y - 2)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update()


class LibraryPage(QWidget):
    """Display and manage games stored in the application database."""

    def __init__(
        self,
        database: Database,
        launcher: GameLauncherService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._launcher = launcher
        self._all_games: list[Game] = []
        self._games: list[Game] = []
        self._icon_provider = QFileIconProvider()
        self._grid_columns = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Header: Title + Subtitle on left, Controls on right
        header = QHBoxLayout()
        header.setSpacing(12)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Library")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Your games")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)

        header.addStretch()

        controls = QHBoxLayout()
        controls.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("librarySearch")
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(135)
        self.search_input.textChanged.connect(self._apply_filters)
        controls.addWidget(self.search_input)

        self.sort_combo = LibrarySortComboBox()
        self.sort_combo.setObjectName("librarySort")
        self.sort_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sort_combo.setFixedWidth(148)
        for label, mode in (
            ("Recently Added", SORT_RECENTLY_ADDED),
            ("Name A-Z", SORT_NAME_ASCENDING),
            ("Name Z-A", SORT_NAME_DESCENDING),
            ("Recently Played", SORT_RECENTLY_PLAYED),
            ("Most Played", SORT_MOST_PLAYED),
        ):
            self.sort_combo.addItem(label, mode)
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        controls.addWidget(self.sort_combo)

        self.add_button = QPushButton("+ Add Game")
        self.add_button.setObjectName("primaryButton")
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self._add_game)
        controls.addWidget(self.add_button)

        segmented_frame = QFrame()
        segmented_frame.setObjectName("segmentedControl")
        selector = QHBoxLayout(segmented_frame)
        selector.setContentsMargins(0, 0, 0, 0)
        selector.setSpacing(2)

        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)
        self.semi_list_button = self._view_button("Semi-list")
        self.grid_button = self._view_button("Grid")
        self.semi_list_button.setChecked(True)

        selector.addWidget(self.semi_list_button)
        selector.addWidget(self.grid_button)
        controls.addWidget(segmented_frame)

        header.addLayout(controls)
        layout.addLayout(header)

        # Content stack
        self.content_stack = QStackedWidget()
        self.empty_state = self._build_empty_state()
        self.search_empty_state = self._build_search_empty_state()
        self.list_scroll, self.list_content, self.list_layout = self._scroll_view(
            QVBoxLayout
        )
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.grid_scroll, self.grid_content, self.grid_layout = self._scroll_view(
            QGridLayout
        )
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.content_stack.addWidget(self.empty_state)
        self.content_stack.addWidget(self.search_empty_state)
        self.content_stack.addWidget(self.list_scroll)
        self.content_stack.addWidget(self.grid_scroll)
        layout.addWidget(self.content_stack, 1)

        self.semi_list_button.clicked.connect(self._show_selected_view)
        self.grid_button.clicked.connect(self._show_selected_view)
        self._launcher.game_started.connect(self._on_game_state_changed)
        self._launcher.game_finished.connect(self._on_game_finished)
        self.refresh()

    def _view_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("segmentedButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_group.addButton(button)
        return button

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

        icon_label = QLabel()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        icon_label.setPixmap(icon.pixmap(QSize(36, 36)))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("No games added yet.")
        title.setObjectName("emptyStateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        text = QLabel("Add a game to start building your library.")
        text.setObjectName("emptyStateText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(text)

        card_layout.addSpacing(6)
        add_btn = QPushButton("+ Add Game")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_game)
        card_layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignCenter)

        wrapper_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        wrapper_layout.addStretch()
        return wrapper

    def _scroll_view(self, layout_type):
        scroll = QScrollArea()
        scroll.setObjectName("libraryScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("libraryContent")
        content_layout = layout_type(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        scroll.setWidget(content)
        return scroll, content, content_layout

    def _build_search_empty_state(self) -> QWidget:
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

        icon_label = QLabel()
        icon_label.setPixmap(self._make_search_icon_pixmap())
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)

        title = QLabel("No games found")
        title.setObjectName("emptyStateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        message = QLabel("Try a different search.")
        message.setObjectName("emptyStateText")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(message)

        wrapper_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        wrapper_layout.addStretch()
        return wrapper

    @staticmethod
    def _make_search_icon_pixmap(size: int = 36) -> QPixmap:
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#475569"), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(7, 7, 14, 14)
        painter.drawLine(18, 18, 27, 27)
        painter.end()
        return pm

    def refresh(self) -> None:
        """Reload games while preserving search, sort, and view state."""
        self._all_games = self._database.list_games()
        self._apply_filters()

    def _apply_filters(self, *args) -> None:
        self._games = filter_and_sort_games(
            self._all_games,
            self.search_input.text(),
            self.sort_combo.currentData() or SORT_RECENTLY_ADDED,
        )
        self._clear_layout(self.list_layout)
        for game in self._games:
            self.list_layout.addWidget(self._game_entry(game, grid=False))
        self.list_layout.addStretch()

        self._grid_columns = 0
        self._rebuild_grid()
        self._show_selected_view()

    def _show_selected_view(self) -> None:
        if not self._all_games:
            self.content_stack.setCurrentWidget(self.empty_state)
        elif not self._games:
            self.content_stack.setCurrentWidget(self.search_empty_state)
        elif self.grid_button.isChecked():
            self.content_stack.setCurrentWidget(self.grid_scroll)
            self._rebuild_grid()
        else:
            self.content_stack.setCurrentWidget(self.list_scroll)

    def _add_game(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Game", "", "Windows executables (*.exe)"
        )
        if not path:
            return
        absolute_path = str(Path(path).resolve())
        self._database.add_game(
            Game(name=default_game_name(absolute_path), exe_path=absolute_path)
        )
        self.refresh()

    def _game_icon(self, game: Game) -> QIcon:
        return executable_icon(self._icon_provider, self.style(), game.exe_path)

    def _game_entry(self, game: Game, grid: bool) -> QFrame:
        if not grid:
            return self._build_list_row(game)
        return self._build_grid_card(game)

    def _build_list_row(self, game: Game) -> QFrame:
        running = game.id is not None and self._launcher.is_running(game.id)
        row = QFrame()
        row.setObjectName("gameRow")
        row.setProperty("running", "true" if running else "false")
        row.setFixedHeight(56)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 8, 14, 8)
        row_layout.setSpacing(14)

        icon_label = QLabel()
        icon_size = 36
        icon_label.setPixmap(self._game_icon(game).pixmap(QSize(icon_size, icon_size)))
        icon_label.setFixedSize(icon_size, icon_size)
        row_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        name_label = ElidedLabel(game.name)
        name_label.setObjectName("gameName")
        name_label.setToolTip(f"{game.name}\n{game.exe_path}")

        meta_label = QLabel(
            f"Last played: {format_last_played(game.last_played)}   ·   Playtime: {format_playtime(game.total_play_seconds)}"
        )
        meta_label.setObjectName("gameMeta")

        info_layout.addWidget(name_label)
        info_layout.addWidget(meta_label)
        row_layout.addLayout(info_layout, 1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        favorite = QPushButton("★" if game.favorite else "☆")
        favorite.setObjectName("favoriteButton")
        favorite.setProperty("active", "true" if game.favorite else "false")
        favorite.setToolTip("Unfavorite" if game.favorite else "Favorite")
        favorite.setCursor(Qt.CursorShape.PointingHandCursor)
        favorite.clicked.connect(
            lambda checked=False, item=game: self._toggle_favorite(item)
        )
        actions_layout.addWidget(favorite, 0, Qt.AlignmentFlag.AlignVCenter)

        actions_layout.addWidget(
            self._launch_button(game), 0, Qt.AlignmentFlag.AlignVCenter
        )

        actions_layout.addWidget(
            self._edit_button(game), 0, Qt.AlignmentFlag.AlignVCenter
        )

        remove = QPushButton("Remove")
        remove.setObjectName("removeButton")
        self._configure_remove_button(remove, game)
        remove.clicked.connect(
            lambda checked=False, item=game: self._remove_game(item)
        )
        actions_layout.addWidget(remove, 0, Qt.AlignmentFlag.AlignVCenter)

        row_layout.addLayout(actions_layout, 0)
        return row

    def _build_grid_card(self, game: Game) -> QFrame:
        running = game.id is not None and self._launcher.is_running(game.id)
        card = QFrame()
        card.setObjectName("gameCard")
        card.setProperty("running", "true" if running else "false")
        card.setFixedWidth(172)
        card.setFixedHeight(175)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 4, 10, 8)
        card_layout.setSpacing(2)

        # Top row with favorite button right-aligned
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()

        favorite = QPushButton("★" if game.favorite else "☆")
        favorite.setObjectName("favoriteButton")
        favorite.setProperty("active", "true" if game.favorite else "false")
        favorite.setToolTip("Unfavorite" if game.favorite else "Favorite")
        favorite.setCursor(Qt.CursorShape.PointingHandCursor)
        favorite.clicked.connect(
            lambda checked=False, item=game: self._toggle_favorite(item)
        )
        top_bar.addWidget(favorite)
        card_layout.addLayout(top_bar)

        # Centered executable icon
        icon_label = QLabel()
        icon_size = 40
        icon_label.setPixmap(self._game_icon(game).pixmap(QSize(icon_size, icon_size)))
        icon_label.setFixedSize(icon_size, icon_size)
        card_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Text group: game name + playtime
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)

        name_label = ElidedLabel(game.name)
        name_label.setObjectName("gameName")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setToolTip(f"{game.name}\n{game.exe_path}")
        text_layout.addWidget(name_label)

        playtime_label = QLabel(format_playtime(game.total_play_seconds))
        playtime_label.setObjectName("gameMeta")
        playtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(playtime_label)

        card_layout.addLayout(text_layout)
        card_layout.addStretch()

        # Compact launch/remove actions centered at bottom
        bottom_actions = QHBoxLayout()
        bottom_actions.setSpacing(6)
        bottom_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_actions.addWidget(self._launch_button(game))
        bottom_actions.addWidget(self._edit_button(game))

        remove = QPushButton("Remove")
        remove.setObjectName("removeButton")
        self._configure_remove_button(remove, game)
        remove.clicked.connect(
            lambda checked=False, item=game: self._remove_game(item)
        )
        bottom_actions.addWidget(remove)
        card_layout.addLayout(bottom_actions)

        return card

    def _toggle_favorite(self, game: Game) -> None:
        if game.id is not None and self._database.set_favorite(
            game.id, not game.favorite
        ):
            self.refresh()

    def _remove_game(self, game: Game) -> None:
        if game.id is not None and self._launcher.is_running(game.id):
            QMessageBox.information(
                self,
                "Game Is Running",
                f'"{game.name}" cannot be removed while it is running.\n\nPlease close the game first.',
            )
            return
        answer = QMessageBox.question(
            self,
            "Remove Game",
            f'Remove "{game.name}" from LitePlay?\n\nThe game files will not be deleted.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes and game.id is not None:
            self._database.remove_game(game.id)
            self.refresh()

    def _edit_game(self, game: Game) -> None:
        if game.id is None or self._launcher.is_running(game.id):
            return
        dialog = EditGameDialog(game, self)
        if dialog.exec() != EditGameDialog.DialogCode.Accepted:
            return
        name, exe_path = dialog.values
        if self._database.update_game(game.id, name, exe_path):
            self.refresh()

    def _edit_button(self, game: Game) -> QPushButton:
        running = game.id is not None and self._launcher.is_running(game.id)
        button = QPushButton("Edit")
        button.setObjectName("editButton")
        button.setEnabled(not running)
        button.setToolTip(
            "A running game cannot be edited" if running else f"Edit {game.name}"
        )
        button.setCursor(
            Qt.CursorShape.ArrowCursor if running else Qt.CursorShape.PointingHandCursor
        )
        button.clicked.connect(
            lambda checked=False, item=game: self._edit_game(item)
        )
        return button

    def _launch_button(self, game: Game) -> QPushButton:
        running = game.id is not None and self._launcher.is_running(game.id)
        button = QPushButton("Running" if running else "Launch")
        button.setObjectName("launchButton")
        button.setProperty("running", "true" if running else "false")
        button.setEnabled(not running)
        button.setCursor(
            Qt.CursorShape.ArrowCursor if running else Qt.CursorShape.PointingHandCursor
        )
        button.setToolTip("Game is running" if running else f"Launch {game.name}")
        button.clicked.connect(
            lambda checked=False, item=game: self._launcher.launch(item)
        )
        return button

    def _configure_remove_button(self, button: QPushButton, game: Game) -> None:
        running = game.id is not None and self._launcher.is_running(game.id)
        button.setEnabled(not running)
        if running:
            button.setToolTip("A running game cannot be removed")
            button.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            button.setToolTip(f"Remove {game.name} from LitePlay")
            button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_game_state_changed(self, game_id: int) -> None:
        self.refresh()

    def _on_game_finished(self, game_id: int, duration_seconds: int) -> None:
        self.refresh()

    def _calculate_columns(self) -> int:
        viewport_w = self.grid_scroll.viewport().width()
        page_w = self.width() - 56 - 12
        available_width = max(viewport_w, page_w)
        card_width = 172
        spacing = 12
        return max(1, available_width // (card_width + spacing))

    def _rebuild_grid(self) -> None:
        columns = self._calculate_columns()

        if columns == self._grid_columns and self.grid_layout.count() and self._games:
            return

        self._grid_columns = columns
        self._clear_layout(self.grid_layout)
        for index, game in enumerate(self._games):
            self.grid_layout.addWidget(
                self._game_entry(game, grid=True), index // columns, index % columns
            )
        if self._games:
            self.grid_layout.setRowStretch((len(self._games) - 1) // columns + 1, 1)

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._games and self.grid_button.isChecked():
            self._grid_columns = 0
            self._rebuild_grid()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._games:
            columns = self._calculate_columns()
            if columns != self._grid_columns:
                self._grid_columns = 0
                self._rebuild_grid()
