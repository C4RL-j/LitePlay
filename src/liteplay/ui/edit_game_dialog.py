"""Dialog for editing an existing LitePlay game entry."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from liteplay.models.game import Game


def validate_game_edit(name: str, exe_path: str) -> tuple[str, str]:
    """Return normalized edit values, or raise ValueError with a user-facing error."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Game name is required.")

    raw_path = exe_path.strip()
    if not raw_path:
        raise ValueError("Executable path is required.")
    path = Path(raw_path).expanduser().resolve()
    if path.suffix.casefold() != ".exe":
        raise ValueError("Executable path must point to an .exe file.")
    if not path.is_file():
        raise ValueError("Executable file does not exist.")
    return normalized_name, str(path)


class EditGameDialog(QDialog):
    """Edit a game's display name and Windows executable path."""

    def __init__(self, game: Game, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Game")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._validated_values: tuple[str, str] | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_input = QLineEdit(game.name)
        self.name_input.setObjectName("editGameName")
        form.addRow("Game Name", self.name_input)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit(game.exe_path)
        self.path_input.setObjectName("editGamePath")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse)
        path_row.addWidget(self.path_input, 1)
        path_row.addWidget(self.browse_button)
        form.addRow("Executable Path", path_row)
        layout.addLayout(form)

        self.error_label = QLabel()
        self.error_label.setObjectName("editGameError")
        self.error_label.setStyleSheet("color: #ef8b8b;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    @property
    def values(self) -> tuple[str, str]:
        if self._validated_values is None:
            raise RuntimeError("Edit values are only available after a successful save.")
        return self._validated_values

    def _browse(self) -> None:
        current = self.path_input.text().strip()
        start = str(Path(current).parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Game Executable", start, "Windows executables (*.exe)"
        )
        if path:
            self.path_input.setText(path)

    def accept(self) -> None:
        try:
            self._validated_values = validate_game_edit(
                self.name_input.text(), self.path_input.text()
            )
        except ValueError as error:
            self.error_label.setText(str(error))
            self.error_label.show()
            return
        self.error_label.hide()
        super().accept()
