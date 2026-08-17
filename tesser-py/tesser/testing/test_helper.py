from tesser.testing.helper import helper


def test_helper_returns_the_same_object_it_decorates() -> None:
    def build() -> str:
        return "spec"

    assert helper(build) is build
    assert helper(build)() == "spec"


def test_helper_is_a_marker_the_walk_reads_not_behavior() -> None:
    def target(value: int) -> int:
        return value * 2

    decorated = helper(target)

    assert decorated(3) == 6
    assert decorated.__name__ == "target"
