from tesser.do_not_use_declared import do_not_use_function, load


def test_do_not_use_function_returns_the_same_object_it_decorates() -> None:
    def target() -> int:
        return 7

    assert do_not_use_function(target) is target
    assert do_not_use_function(target)() == 7


def test_load_returns_the_same_object_it_decorates() -> None:
    def target() -> int:
        return 7

    assert load(target) is target
    assert load(target)() == 7


def test_the_declarations_are_markers_the_walk_reads_not_behavior() -> None:
    def target(value: int) -> int:
        return value * 2

    for decorator in (do_not_use_function, load):
        decorated = decorator(target)
        assert decorated(3) == 6
        assert decorated.__name__ == "target"
