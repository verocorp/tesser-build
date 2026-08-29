import tesser.adapters.handler as handler
import tesser.adapters.job as job


def test_job_is_a_plain_marker_base() -> None:
    class Concrete(job.Job):
        pass

    assert issubclass(Concrete, job.Job)
    assert job.Job.__mro__[1:] == (object,)
    assert not hasattr(job.Job, "__slots__")


def test_job_is_not_a_handler() -> None:
    assert not issubclass(job.Job, handler.Handler)
    assert not issubclass(handler.Handler, job.Job)


def test_job_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(job.Job) if not name.startswith("__")}
    assert own == set(), own
