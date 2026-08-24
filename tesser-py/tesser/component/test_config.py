import tesser.component.config as config


def test_config_is_a_plain_marker_base() -> None:
    class Concrete(config.Config):
        pass

    assert issubclass(Concrete, config.Config)
    assert config.Config.__mro__[1:] == (object,)


def test_config_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(config.Config) if not name.startswith("__")}
    assert own == set(), own
