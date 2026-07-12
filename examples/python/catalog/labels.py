from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Labels:
    """A collection value object: a set of key/value tags on a product (e.g.
    {"color": "black", "size": "M"}).

    Go wraps a ``map`` and must provide ``Equal`` (a map-backed struct is
    non-comparable). Python's idiom is different: store the entries as an
    immutable, canonicalized ``tuple`` so the frozen dataclass's default
    field-wise equality is content-based *and* the value is hashable. The
    backing tuple is sorted on every construction path (``__post_init__``), so
    two label sets with the same contents in any order are equal, and callers
    receive a fresh ``dict`` — the internal tuple never escapes.
    """

    _values: tuple[tuple[str, str], ...] = field(default=())

    def __post_init__(self) -> None:
        # Canonicalize to sorted order on every construction path, so equality
        # and hashing are content-based regardless of input order.
        object.__setattr__(self, "_values", tuple(sorted(self._values)))

    @classmethod
    def new(cls, values: Mapping[str, str] | None = None) -> "Labels":
        """Construct a Labels, normalizing an absent map to an empty set. No
        error path — an empty set of labels is valid — so there is no ``Must``
        analog to worry about."""
        return cls(tuple((values or {}).items()))

    @classmethod
    def require(cls, values: Mapping[str, str] | None = None) -> "Labels":
        """The constructor variant for a context where at least one label is
        mandatory."""
        if not values:
            raise ValueError("labels must not be empty")
        return cls.new(values)

    def get(self, key: str) -> str | None:
        return dict(self._values).get(key)

    def as_dict(self) -> dict[str, str]:
        """Return a defensive copy — the backing tuple never escapes as a
        mutable structure."""
        return dict(self._values)

    def __len__(self) -> int:
        return len(self._values)
