import typing

C = typing.TypeVar("C", contravariant=True)
O = typing.TypeVar("O", covariant=True)


class Workflow(typing.Protocol[C, O]):
    def invocation(self, context: C, /) -> typing.AsyncContextManager[O]: ...
