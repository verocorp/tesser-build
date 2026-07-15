"""The AST tool CANNOT catch this: field type is a custom class name, not a
literal list/dict/set -- it needs to know the class is unhashable (defines
__eq__ without __hash__, so Python sets its runtime __hash__ to None)."""
from dataclasses import dataclass


class MutableBag:
    def __init__(self, items: list[str]) -> None:
        self.items = items

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MutableBag) and self.items == other.items
    # NOTE: defining __eq__ without __hash__ makes CPython set __hash__ = None
    # at runtime for a plain class -- this is the non-literal unhashable case.


@dataclass(frozen=True)
class Holder:
    bag: MutableBag  # unhashable custom class -- DDD002 (non-literal case)


h = Holder(bag=MutableBag(["x"]))  # valid construction call -- must still typecheck
