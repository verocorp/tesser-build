import asyncio
import typing

import tesser.testing as ts

import tesser.application.job_context as job_context


@ts.fake
class FakeJobContext(job_context.JobContext):

    async def call[I, O](
        self, step: typing.Callable[[typing.Any, I], typing.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


class TestJobContext:

    def test_a_job_context_runs_a_step_it_is_handed(self) -> None:
        async def double(ctx: object, request: int) -> int:
            return request * 2

        assert asyncio.run(FakeJobContext().call(double, 21)) == 42

    def test_job_context_is_a_protocol_base_that_extends_into_new_protocols(self) -> None:
        assert job_context.JobContext in FakeJobContext.__mro__
        assert getattr(job_context.JobContext, "_is_protocol", False)

    def test_job_context_declares_exactly_the_call_shape(self) -> None:
        own = {name for name in vars(job_context.JobContext) if not name.startswith("_")}
        assert own == {"call"}, own
