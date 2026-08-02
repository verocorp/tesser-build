from decimal import Decimal


def canonical_str(value: str) -> str:
    return value


def canonical_decimal(value: Decimal) -> str:
    return str(value)
