"""a module docstring narrating what the imports below already say"""


def double(x: int) -> int:
    """double the input"""
    # multiply by two
    return x * 2


def encode(x: int) -> int:
    # hardcoding=1 is a temporary workaround, not a PEP 263 coding declaration
    y = x + 1
    "prose smuggled as a bare string literal mid-body"
    return y
