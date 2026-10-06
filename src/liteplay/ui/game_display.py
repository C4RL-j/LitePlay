"""Shared display helpers for persisted games."""

from datetime import datetime, timedelta

from PySide6.QtCore import QFileInfo, QSize, Qt
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtWidgets import QFileIconProvider, QLabel, QSizePolicy, QStyle, QWidget


def format_playtime(total_seconds: int) -> str:
    minutes = max(0, total_seconds) // 60
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def format_last_played(last_played: datetime | None) -> str:
    if not last_played:
        return "Never"
    now = datetime.now()
    if last_played.date() == now.date():
        return f"Today, {last_played.strftime('%H:%M')}"
    if last_played.date() == (now - timedelta(days=1)).date():
        return f"Yesterday, {last_played.strftime('%H:%M')}"
    return last_played.strftime("%b %d, %Y")


def executable_icon(
    provider: QFileIconProvider, style: QStyle, executable_path: str
) -> QIcon:
    icon = provider.icon(QFileInfo(executable_path))
    if icon.isNull():
        return style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    return icon


class ElidedLabel(QLabel):
    """A QLabel that draws its text elided when space is constrained."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def setText(self, text: str) -> None:
        self._text = text
        self.setToolTip(text)
        self.update()

    def text(self) -> str:
        return self._text

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(20, hint.height())

    def sizeHint(self) -> QSize:
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self._text), metrics.height())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(
            self._text, Qt.TextElideMode.ElideRight, max(0, self.width())
        )
        self.style().drawItemText(
            painter,
            self.rect(),
            int(self.alignment() | Qt.TextFlag.TextSingleLine),
            self.palette(),
            self.isEnabled(),
            elided,
            self.foregroundRole(),
        )
