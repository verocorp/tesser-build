from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def canonical_str(value: str) -> str:
    return value


def canonical_int(value: int) -> int:
    return value


def canonical_float(value: float) -> float:
    return value


def canonical_bytes(value: bytes) -> bytes:
    return value


def canonical_decimal(value: Decimal) -> str:
    return str(value)


def canonical_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("naive datetimes have no canonical form; carry an aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
