import typing

import tesser.application.job_context as job_context
import tesser.application.port as port
import tesser.application.relay as relay


@typing.runtime_checkable
class _Shaped(job_context.JobContext, typing.Protocol):
    def step(self) -> int: ...


class _Impl:

    def step(self) -> int:
        return 1


def test_a_job_context_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Shaped)
    assert job_context.JobContext not in type(_Impl()).__mro__


def test_job_context_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert job_context.JobContext in _Shaped.__mro__
    assert getattr(job_context.JobContext, "_is_protocol", False)


def test_a_job_context_is_neither_a_port_nor_a_relay() -> None:
    assert port.Port not in job_context.JobContext.__mro__
    assert relay.Relay not in job_context.JobContext.__mro__


def test_job_context_declares_no_call_of_its_own() -> None:
    own = {name for name in vars(job_context.JobContext) if not name.startswith("_")}
    assert own == set(), own
