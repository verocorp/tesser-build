from tesser.declared import fake, function, helper


def test_function_returns_the_same_object_it_decorates() -> None:
    def target() -> int:
        return 7

    assert function(target) is target
    assert function(target)() == 7


def test_helper_returns_the_same_object_it_decorates() -> None:
    def build() -> str:
        return "spec"

    assert helper(build) is build
    assert helper(build)() == "spec"


def test_fake_returns_the_same_class_it_decorates() -> None:
    class Double:
        pass

    assert fake(Double) is Double


def test_the_declarations_are_markers_the_walk_reads_not_behavior() -> None:
    def target(value: int) -> int:
        return value * 2

    for decorator in (function, helper):
        decorated = decorator(target)
        assert decorated(3) == 6
        assert decorated.__name__ == "target"
