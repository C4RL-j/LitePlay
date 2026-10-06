"""Session data model for LitePlay."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Session:
    """Represents a play session for a game in LitePlay."""

    game_id: int
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = 0
    id: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.started_at, str):
            self.started_at = datetime.fromisoformat(self.started_at)
        if isinstance(self.ended_at, str):
            self.ended_at = datetime.fromisoformat(self.ended_at)
