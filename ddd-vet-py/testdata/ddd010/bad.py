"""A value object that leaks a primitive through a public field — DDD010.

``Money`` hides its amount (``_amount``), so it is a value object, not a spec —
but it exposes ``currency`` as a public primitive, so callers can read and pass
the raw string around. Hide it (``_currency``): a currency is exposed, if at
all, through an accessor, never a bare public field.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    _amount: str  # hidden — this makes it a value object, not a spec
    currency: str  # public primitive on a value object — the leak (DDD010)

    def __str__(self) -> str:
        return f"{self._amount} {self.currency}"
