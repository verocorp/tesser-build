from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts


class InlineJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I  # tesser:debt TB022
    ) -> O:
        return await step(None, request)
