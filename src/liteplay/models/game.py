"""Game data model for LitePlay."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Game:
    """A registered game and its saved play statistics."""

    name: str
    exe_path: str
    favorite: bool = False
    added_at: datetime | None = None
    last_played: datetime | None = None
    total_play_seconds: int = 0
    launch_count: int = 0
    id: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.added_at, str):
            self.added_at = datetime.fromisoformat(self.added_at)
        if isinstance(self.last_played, str):
            self.last_played = datetime.fromisoformat(self.last_played)
