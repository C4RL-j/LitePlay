"""Tests for non-blocking game launching and process tracking."""

from datetime import datetime
from pathlib import Path
import shutil
import tempfile
import unittest

from PySide6.QtCore import QCoreApplication

from liteplay.data.database import Database
from liteplay.models.game import Game
from liteplay.services.game_launcher import GameLauncherService


class FakeProcess:
    def __init__(self) -> None:
        self.return_code = None

    def poll(self):
        return self.return_code


class TestGameLauncherService(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="liteplay_launcher_test_"))
        self.executable = self.temp_dir / "Fake Game.exe"
        self.executable.touch()
        self.db = Database(self.temp_dir / "test.db")
        self.game = self.db.add_game(
            Game(name="Fake Game", exe_path=str(self.executable))
        )
        self.process = FakeProcess()
        self.process_calls = []

        def process_factory(*args, **kwargs):
            self.process_calls.append((args, kwargs))
            return self.process

        self.clock_values = iter((10.0, 5.0))
        self.service = GameLauncherService(
            self.db,
            process_factory=process_factory,
            monotonic=lambda: next(self.clock_values),
            now=lambda: datetime(2026, 9, 28, 12, 0, 0),
        )

    def tearDown(self) -> None:
        self.service._timer.stop()
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_executable_fails_without_session(self) -> None:
        missing = self.db.add_game(
            Game(name="Missing", exe_path=str(self.temp_dir / "missing.exe"))
        )
        failures = []
        self.service.launch_failed.connect(lambda game_id, message: failures.append(message))
        self.assertFalse(self.service.launch(missing))
        self.assertTrue(failures)
        self.assertEqual(self.db.list_sessions_for_game(missing.id), [])

    def test_duplicate_launch_is_prevented(self) -> None:
        self.assertTrue(self.service.launch(self.game))
        self.assertFalse(self.service.launch(self.game))
        self.assertEqual(len(self.process_calls), 1)
        self.assertEqual(len(self.db.list_sessions_for_game(self.game.id)), 1)
        self.assertEqual(self.db.get_game_by_id(self.game.id).launch_count, 1)

    def test_completion_clamps_duration_and_clears_active_state(self) -> None:
        completed = []
        self.service.game_finished.connect(
            lambda game_id, duration: completed.append((game_id, duration))
        )
        self.assertTrue(self.service.launch(self.game))
        self.assertTrue(self.service.is_running(self.game.id))
        self.process.return_code = 0

        self.service._poll_processes()

        self.assertFalse(self.service.is_running(self.game.id))
        self.assertEqual(completed, [(self.game.id, 0)])
        session = self.db.list_sessions_for_game(self.game.id)[0]
        self.assertEqual(session.duration_seconds, 0)
        self.assertIsNotNone(session.ended_at)

    def test_shutdown_finalizes_tracking_without_terminating_process(self) -> None:
        self.clock_values = iter((10.0, 15.0))
        self.service._monotonic = lambda: next(self.clock_values)
        self.assertTrue(self.service.launch(self.game))

        self.service.finalize_active_sessions()

        self.assertFalse(self.service.active_game_ids)
        self.assertIsNone(self.process.poll())
        session = self.db.list_sessions_for_game(self.game.id)[0]
        self.assertEqual(session.duration_seconds, 5)
        self.assertIsNotNone(session.ended_at)


if __name__ == "__main__":
    unittest.main()
