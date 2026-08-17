from tesser.testing.fake import fake


def test_fake_returns_the_same_class_it_decorates() -> None:
    class Double:
        pass

    assert fake(Double) is Double


def test_fake_leaves_the_class_it_decorates_usable() -> None:
    @fake
    class Double:
        def answer(self) -> int:
            return 7

    assert Double().answer() == 7
