def check(a: object, b: object) -> None:
    assert a == b
    _ = str(a)
    assert str(a) == "USD 100"
