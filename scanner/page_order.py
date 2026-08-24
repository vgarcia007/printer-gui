from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar


Page = TypeVar("Page")


class PageCountMismatch(ValueError):
    def __init__(self, front_count: int, back_count: int) -> None:
        self.front_count = front_count
        self.back_count = back_count
        super().__init__(f"{front_count} front page(s), {back_count} back page(s)")


def assemble_pages(
    fronts: Sequence[Page],
    backs: Sequence[Page] | None,
    is_blank: Callable[[Page], bool],
) -> list[Page]:
    """Pair raw duplex pages before removing blank pages.

    The stack is turned over before scanning its back sides, so the back-side
    files arrive in reverse document order. Blank-page detection must happen
    after pairing: otherwise a blank side can create a false count mismatch.
    """
    raw_fronts = list(fronts)
    if backs is None:
        ordered = raw_fronts
    else:
        raw_backs = list(backs)
        if len(raw_fronts) != len(raw_backs):
            raise PageCountMismatch(len(raw_fronts), len(raw_backs))
        ordered = []
        for front, back in zip(raw_fronts, reversed(raw_backs)):
            ordered.extend((front, back))

    kept = [page for page in ordered if not is_blank(page)]
    return kept or ordered[:1]
