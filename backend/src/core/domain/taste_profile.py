"""Domain entity for taste profiles."""

from dataclasses import dataclass, field


@dataclass
class TasteProfileEntity:
    device_id: str
    genre_weights: dict[str, float] = field(default_factory=dict)
    pacing_preference: str = "balanced"  # ease_in / start_heavy / balanced
    disliked_genres: list[str] = field(default_factory=list)
    preferred_providers: list[str] = field(default_factory=list)
    avg_session_length_minutes: int | None = None
    onboarding_completed: bool = False

    def boost_genre(self, genre: str, amount: float = 0.1) -> None:
        current = self.genre_weights.get(genre, 0.5)
        self.genre_weights[genre] = min(1.0, current + amount)

    def suppress_genre(self, genre: str, amount: float = 0.1) -> None:
        current = self.genre_weights.get(genre, 0.5)
        self.genre_weights[genre] = max(0.0, current - amount)

    def get_top_genres(self, n: int = 5) -> list[str]:
        sorted_genres = sorted(self.genre_weights.items(), key=lambda x: x[1], reverse=True)
        return [g for g, _ in sorted_genres[:n]]
