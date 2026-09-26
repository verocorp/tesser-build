import tesser.testing as testing


class Scaled:

    def __init__(self, factor: int) -> None:
        self.factor = factor

    def __call__(self, value: int) -> int:
        return self.factor * value


def test_helper_returns_the_same_object_it_decorates() -> None:
    assert testing.helper(str.lower) is str.lower
    assert testing.helper(str.lower)("SPEC") == "spec"


def test_helper_is_a_marker_the_walk_reads_not_behavior() -> None:
    assert testing.helper(testing.assembly) is testing.assembly
    assert testing.helper(testing.assembly)(str.upper)("spec") == "SPEC"
    assert testing.helper(testing.assembly).__name__ == "assembly"


def test_assembly_returns_the_same_object_it_decorates() -> None:
    assert testing.assembly(str.upper) is str.upper
    assert testing.assembly(str.upper)("spec") == "SPEC"


def test_markers_preserve_a_callable_objects_type_and_attributes() -> None:
    scaled = Scaled(3)

    assert testing.helper(scaled) is scaled
    assert testing.helper(scaled).factor == 3
    assert testing.helper(scaled)(4) == 12
    assert testing.assembly(scaled) is scaled
    assert testing.assembly(scaled).factor == 3
    assert testing.assembly(scaled)(4) == 12
