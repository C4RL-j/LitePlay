from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

from liteplay.models.game import Game
from liteplay.ui.library import (
    SORT_MOST_PLAYED,
    SORT_NAME_ASCENDING,
    SORT_NAME_DESCENDING,
    SORT_RECENTLY_ADDED,
    SORT_RECENTLY_PLAYED,
    default_game_name,
    filter_and_sort_games,
    format_last_played,
    format_playtime,
)
from liteplay.ui.edit_game_dialog import validate_game_edit


class TestLibraryHelpers(unittest.TestCase):
    def test_edit_validation_rejects_blank_name_and_invalid_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "Valid Game.exe"
            executable.touch()
            text_file = Path(directory) / "not-a-game.txt"
            text_file.touch()
            with self.assertRaisesRegex(ValueError, "Game name is required"):
                validate_game_edit("   ", str(executable))
            with self.assertRaisesRegex(ValueError, "Executable path is required"):
                validate_game_edit("Game", "   ")
            with self.assertRaisesRegex(ValueError, "does not exist"):
                validate_game_edit("Game", str(Path(directory) / "missing.exe"))
            with self.assertRaisesRegex(ValueError, "must point to an .exe"):
                validate_game_edit("Game", str(text_file))

    def test_edit_validation_trims_name_and_normalizes_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "Game With Spaces.EXE"
            executable.touch()
            name, path = validate_game_edit("  My Game  ", str(executable))
            self.assertEqual(name, "My Game")
            self.assertEqual(path, str(executable.resolve()))

    def test_default_game_name_uses_executable_stem(self) -> None:
        self.assertEqual(default_game_name("C:/Games/Hades/Hades.exe"), "Hades")

    def test_format_playtime(self) -> None:
        self.assertEqual(format_playtime(0), "0m")
        self.assertEqual(format_playtime(65 * 60), "1h 5m")

    def test_format_last_played(self) -> None:
        self.assertEqual(format_last_played(None), "Never")
        now = datetime.now()
        self.assertEqual(
            format_last_played(now), f"Today, {now.strftime('%H:%M')}"
        )
        yesterday = now - timedelta(days=1)
        self.assertEqual(
            format_last_played(yesterday), f"Yesterday, {yesterday.strftime('%H:%M')}"
        )
        past = datetime(2025, 4, 12, 10, 30)
        self.assertEqual(format_last_played(past), "Apr 12, 2025")

    def test_search_is_partial_case_insensitive_and_trimmed(self) -> None:
        games = [
            Game(id=1, name="DOOM Eternal", exe_path="doom.exe"),
            Game(id=2, name="Minecraft", exe_path="minecraft.exe"),
        ]
        self.assertEqual(
            [g.name for g in filter_and_sort_games(games, "  doom  ", SORT_NAME_ASCENDING)],
            ["DOOM Eternal"],
        )
        self.assertEqual(
            [g.name for g in filter_and_sort_games(games, "craft", SORT_NAME_ASCENDING)],
            ["Minecraft"],
        )
        self.assertEqual(len(filter_and_sort_games(games, "  ", SORT_NAME_ASCENDING)), 2)
        self.assertEqual(filter_and_sort_games(games, "portal", SORT_NAME_ASCENDING), [])

    def test_all_sort_modes_are_deterministic(self) -> None:
        same_added = datetime(2026, 1, 1)
        games = [
            Game(
                id=3,
                name="zero",
                exe_path="zero.exe",
                added_at=datetime(2024, 1, 1),
            ),
            Game(
                id=2,
                name="alpha",
                exe_path="alpha2.exe",
                added_at=same_added,
                last_played=datetime(2026, 2, 1),
                total_play_seconds=20,
            ),
            Game(
                id=1,
                name="Alpha",
                exe_path="alpha1.exe",
                added_at=same_added,
                last_played=datetime(2026, 2, 1),
                total_play_seconds=20,
            ),
            Game(
                id=4,
                name="Beta",
                exe_path="beta.exe",
                added_at=datetime(2025, 1, 1),
                last_played=datetime(2026, 3, 1),
                total_play_seconds=40,
            ),
        ]
        self.assertEqual(
            [g.id for g in filter_and_sort_games(games, "", SORT_RECENTLY_ADDED)],
            [1, 2, 4, 3],
        )
        self.assertEqual(
            [g.id for g in filter_and_sort_games(games, "", SORT_NAME_ASCENDING)],
            [1, 2, 4, 3],
        )
        self.assertEqual(
            [g.id for g in filter_and_sort_games(games, "", SORT_NAME_DESCENDING)],
            [3, 4, 1, 2],
        )
        self.assertEqual(
            [g.id for g in filter_and_sort_games(games, "", SORT_RECENTLY_PLAYED)],
            [4, 1, 2, 3],
        )
        self.assertEqual(
            [g.id for g in filter_and_sort_games(games, "", SORT_MOST_PLAYED)],
            [4, 1, 2, 3],
        )

    def test_search_and_sort_are_combined(self) -> None:
        games = [
            Game(
                id=1,
                name="Portal 2",
                exe_path="p2.exe",
                last_played=datetime(2026, 1, 1),
                total_play_seconds=10,
            ),
            Game(
                id=2,
                name="Half-Life 2",
                exe_path="hl2.exe",
                last_played=datetime(2026, 2, 1),
                total_play_seconds=50,
            ),
            Game(id=3, name="Portal", exe_path="p.exe", total_play_seconds=100),
        ]
        self.assertEqual(
            [g.name for g in filter_and_sort_games(games, "2", SORT_NAME_ASCENDING)],
            ["Half-Life 2", "Portal 2"],
        )
        self.assertEqual(
            [g.name for g in filter_and_sort_games(games, "2", SORT_MOST_PLAYED)],
            ["Half-Life 2", "Portal 2"],
        )
        self.assertEqual(
            [g.name for g in filter_and_sort_games(games, "2", SORT_RECENTLY_PLAYED)],
            ["Half-Life 2", "Portal 2"],
        )


if __name__ == "__main__":
    unittest.main()
