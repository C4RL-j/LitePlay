"""Lightweight data-integration tests for Dashboard and Favorites pages."""

from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton

from liteplay.data.database import Database
from liteplay.models.game import Game
from liteplay.models.session import Session
from liteplay.services.game_launcher import GameLauncherService
from liteplay.ui.dashboard import DashboardPage
from liteplay.ui.favorites import FavoritesPage
from liteplay.ui.main_window import MainWindow
from liteplay.ui.library import LibraryPage, SORT_NAME_ASCENDING


class FakeProcess:
    def poll(self):
        return None


class AcceptedEditDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, game, parent=None):
        self.values = ("Quake", str(Path(game.exe_path).with_name("Repaired.exe")))

    def exec(self):
        return QDialog.DialogCode.Accepted


class TestIntegratedPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="liteplay_pages_test_"))
        self.executable = self.temp_dir / "Fake.exe"
        self.executable.touch()
        self.db = Database(self.temp_dir / "pages.db")
        self.launcher = GameLauncherService(
            self.db, process_factory=lambda *args, **kwargs: FakeProcess()
        )

    def tearDown(self) -> None:
        self.launcher._timer.stop()
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_favorites_empty_add_and_unfavorite(self) -> None:
        page = FavoritesPage(self.db, self.launcher)
        self.assertIs(page.content_stack.currentWidget(), page.empty_state)
        game = self.db.add_game(
            Game(name="Favorite", exe_path=str(self.executable), favorite=True)
        )
        page.refresh()
        self.assertEqual([item.name for item in page._games], ["Favorite"])
        self.assertIs(page.content_stack.currentWidget(), page.list_scroll)

        page._unfavorite(game)

        self.assertEqual(page._games, [])
        self.assertFalse(self.db.get_game_by_id(game.id).favorite)

    def test_shared_running_state_is_reflected_in_favorites(self) -> None:
        game = self.db.add_game(
            Game(name="Running", exe_path=str(self.executable), favorite=True)
        )
        page = FavoritesPage(self.db, self.launcher)
        self.assertTrue(self.launcher.launch(game))
        self.app.processEvents()
        row = page.list_layout.itemAt(0).widget()
        launch = next(
            button
            for button in row.findChildren(QPushButton)
            if button.objectName() == "launchButton"
        )
        self.assertEqual(launch.text(), "Running")
        self.assertFalse(launch.isEnabled())

    def test_dashboard_uses_real_database_values(self) -> None:
        game = self.db.add_game(
            Game(
                name="Played",
                exe_path=str(self.executable),
                favorite=True,
                last_played=datetime(2026, 9, 28, 12, 0),
                total_play_seconds=125,
            )
        )
        assert game.id is not None
        self.db.add_session(Session(game_id=game.id, started_at=datetime.now()))
        page = DashboardPage(self.db, self.launcher)
        self.assertEqual(page._metrics["Total Games"].text(), "1")
        self.assertEqual(page._metrics["Total Playtime"].text(), "2m")
        self.assertEqual(page._metrics["Total Sessions"].text(), "1")
        self.assertEqual(page._metrics["Favorites"].text(), "1")
        self.assertEqual(page._recent_layout.count(), 1)
        self.assertEqual(page._most_layout.count(), 1)
        self.assertEqual(page._favorites_layout.count(), 1)

    def test_navigation_refreshes_favorites(self) -> None:
        game = self.db.add_game(
            Game(name="Later Favorite", exe_path=str(self.executable))
        )
        window = MainWindow(self.db, self.launcher)
        self.assertEqual(window.pages[2]._games, [])
        self.db.set_favorite(game.id, True)

        window.page_stack.setCurrentIndex(2)

        self.assertEqual([item.name for item in window.pages[2]._games], ["Later Favorite"])

    def test_library_search_sort_and_view_state(self) -> None:
        self.db.add_game(Game(name="Minecraft", exe_path=str(self.executable)))
        self.db.add_game(Game(name="DOOM Eternal", exe_path=str(self.executable)))
        self.db.add_game(Game(name="DOOM 64", exe_path=str(self.executable)))
        page = LibraryPage(self.db, self.launcher)
        self.assertIsNotNone(page.search_input)
        self.assertIsNotNone(page.sort_combo)

        page.search_input.setText(" doom ")
        self.assertEqual(len(page._games), 2)
        sort_index = page.sort_combo.findData(SORT_NAME_ASCENDING)
        page.sort_combo.setCurrentIndex(sort_index)
        self.assertEqual([game.name for game in page._games], ["DOOM 64", "DOOM Eternal"])

        page.grid_button.click()
        self.assertEqual(page.search_input.text(), " doom ")
        self.assertIs(page.content_stack.currentWidget(), page.grid_scroll)
        page.refresh()
        self.assertEqual(page.search_input.text(), " doom ")
        self.assertEqual(page.sort_combo.currentData(), SORT_NAME_ASCENDING)

        page.search_input.clear()
        self.assertEqual(len(page._games), 3)

    def test_library_search_empty_state_differs_from_empty_library(self) -> None:
        empty_page = LibraryPage(self.db, self.launcher)
        self.assertIs(empty_page.content_stack.currentWidget(), empty_page.empty_state)
        self.db.add_game(Game(name="Portal", exe_path=str(self.executable)))
        page = LibraryPage(self.db, self.launcher)
        page.search_input.setText("doom")
        self.assertEqual(page._games, [])
        self.assertIs(
            page.content_stack.currentWidget(), page.search_empty_state
        )

    def test_valid_edit_refreshes_library_and_preserves_search_sort_view(self) -> None:
        repaired = self.temp_dir / "Repaired.exe"
        repaired.touch()
        game = self.db.add_game(
            Game(name="DOOM Eternal", exe_path=str(self.executable), favorite=True)
        )
        page = LibraryPage(self.db, self.launcher)
        page.search_input.setText("doom")
        page.sort_combo.setCurrentIndex(
            page.sort_combo.findData(SORT_NAME_ASCENDING)
        )
        page.grid_button.click()

        with patch("liteplay.ui.library.EditGameDialog", AcceptedEditDialog):
            page._edit_game(game)

        self.assertEqual(page.search_input.text(), "doom")
        self.assertEqual(page.sort_combo.currentData(), SORT_NAME_ASCENDING)
        self.assertTrue(page.grid_button.isChecked())
        self.assertEqual(page._games, [])
        updated = self.db.get_game_by_id(game.id)
        assert updated is not None
        self.assertEqual(updated.name, "Quake")
        self.assertEqual(updated.exe_path, str(repaired))
        self.assertTrue(updated.favorite)

    def test_rename_re_evaluates_active_sort(self) -> None:
        game = self.db.add_game(Game(name="Zulu", exe_path=str(self.executable)))
        repaired = self.temp_dir / "Repaired.exe"
        repaired.touch()
        self.db.add_game(Game(name="Beta", exe_path=str(self.executable)))
        page = LibraryPage(self.db, self.launcher)
        page.sort_combo.setCurrentIndex(
            page.sort_combo.findData(SORT_NAME_ASCENDING)
        )

        with patch("liteplay.ui.library.EditGameDialog", AcceptedEditDialog):
            page._edit_game(game)

        self.assertEqual([item.name for item in page._games], ["Beta", "Quake"])

    def test_edit_is_disabled_while_game_is_running(self) -> None:
        game = self.db.add_game(Game(name="Running", exe_path=str(self.executable)))
        page = LibraryPage(self.db, self.launcher)
        self.assertTrue(self.launcher.launch(game))
        self.app.processEvents()

        for container in (
            page.list_layout.itemAt(0).widget(),
            page.grid_layout.itemAt(0).widget(),
        ):
            edit = next(
                button
                for button in container.findChildren(QPushButton)
                if button.objectName() == "editButton"
            )
            self.assertFalse(edit.isEnabled())

        with patch("liteplay.ui.library.EditGameDialog") as dialog:
            page._edit_game(game)
        dialog.assert_not_called()

    def test_repaired_executable_launches(self) -> None:
        missing = self.db.add_game(
            Game(name="Missing", exe_path=str(self.temp_dir / "missing.exe"))
        )
        self.assertFalse(self.launcher.launch(missing))
        self.assertTrue(
            self.db.update_game(missing.id, "Missing", str(self.executable.resolve()))
        )
        repaired = self.db.get_game_by_id(missing.id)
        assert repaired is not None
        self.assertTrue(self.launcher.launch(repaired))

    def test_favorites_and_dashboard_refresh_after_edit(self) -> None:
        game = self.db.add_game(
            Game(
                name="Before",
                exe_path=str(self.executable),
                favorite=True,
                last_played=datetime(2026, 9, 28, 12, 0),
                total_play_seconds=60,
            )
        )
        repaired = self.temp_dir / "Other.exe"
        repaired.touch()
        favorites = FavoritesPage(self.db, self.launcher)
        dashboard = DashboardPage(self.db, self.launcher)

        self.db.update_game(game.id, "After", str(repaired))
        favorites.refresh()
        dashboard.refresh()

        self.assertEqual(favorites._games[0].name, "After")
        self.assertEqual(favorites._games[0].exe_path, str(repaired))
        favorite_row = favorites.list_layout.itemAt(0).widget()
        self.assertTrue(
            any(label.text() == "After" for label in favorite_row.findChildren(QLabel))
        )
        dashboard_names = [
            label.text()
            for layout in (
                dashboard._recent_layout,
                dashboard._most_layout,
                dashboard._favorites_layout,
            )
            for index in range(layout.count())
            for label in layout.itemAt(index).widget().findChildren(QLabel)
        ]
        self.assertIn("After", dashboard_names)


if __name__ == "__main__":
    unittest.main()
