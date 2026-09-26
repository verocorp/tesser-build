import tesser.testing as testing


def test_fake_returns_the_same_class_it_decorates() -> None:
    class Double:
        pass

    assert testing.fake(Double) is Double


def test_fake_leaves_the_class_it_decorates_usable() -> None:
    @testing.fake
    class Double:
        def answer(self) -> int:
            return 7

    assert Double().answer() == 7


def test_peer_preserves_the_callable_class_and_its_signature() -> None:
    class Reply:

        def __init__(self, text: str) -> None:
            self.text = text

        def __call__(self, request: int) -> str:
            return self.text * request

    assert testing.peer(Reply) is Reply
    assert testing.peer(Reply)("ok")(2) == "okok"
    assert testing.peer(Reply)("ok").text == "ok"
