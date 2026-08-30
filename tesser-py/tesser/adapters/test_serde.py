import tesser.adapters.job as job
import tesser.adapters.serde as serde


def test_serde_is_a_plain_marker_base() -> None:
    class Concrete(serde.Serde):
        pass

    assert issubclass(Concrete, serde.Serde)
    assert serde.Serde.__mro__[1:] == (object,)
    assert not hasattr(serde.Serde, "__slots__")


def test_serde_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(serde.Serde) if not name.startswith("__")}
    assert own == set(), own


def test_a_serde_is_not_a_job() -> None:
    assert not issubclass(serde.Serde, job.Job)
    assert not issubclass(job.Job, serde.Serde)


def test_a_serde_composes_with_an_engine_base() -> None:
    class Engine[T]:
        pass

    class Concrete[T](serde.Serde, Engine[T]):
        pass

    assert issubclass(Concrete, serde.Serde)
    assert issubclass(Concrete, Engine)
