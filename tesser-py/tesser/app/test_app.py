import tesser.app.app as app


def test_app_is_a_plain_marker_base() -> None:
    class Concrete(app.App):
        pass

    assert issubclass(Concrete, app.App)
    assert app.App.__mro__[1:] == (object,)


def test_app_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(app.App) if not name.startswith("__")}
    assert own == set(), own
