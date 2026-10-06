"""Database-backed dashboard page."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
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


def _stat_card(label: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setObjectName("statCard")
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    card.setFixedHeight(84)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(4)
    name_label = QLabel(label)
    name_label.setObjectName("statLabel")
    value_label = QLabel("0")
    value_label.setObjectName("statValue")
    value_label.setProperty("metric", label)
    layout.addWidget(name_label)
    layout.addWidget(value_label)
    return card, value_label


def _section(title: str) -> tuple[QFrame, QVBoxLayout]:
    section = QFrame()
    section.setObjectName("sectionCard")
    section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    layout = QVBoxLayout(section)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)
    content = QVBoxLayout()
    content.setSpacing(4)
    content.setContentsMargins(0, 0, 0, 0)
    layout.addLayout(content)
    layout.addStretch()
    return section, content


class DashboardPage(QWidget):
    """Overview page populated from persisted games and sessions."""

    def __init__(
        self,
        database: Database,
        launcher: GameLauncherService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._launcher = launcher
        self._icon_provider = QFileIconProvider()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Your gaming overview")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        layout.addLayout(heading)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self._metrics: dict[str, QLabel] = {}
        for label in ("Total Games", "Total Playtime", "Total Sessions", "Favorites"):
            card, value = _stat_card(label)
            self._metrics[label] = value
            stats.addWidget(card)
        layout.addLayout(stats)

        sections = QHBoxLayout()
        sections.setSpacing(12)
        recent_card, self._recent_layout = _section("Recently Played")
        most_card, self._most_layout = _section("Most Played")
        favorites_card, self._favorites_layout = _section("Favorites")
        sections.addWidget(recent_card)
        sections.addWidget(most_card)
        sections.addWidget(favorites_card)
        layout.addLayout(sections, 1)

        launcher.game_started.connect(self._on_game_state_changed)
        launcher.game_finished.connect(self._on_game_finished)
        self.refresh()

    def refresh(self) -> None:
        self._metrics["Total Games"].setText(str(self._database.count_games()))
        self._metrics["Total Playtime"].setText(
            format_playtime(self._database.get_total_play_seconds())
        )
        self._metrics["Total Sessions"].setText(str(self._database.count_sessions()))
        self._metrics["Favorites"].setText(str(self._database.count_favorites()))
        self._fill_section(
            self._recent_layout,
            self._database.get_recently_played(5),
            "No recent activity recorded.",
            recent=True,
        )
        self._fill_section(
            self._most_layout,
            self._database.get_most_played(5),
            "No playtime recorded yet.",
        )
        self._fill_section(
            self._favorites_layout,
            self._database.get_favorite_games(5),
            "No favorite games yet.",
        )

    def _fill_section(
        self,
        layout: QVBoxLayout,
        games: list[Game],
        empty_message: str,
        *,
        recent: bool = False,
    ) -> None:
        self._clear_layout(layout)
        if not games:
            empty = QLabel(empty_message)
            empty.setObjectName("mutedText")
            empty.setContentsMargins(4, 10, 4, 10)
            layout.addWidget(empty)
            return
        for game in games:
            row = QFrame()
            row.setObjectName("dashboardItem")
            row.setFixedHeight(40)

            running = game.id is not None and self._launcher.is_running(game.id)
            if running:
                row.setProperty("running", "true")

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(8)

            icon = QLabel()
            icon.setFixedSize(22, 22)
            icon.setPixmap(
                executable_icon(self._icon_provider, self.style(), game.exe_path).pixmap(
                    QSize(22, 22)
                )
            )
            row_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

            text = QVBoxLayout()
            text.setSpacing(1)
            text.setContentsMargins(0, 0, 0, 0)

            name = ElidedLabel(game.name)
            name.setObjectName("dashboardGameName")
            name.setToolTip(f"{game.name}\n{game.exe_path}")

            detail = (
                format_last_played(game.last_played)
                if recent
                else format_playtime(game.total_play_seconds)
            )
            if running:
                detail = f"Running  ·  {detail}"

            meta = QLabel(detail)
            meta.setObjectName("dashboardMeta")
            if running:
                meta.setProperty("running", "true")

            text.addWidget(name)
            text.addWidget(meta)
            row_layout.addLayout(text, 1)
            layout.addWidget(row)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _on_game_state_changed(self, game_id: int) -> None:
        self.refresh()

    def _on_game_finished(self, game_id: int, duration_seconds: int) -> None:
        self.refresh()
