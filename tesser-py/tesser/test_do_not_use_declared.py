from tesser.do_not_use_declared import load


def test_load_returns_the_same_object_it_decorates() -> None:
    def target() -> int:
        return 7

    assert load(target) is target
    assert load(target)() == 7


def test_the_declaration_is_a_marker_the_walk_reads_not_behavior() -> None:
    def target(value: int) -> int:
        return value * 2

    decorated = load(target)
    assert decorated(3) == 6
    assert decorated.__name__ == "target"
