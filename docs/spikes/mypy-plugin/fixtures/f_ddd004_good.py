def check(a: object, b: object) -> None:
    assert a == b               # compare by value
    _ = str(a)                  # a lone display call is fine
    assert str(a) == "USD 100"  # comparing against a literal is fine
