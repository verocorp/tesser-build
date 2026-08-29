from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts
import restate


class RestateJobContext(ts.JobContext):

    def __init__(self, ctx: restate.Context) -> None:
        self._ctx = ctx

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await self._ctx.service_call(step, request)
