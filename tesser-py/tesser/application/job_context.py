import collections.abc as abc
import typing


class JobContext(typing.Protocol):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O: ...
