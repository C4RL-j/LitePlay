"""Non-blocking game process launching and session tracking."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import time
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from liteplay.data.database import Database
from liteplay.models.game import Game


@dataclass
class _ActiveProcess:
    process: subprocess.Popen
    session_id: int
    monotonic_started: float


class GameLauncherService(QObject):
    """Launch games and poll their processes without blocking the UI thread."""

    game_started = Signal(int)
    game_finished = Signal(int, int)
    launch_failed = Signal(int, str)

    def __init__(
        self,
        database: Database,
        parent: QObject | None = None,
        *,
        process_factory: Callable = subprocess.Popen,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = datetime.now,
        poll_interval_ms: int = 750,
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._process_factory = process_factory
        self._monotonic = monotonic
        self._now = now
        self._active: dict[int, _ActiveProcess] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self._poll_processes)

    @property
    def active_game_ids(self) -> frozenset[int]:
        """Return the IDs of games currently tracked as running."""
        return frozenset(self._active)

    def is_running(self, game_id: int) -> bool:
        return game_id in self._active

    def launch(self, game: Game) -> bool:
        """Start a game and begin its database session after process creation."""
        if game.id is None:
            self.launch_failed.emit(-1, "The game must be saved before it can launch.")
            return False
        if self.is_running(game.id):
            self.launch_failed.emit(game.id, f'"{game.name}" is already running.')
            return False

        executable = Path(game.exe_path)
        if not executable.is_file():
            self.launch_failed.emit(
                game.id, f'The executable for "{game.name}" could not be found:\n{executable}'
            )
            return False

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = self._process_factory(
                [str(executable)],
                cwd=str(executable.parent),
                shell=False,
                creationflags=creationflags,
            )
        except OSError as error:
            self.launch_failed.emit(game.id, f'Could not launch "{game.name}":\n{error}')
            return False

        started_at = self._now()
        monotonic_started = self._monotonic()
        try:
            session = self._database.begin_session(game.id, started_at)
        except Exception as error:
            self.launch_failed.emit(
                game.id,
                f'"{game.name}" started, but LitePlay could not track it:\n{error}',
            )
            return False

        assert session.id is not None
        self._active[game.id] = _ActiveProcess(
            process=process,
            session_id=session.id,
            monotonic_started=monotonic_started,
        )
        if not self._timer.isActive():
            self._timer.start()
        self.game_started.emit(game.id)
        return True

    def _duration(self, active: _ActiveProcess) -> int:
        return max(0, int(self._monotonic() - active.monotonic_started))

    def _poll_processes(self) -> None:
        for game_id, active in tuple(self._active.items()):
            if active.process.poll() is None:
                continue
            duration = self._duration(active)
            try:
                self._database.finish_session(
                    active.session_id, self._now(), duration
                )
            except Exception as error:
                self.launch_failed.emit(
                    game_id, f"LitePlay could not save the completed session:\n{error}"
                )
                continue
            del self._active[game_id]
            self.game_finished.emit(game_id, duration)
        if not self._active:
            self._timer.stop()

    def finalize_active_sessions(self) -> None:
        """Finalize tracking at shutdown without terminating child processes."""
        self._timer.stop()
        for game_id, active in tuple(self._active.items()):
            duration = self._duration(active)
            self._database.finish_session(active.session_id, self._now(), duration)
            del self._active[game_id]
            self.game_finished.emit(game_id, duration)
