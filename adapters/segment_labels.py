"""Segment-label mapping between modules.

Module 1 (segmentation) and Module 2 (automation) use Title-Case labels with
spaces. Module 3 (analytics) uses snake_case. This is the single source of truth
for translating between them so the pipeline never silently mismatches a segment.
"""

from __future__ import annotations

# M1 / M2 canonical labels  ->  M3 canonical labels
TITLE_TO_SNAKE: dict[str, str] = {
    "High Intent": "high_intent",
    "Low Engagement": "low_engagement",
    "Price Sensitive": "price_sensitive",
    "Loyal Customer": "loyal_customer",
    "New Cold User": "new_cold_customer",
}

SNAKE_TO_TITLE: dict[str, str] = {v: k for k, v in TITLE_TO_SNAKE.items()}

# The five labels every module must agree on.
CANONICAL_TITLE = list(TITLE_TO_SNAKE.keys())
CANONICAL_SNAKE = list(TITLE_TO_SNAKE.values())


def to_snake(label: str) -> str:
    """Title-Case segment -> snake_case (unknown labels pass through unchanged)."""
    return TITLE_TO_SNAKE.get(label, label)


def to_title(label: str) -> str:
    """snake_case segment -> Title-Case (unknown labels pass through unchanged)."""
    return SNAKE_TO_TITLE.get(label, label)


def validate_titles(labels) -> None:
    """Raise if any label is outside the agreed set (catches integration drift)."""
    unknown = set(labels) - set(CANONICAL_TITLE)
    if unknown:
        raise ValueError(
            f"Unknown segment label(s) {sorted(unknown)}; "
            f"expected a subset of {CANONICAL_TITLE}"
        )
