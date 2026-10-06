"""SQLite database storage layer for LitePlay."""

from dataclasses import replace
from datetime import datetime
import os
from pathlib import Path
import sqlite3

from liteplay.models.game import Game
from liteplay.models.session import Session


def get_default_db_path() -> Path:
    """Return LitePlay's original platform-specific database location."""
    app_data = os.environ.get("APPDATA")
    directory = Path(app_data) / "LitePlay" if app_data else Path.home() / ".liteplay"
    return directory / "liteplay.db"


class Database:
    """Store games and sessions, committing each write atomically."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = get_default_db_path() if db_path is None else db_path
        if str(self._db_path) != ":memory:":
            self._db_path = Path(self._db_path)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection | None = sqlite3.connect(
            str(self._db_path)
        )
        self._connection.row_factory = sqlite3.Row
        try:
            self._connection.execute("PRAGMA foreign_keys = ON;")
            self._create_tables()
        except Exception:
            self.close()
            raise

    @property
    def in_transaction(self) -> bool:
        return self._ensure_connected().in_transaction

    def _ensure_connected(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Database connection is closed.")
        return self._connection

    def _create_tables(self) -> None:
        self._ensure_connected().executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exe_path TEXT NOT NULL,
                favorite INTEGER NOT NULL DEFAULT 0,
                added_at TEXT NOT NULL,
                last_played TEXT,
                total_play_seconds INTEGER NOT NULL DEFAULT 0,
                launch_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
            );
            """
        )

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "Database":
        self._ensure_connected()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @staticmethod
    def _game_from_row(row: sqlite3.Row) -> Game:
        values = dict(row)
        values["favorite"] = bool(values["favorite"])
        return Game(**values)

    @staticmethod
    def _validate_game_values(name: str, exe_path: str) -> tuple[str, str]:
        name, exe_path = name.strip(), exe_path.strip()
        if not name:
            raise ValueError("Game name cannot be blank or whitespace-only.")
        if not exe_path:
            raise ValueError("Game exe_path cannot be blank or whitespace-only.")
        return name, exe_path

    def add_game(self, game: Game) -> Game:
        """Persist a game and return a copy with its generated ID."""
        if not isinstance(game, Game):
            raise TypeError(f"Expected Game instance, got {type(game).__name__}")
        name, exe_path = self._validate_game_values(game.name, game.exe_path)
        added_at = game.added_at or datetime.now()
        connection = self._ensure_connected()
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO games (
                    name, exe_path, favorite, added_at, last_played,
                    total_play_seconds, launch_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    name,
                    exe_path,
                    int(bool(game.favorite)),
                    added_at.isoformat(),
                    game.last_played.isoformat() if game.last_played else None,
                    game.total_play_seconds,
                    game.launch_count,
                ),
            )
        return replace(
            game,
            id=cursor.lastrowid,
            name=name,
            exe_path=exe_path,
            favorite=bool(game.favorite),
            added_at=added_at,
        )

    def get_game_by_id(self, game_id: int) -> Game | None:
        row = self._ensure_connected().execute(
            "SELECT * FROM games WHERE id = ?;", (game_id,)
        ).fetchone()
        return self._game_from_row(row) if row is not None else None

    def _query_games(self, query: str, limit: int | None = None) -> list[Game]:
        parameters: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            parameters = (max(0, int(limit)),)
        rows = self._ensure_connected().execute(query, parameters)
        return [self._game_from_row(row) for row in rows]

    def list_games(self) -> list[Game]:
        return self._query_games("SELECT * FROM games ORDER BY id ASC")

    def get_favorite_games(self, limit: int | None = None) -> list[Game]:
        return self._query_games(
            "SELECT * FROM games WHERE favorite = 1 "
            "ORDER BY name COLLATE NOCASE ASC, id ASC",
            limit,
        )

    def get_recently_played(self, limit: int = 5) -> list[Game]:
        return self._query_games(
            "SELECT * FROM games WHERE last_played IS NOT NULL "
            "ORDER BY last_played DESC, id ASC",
            limit,
        )

    def get_most_played(self, limit: int = 5) -> list[Game]:
        return self._query_games(
            "SELECT * FROM games WHERE total_play_seconds > 0 "
            "ORDER BY total_play_seconds DESC, name COLLATE NOCASE ASC, id ASC",
            limit,
        )

    def count_games(self) -> int:
        return self._ensure_connected().execute(
            "SELECT COUNT(*) FROM games;"
        ).fetchone()[0]

    def count_sessions(self) -> int:
        return self._ensure_connected().execute(
            "SELECT COUNT(*) FROM sessions;"
        ).fetchone()[0]

    def count_favorites(self) -> int:
        return self._ensure_connected().execute(
            "SELECT COUNT(*) FROM games WHERE favorite = 1;"
        ).fetchone()[0]

    def get_total_play_seconds(self) -> int:
        return self._ensure_connected().execute(
            "SELECT COALESCE(SUM(total_play_seconds), 0) FROM games;"
        ).fetchone()[0]

    def set_favorite(self, game_id: int, favorite: bool) -> bool:
        connection = self._ensure_connected()
        with connection:
            cursor = connection.execute(
                "UPDATE games SET favorite = ? WHERE id = ?;",
                (int(bool(favorite)), game_id),
            )
        return cursor.rowcount > 0

    def update_game(self, game_id: int, name: str, exe_path: str) -> bool:
        """Edit metadata while preserving statistics and related sessions."""
        name, exe_path = self._validate_game_values(name, exe_path)
        connection = self._ensure_connected()
        with connection:
            cursor = connection.execute(
                "UPDATE games SET name = ?, exe_path = ? WHERE id = ?;",
                (name, exe_path, game_id),
            )
        return cursor.rowcount > 0

    def remove_game(self, game_id: int) -> bool:
        connection = self._ensure_connected()
        with connection:
            cursor = connection.execute(
                "DELETE FROM games WHERE id = ?;", (game_id,)
            )
        return cursor.rowcount > 0

    def begin_session(self, game_id: int, started_at: datetime) -> Session:
        """Create a session and record a launch in the same transaction."""
        connection = self._ensure_connected()
        timestamp = started_at.isoformat()
        with connection:
            cursor = connection.execute(
                "INSERT INTO sessions "
                "(game_id, started_at, ended_at, duration_seconds) "
                "VALUES (?, ?, NULL, 0);",
                (game_id, timestamp),
            )
            connection.execute(
                "UPDATE games SET launch_count = launch_count + 1, "
                "last_played = ? WHERE id = ?;",
                (timestamp, game_id),
            )
        return Session(id=cursor.lastrowid, game_id=game_id, started_at=started_at)

    def finish_session(
        self, session_id: int, ended_at: datetime, duration_seconds: int
    ) -> bool:
        """Finish a session once, adding its duration to the game's playtime."""
        connection = self._ensure_connected()
        duration = max(0, int(duration_seconds))
        with connection:
            row = connection.execute(
                "SELECT game_id FROM sessions WHERE id = ? AND ended_at IS NULL;",
                (session_id,),
            ).fetchone()
            if row is None:
                return False
            cursor = connection.execute(
                "UPDATE sessions SET ended_at = ?, duration_seconds = ? "
                "WHERE id = ? AND ended_at IS NULL;",
                (ended_at.isoformat(), duration, session_id),
            )
            if cursor.rowcount != 1:
                return False
            connection.execute(
                "UPDATE games SET total_play_seconds = total_play_seconds + ? "
                "WHERE id = ?;",
                (duration, row["game_id"]),
            )
        return True

    def add_session(self, session: Session) -> Session:
        if not isinstance(session, Session):
            raise TypeError(f"Expected Session instance, got {type(session).__name__}")
        started_at = session.started_at or datetime.now()
        connection = self._ensure_connected()
        with connection:
            cursor = connection.execute(
                "INSERT INTO sessions "
                "(game_id, started_at, ended_at, duration_seconds) "
                "VALUES (?, ?, ?, ?);",
                (
                    session.game_id,
                    started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.duration_seconds,
                ),
            )
        return replace(session, id=cursor.lastrowid, started_at=started_at)

    def list_sessions_for_game(self, game_id: int) -> list[Session]:
        rows = self._ensure_connected().execute(
            "SELECT * FROM sessions WHERE game_id = ? ORDER BY id ASC;",
            (game_id,),
        )
        return [Session(**dict(row)) for row in rows]
