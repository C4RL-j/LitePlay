"""Unit tests for the LitePlay data layer."""

from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from liteplay.data.database import Database
from liteplay.models.game import Game
from liteplay.models.session import Session


class TestLitePlayData(unittest.TestCase):
    """Test suite for SQLite-backed storage and domain models."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="liteplay_test_")
        self.db_path = Path(self.temp_dir) / "test_liteplay.db"
        self.db = Database(self.db_path)

    def tearDown(self) -> None:
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization_and_table_creation(self) -> None:
        """Database should create file, enable foreign keys, and create required tables."""
        self.assertTrue(self.db_path.exists())

        conn = self.db._ensure_connected()
        fk_cursor = conn.execute("PRAGMA foreign_keys;")
        self.assertEqual(fk_cursor.fetchone()[0], 1)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = {row[0] for row in cursor.fetchall()}
        self.assertIn("games", tables)
        self.assertIn("sessions", tables)

    def test_add_game_with_model_and_get_by_id(self) -> None:
        """Adding a Game model should persist and return a Game with generated ID."""
        now = datetime.now()
        game = Game(
            name="Hades",
            exe_path="C:/Games/Hades/Hades.exe",
            favorite=True,
            added_at=now,
            last_played=now,
            total_play_seconds=3600,
            launch_count=5,
        )

        saved = self.db.add_game(game)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.name, "Hades")
        self.assertEqual(saved.exe_path, "C:/Games/Hades/Hades.exe")
        self.assertTrue(saved.favorite)
        self.assertEqual(saved.total_play_seconds, 3600)
        self.assertEqual(saved.launch_count, 5)

        retrieved = self.db.get_game_by_id(saved.id)
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved.id, saved.id)
        self.assertEqual(retrieved.name, "Hades")
        self.assertEqual(retrieved.exe_path, "C:/Games/Hades/Hades.exe")
        self.assertTrue(retrieved.favorite)
        self.assertIsInstance(retrieved.added_at, datetime)
        self.assertIsInstance(retrieved.last_played, datetime)
        self.assertEqual(retrieved.total_play_seconds, 3600)
        self.assertEqual(retrieved.launch_count, 5)

    def test_add_game_defaults(self) -> None:
        """Adding a game should apply defaults correctly."""
        game = Game(name="Celeste", exe_path="C:/Games/Celeste/Celeste.exe")
        saved = self.db.add_game(game)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.name, "Celeste")
        self.assertEqual(saved.exe_path, "C:/Games/Celeste/Celeste.exe")
        self.assertFalse(saved.favorite)
        self.assertIsInstance(saved.added_at, datetime)
        self.assertIsNone(saved.last_played)
        self.assertEqual(saved.total_play_seconds, 0)
        self.assertEqual(saved.launch_count, 0)

        retrieved = self.db.get_game_by_id(saved.id)
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertFalse(retrieved.favorite)
        self.assertIsNone(retrieved.last_played)

    def test_add_game_validation_invalid_name(self) -> None:
        """A game must not be persisted with blank or whitespace-only name."""
        with self.assertRaises(ValueError):
            self.db.add_game(Game(name="", exe_path="C:/game.exe"))

        with self.assertRaises(ValueError):
            self.db.add_game(Game(name="   \t  ", exe_path="C:/game.exe"))

    def test_add_game_validation_invalid_exe_path(self) -> None:
        """A game must not be persisted with blank or whitespace-only exe_path."""
        with self.assertRaises(ValueError):
            self.db.add_game(Game(name="Game", exe_path=""))

        with self.assertRaises(ValueError):
            self.db.add_game(Game(name="Game", exe_path="   \n  "))

    def test_add_game_invalid_type(self) -> None:
        """add_game should raise TypeError if non-Game is passed."""
        with self.assertRaises(TypeError):
            self.db.add_game("Not a Game")  # type: ignore[arg-type]

    def test_add_session_invalid_type(self) -> None:
        """add_session should raise TypeError if non-Session is passed."""
        with self.assertRaises(TypeError):
            self.db.add_session("Not a Session")  # type: ignore[arg-type]

    def test_get_game_by_id_not_found(self) -> None:
        """Non-existent game ID should return None."""
        self.assertIsNone(self.db.get_game_by_id(99999))

    def test_list_games(self) -> None:
        """Listing games should return all registered games."""
        self.assertEqual(self.db.list_games(), [])

        g1 = self.db.add_game(Game(name="Game 1", exe_path="C:/g1.exe"))
        g2 = self.db.add_game(
            Game(name="Game 2", exe_path="C:/g2.exe", favorite=True)
        )

        games = self.db.list_games()
        self.assertEqual(len(games), 2)
        game_ids = [g.id for g in games]
        self.assertIn(g1.id, game_ids)
        self.assertIn(g2.id, game_ids)
        self.assertFalse(games[0].favorite)
        self.assertTrue(games[1].favorite)

    def test_dashboard_queries_and_favorite_ordering(self) -> None:
        never = self.db.add_game(
            Game(name="Never", exe_path="C:/never.exe", favorite=False)
        )
        beta = self.db.add_game(
            Game(
                name="beta",
                exe_path="C:/beta.exe",
                favorite=True,
                last_played=datetime(2026, 9, 27, 10, 0),
                total_play_seconds=60,
            )
        )
        alpha = self.db.add_game(
            Game(
                name="Alpha",
                exe_path="C:/alpha.exe",
                favorite=True,
                last_played=datetime(2026, 9, 28, 10, 0),
                total_play_seconds=180,
            )
        )
        gamma = self.db.add_game(
            Game(
                name="Gamma",
                exe_path="C:/gamma.exe",
                last_played=datetime(2026, 9, 26, 10, 0),
                total_play_seconds=120,
            )
        )
        assert never.id is not None
        assert beta.id is not None
        assert alpha.id is not None
        assert gamma.id is not None
        self.db.add_session(Session(game_id=alpha.id, started_at=datetime.now()))
        self.db.add_session(Session(game_id=beta.id, started_at=datetime.now()))

        self.assertEqual(
            [game.name for game in self.db.get_favorite_games()],
            ["Alpha", "beta"],
        )
        self.assertEqual(self.db.count_games(), 4)
        self.assertEqual(self.db.count_favorites(), 2)
        self.assertEqual(self.db.count_sessions(), 2)
        self.assertEqual(self.db.get_total_play_seconds(), 360)
        self.assertEqual(
            [game.name for game in self.db.get_recently_played()],
            ["Alpha", "beta", "Gamma"],
        )
        self.assertNotIn("Never", [g.name for g in self.db.get_recently_played()])
        self.assertEqual(
            [game.name for game in self.db.get_recently_played(2)],
            ["Alpha", "beta"],
        )
        self.assertEqual(
            [game.name for game in self.db.get_most_played()],
            ["Alpha", "Gamma", "beta"],
        )
        self.assertEqual(
            [game.name for game in self.db.get_most_played(2)],
            ["Alpha", "Gamma"],
        )
        self.assertNotIn("Never", [g.name for g in self.db.get_most_played()])

    def test_empty_dashboard_aggregates_and_zero_playtime_ranking(self) -> None:
        self.assertEqual(self.db.count_games(), 0)
        self.assertEqual(self.db.count_sessions(), 0)
        self.assertEqual(self.db.count_favorites(), 0)
        self.assertEqual(self.db.get_total_play_seconds(), 0)
        self.db.add_game(Game(name="Zero", exe_path="C:/zero.exe"))
        self.assertEqual(self.db.get_most_played(), [])

    def test_update_favorite_status(self) -> None:
        """Updating favorite status should modify SQLite record."""
        game = self.db.add_game(
            Game(name="Dead Cells", exe_path="C:/deadcells.exe", favorite=False)
        )
        assert game.id is not None

        updated = self.db.set_favorite(game.id, True)
        self.assertTrue(updated)
        retrieved = self.db.get_game_by_id(game.id)
        assert retrieved is not None
        self.assertTrue(retrieved.favorite)

        updated_again = self.db.set_favorite(game.id, False)
        self.assertTrue(updated_again)
        retrieved_again = self.db.get_game_by_id(game.id)
        assert retrieved_again is not None
        self.assertFalse(retrieved_again.favorite)

        # Non-existent game ID
        self.assertFalse(self.db.set_favorite(99999, True))

    def test_update_game_preserves_identity_statistics_and_sessions(self) -> None:
        added = datetime(2026, 1, 2, 3, 4, 5)
        played = datetime(2026, 2, 3, 4, 5, 6)
        game = self.db.add_game(
            Game(
                name="Old Name",
                exe_path="C:/old.exe",
                favorite=True,
                added_at=added,
                last_played=played,
                total_play_seconds=987,
                launch_count=12,
            )
        )
        assert game.id is not None
        session = self.db.add_session(
            Session(
                game_id=game.id,
                started_at=played,
                ended_at=played,
                duration_seconds=45,
            )
        )

        self.assertTrue(
            self.db.update_game(game.id, "  New Name  ", "  C:/new game.exe  ")
        )

        updated = self.db.get_game_by_id(game.id)
        assert updated is not None
        self.assertEqual(updated.id, game.id)
        self.assertEqual(updated.name, "New Name")
        self.assertEqual(updated.exe_path, "C:/new game.exe")
        self.assertTrue(updated.favorite)
        self.assertEqual(updated.added_at, added)
        self.assertEqual(updated.last_played, played)
        self.assertEqual(updated.total_play_seconds, 987)
        self.assertEqual(updated.launch_count, 12)
        sessions = self.db.list_sessions_for_game(game.id)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].id, session.id)
        self.assertEqual(sessions[0].duration_seconds, 45)

    def test_update_game_invalid_id_and_values(self) -> None:
        self.assertFalse(self.db.update_game(99999, "Missing", "C:/missing.exe"))
        with self.assertRaises(ValueError):
            self.db.update_game(99999, "   ", "C:/missing.exe")
        with self.assertRaises(ValueError):
            self.db.update_game(99999, "Missing", "   ")

    def test_update_game_failure_rolls_back(self) -> None:
        game = self.db.add_game(Game(name="Original", exe_path="C:/original.exe"))
        assert game.id is not None
        conn = self.db._ensure_connected()
        conn.execute(
            """
            CREATE TRIGGER fail_game_edit BEFORE UPDATE OF name ON games
            BEGIN SELECT RAISE(ABORT, 'forced edit failure'); END;
            """
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.update_game(game.id, "Changed", "C:/changed.exe")

        unchanged = self.db.get_game_by_id(game.id)
        assert unchanged is not None
        self.assertEqual(unchanged.name, "Original")
        self.assertEqual(unchanged.exe_path, "C:/original.exe")
        self.assertFalse(self.db.in_transaction)

    def test_remove_game(self) -> None:
        """Removing a game should delete it from SQLite."""
        game = self.db.add_game(Game(name="Tunic", exe_path="C:/tunic.exe"))
        assert game.id is not None

        self.assertTrue(self.db.remove_game(game.id))
        self.assertIsNone(self.db.get_game_by_id(game.id))
        self.assertEqual(len(self.db.list_games()), 0)

        # Deleting again returns False
        self.assertFalse(self.db.remove_game(game.id))

    def test_add_session_and_list_sessions_for_game(self) -> None:
        """Adding sessions should persist and be listable for that game."""
        game = self.db.add_game(
            Game(name="Hollow Knight", exe_path="C:/hk.exe")
        )
        assert game.id is not None

        t1 = datetime(2026, 9, 27, 10, 0, 0)
        t2 = datetime(2026, 9, 27, 11, 30, 0)
        session_1 = Session(
            game_id=game.id,
            started_at=t1,
            ended_at=t2,
            duration_seconds=5400,
        )

        saved_session = self.db.add_session(session_1)
        self.assertIsNotNone(saved_session.id)
        self.assertEqual(saved_session.game_id, game.id)
        self.assertEqual(saved_session.duration_seconds, 5400)

        # Add second session via Session model
        t3 = datetime(2026, 9, 27, 14, 0, 0)
        session_2 = Session(
            game_id=game.id,
            started_at=t3,
            duration_seconds=1200,
        )
        self.db.add_session(session_2)

        sessions = self.db.list_sessions_for_game(game.id)
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0].duration_seconds, 5400)
        self.assertEqual(sessions[0].started_at, t1)
        self.assertEqual(sessions[0].ended_at, t2)
        self.assertEqual(sessions[1].duration_seconds, 1200)
        self.assertEqual(sessions[1].started_at, t3)
        self.assertIsNone(sessions[1].ended_at)

        # Other game has no sessions
        other_game = self.db.add_game(Game(name="Other", exe_path="C:/other.exe"))
        assert other_game.id is not None
        self.assertEqual(self.db.list_sessions_for_game(other_game.id), [])

    def test_begin_and_finish_session_lifecycle_is_idempotent(self) -> None:
        game = self.db.add_game(Game(name="Journey", exe_path="C:/journey.exe"))
        assert game.id is not None
        started = datetime(2026, 9, 28, 10, 0, 0)
        ended = datetime(2026, 9, 28, 10, 1, 5)

        session = self.db.begin_session(game.id, started)
        assert session.id is not None
        sessions = self.db.list_sessions_for_game(game.id)
        self.assertEqual(len(sessions), 1)
        self.assertIsNone(sessions[0].ended_at)
        self.assertEqual(sessions[0].duration_seconds, 0)
        launched_game = self.db.get_game_by_id(game.id)
        assert launched_game is not None
        self.assertEqual(launched_game.launch_count, 1)
        self.assertEqual(launched_game.last_played, started)

        self.assertTrue(self.db.finish_session(session.id, ended, 65))
        finished = self.db.list_sessions_for_game(game.id)[0]
        self.assertEqual(finished.ended_at, ended)
        self.assertEqual(finished.duration_seconds, 65)
        updated_game = self.db.get_game_by_id(game.id)
        assert updated_game is not None
        self.assertEqual(updated_game.total_play_seconds, 65)

        self.assertFalse(self.db.finish_session(session.id, ended, 65))
        self.assertEqual(
            self.db.get_game_by_id(game.id).total_play_seconds, 65  # type: ignore[union-attr]
        )

    def test_begin_session_failure_rolls_back_insert(self) -> None:
        game = self.db.add_game(Game(name="Limbo", exe_path="C:/limbo.exe"))
        assert game.id is not None
        conn = self.db._ensure_connected()
        conn.execute(
            """
            CREATE TRIGGER fail_launch_update BEFORE UPDATE OF launch_count ON games
            BEGIN SELECT RAISE(ABORT, 'forced launch update failure'); END;
            """
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.begin_session(game.id, datetime.now())
        self.assertEqual(self.db.list_sessions_for_game(game.id), [])
        self.assertEqual(self.db.get_game_by_id(game.id).launch_count, 0)  # type: ignore[union-attr]
        self.assertFalse(self.db.in_transaction)

    def test_finish_session_failure_rolls_back_completion(self) -> None:
        game = self.db.add_game(Game(name="Inside", exe_path="C:/inside.exe"))
        assert game.id is not None
        session = self.db.begin_session(game.id, datetime.now())
        assert session.id is not None
        conn = self.db._ensure_connected()
        conn.execute(
            """
            CREATE TRIGGER fail_playtime_update BEFORE UPDATE OF total_play_seconds ON games
            BEGIN SELECT RAISE(ABORT, 'forced playtime update failure'); END;
            """
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.finish_session(session.id, datetime.now(), 10)
        unfinished = self.db.list_sessions_for_game(game.id)[0]
        self.assertIsNone(unfinished.ended_at)
        self.assertEqual(unfinished.duration_seconds, 0)
        self.assertEqual(self.db.get_game_by_id(game.id).total_play_seconds, 0)  # type: ignore[union-attr]
        self.assertFalse(self.db.in_transaction)

    def test_foreign_key_behavior(self) -> None:
        """Foreign key constraint must prevent invalid game_id and cascade on delete."""
        # Non-existent game_id must raise IntegrityError
        invalid_session = Session(
            game_id=99999,
            started_at=datetime.now(),
            duration_seconds=100,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_session(invalid_session)

        # Cascade delete verification
        game = self.db.add_game(
            Game(name="Transistor", exe_path="C:/transistor.exe")
        )
        assert game.id is not None
        self.db.add_session(
            Session(game_id=game.id, started_at=datetime.now(), duration_seconds=300)
        )
        self.assertEqual(len(self.db.list_sessions_for_game(game.id)), 1)

        self.db.remove_game(game.id)
        self.assertEqual(len(self.db.list_sessions_for_game(game.id)), 0)

    def test_transaction_rollback_on_failure(self) -> None:
        """Failed write must roll back, keep in_transaction False, and leave connection usable."""
        # Attempt an invalid foreign-key session
        invalid_session = Session(
            game_id=99999,
            started_at=datetime.now(),
            duration_seconds=100,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_session(invalid_session)

        # Verify transaction was rolled back and is not active
        self.assertFalse(self.db.in_transaction)

        # Verify subsequent valid operations succeed normally
        valid_game = self.db.add_game(
            Game(name="Portal", exe_path="C:/portal.exe")
        )
        self.assertIsNotNone(valid_game.id)
        self.assertFalse(self.db.in_transaction)

        retrieved = self.db.get_game_by_id(valid_game.id)
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved.name, "Portal")

    def test_context_manager_and_closed_connection(self) -> None:
        """Database should support context management and error when closed."""
        db_path = Path(self.temp_dir) / "ctx_test.db"
        with Database(db_path) as db:
            db.add_game(Game(name="Braid", exe_path="C:/braid.exe"))
            self.assertEqual(len(db.list_games()), 1)

        with self.assertRaises(RuntimeError):
            db.list_games()

    def test_games_and_sessions_persist_after_reopening(self) -> None:
        game = self.db.add_game(
            Game(name="Saved Game", exe_path="C:/saved.exe", favorite=True)
        )
        assert game.id is not None
        started = datetime(2026, 9, 28, 10, 0, 0)
        ended = datetime(2026, 9, 28, 10, 1, 0)
        session = self.db.begin_session(game.id, started)
        assert session.id is not None
        self.db.finish_session(session.id, ended, 60)

        self.db.close()
        self.db = Database(self.db_path)

        saved = self.db.get_game_by_id(game.id)
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved.name, "Saved Game")
        self.assertTrue(saved.favorite)
        self.assertEqual(saved.last_played, started)
        self.assertEqual(saved.launch_count, 1)
        self.assertEqual(saved.total_play_seconds, 60)
        self.assertEqual(
            self.db.list_sessions_for_game(game.id),
            [
                Session(
                    id=session.id,
                    game_id=game.id,
                    started_at=started,
                    ended_at=ended,
                    duration_seconds=60,
                )
            ],
        )

    def test_memory_database_does_not_share_saved_games(self) -> None:
        with Database(":memory:") as database:
            database.add_game(Game(name="Temporary Game", exe_path="C:/temp.exe"))
            self.assertEqual(database.count_games(), 1)
        with Database(":memory:") as database:
            self.assertEqual(database.count_games(), 0)
        self.assertEqual(self.db.count_games(), 0)

    def test_datetime_string_handling(self) -> None:
        """Models should accept ISO strings and parse them to datetime instances."""
        added_iso = "2026-09-27T10:00:00"
        last_iso = "2026-09-27T12:00:00"
        game = self.db.add_game(
            Game(
                name="Bastion",
                exe_path="C:/bastion.exe",
                added_at=added_iso,  # type: ignore[arg-type]
                last_played=last_iso,  # type: ignore[arg-type]
            )
        )
        self.assertIsInstance(game.added_at, datetime)
        self.assertIsInstance(game.last_played, datetime)
        self.assertEqual(game.added_at, datetime(2026, 9, 27, 10, 0, 0))
        self.assertEqual(game.last_played, datetime(2026, 9, 27, 12, 0, 0))

        session = self.db.add_session(
            Session(
                game_id=game.id,  # type: ignore[arg-type]
                started_at=added_iso,  # type: ignore[arg-type]
                ended_at=last_iso,  # type: ignore[arg-type]
                duration_seconds=7200,
            )
        )
        self.assertIsInstance(session.started_at, datetime)
        self.assertIsInstance(session.ended_at, datetime)
        self.assertEqual(session.started_at, datetime(2026, 9, 27, 10, 0, 0))
        self.assertEqual(session.ended_at, datetime(2026, 9, 27, 12, 0, 0))


if __name__ == "__main__":
    unittest.main()
