import tesser.do_not_use_declared as do_not_use_declared
import tesser.testing as testing


class Scaled:

    def __init__(self, factor: int) -> None:
        self.factor = factor

    def __call__(self, value: int) -> int:
        return self.factor * value


def test_load_returns_the_same_object_it_decorates() -> None:
    assert do_not_use_declared.load(abs) is abs
    assert do_not_use_declared.load(abs)(-7) == 7


def test_the_declaration_is_a_marker_the_walk_reads_not_behavior() -> None:
    assert do_not_use_declared.load(testing.helper) is testing.helper
    assert do_not_use_declared.load(testing.helper)(str.upper)("spec") == "SPEC"
    assert do_not_use_declared.load(testing.helper).__name__ == "helper"


def test_the_declaration_preserves_a_callable_objects_type_and_attributes() -> None:
    scaled = Scaled(3)

    assert do_not_use_declared.load(scaled) is scaled
    assert do_not_use_declared.load(scaled).factor == 3
    assert do_not_use_declared.load(scaled)(4) == 12
