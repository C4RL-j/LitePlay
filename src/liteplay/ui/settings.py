"""Settings placeholder page."""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    """Placeholder for future application settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Application preferences")
        subtitle.setObjectName("subtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        layout.addLayout(heading)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(8)

        about_title = QLabel("About LitePlay")
        about_title.setObjectName("sectionTitle")

        app_info = QLabel("LitePlay v0.1.0 — Lightweight local game manager for Windows.")
        app_info.setObjectName("subtitle")

        message = QLabel("Application settings and customization options will be available in future releases.")
        message.setObjectName("mutedText")

        card_layout.addWidget(about_title)
        card_layout.addWidget(app_info)
        card_layout.addWidget(message)

        layout.addWidget(card)
        layout.addStretch()
