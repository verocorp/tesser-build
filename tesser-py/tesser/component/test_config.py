from tesser.component.config import Config


def test_config_is_a_plain_marker_base() -> None:
    class Concrete(Config):
        pass

    assert issubclass(Concrete, Config)
    assert Config.__mro__[1:] == (object,)


def test_config_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Config) if not name.startswith("__")}
    assert own == set(), own
