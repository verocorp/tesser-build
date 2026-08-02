from decimal import Decimal

CANONICAL_DECIMAL_MAX_ADJUSTED = 40


def canonical_str(value: str) -> str:
    return value


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite() or abs(value.adjusted()) > CANONICAL_DECIMAL_MAX_ADJUSTED:
        raise ValueError(f"no canonical decimal form: {value}")
    return format(value, "f")
