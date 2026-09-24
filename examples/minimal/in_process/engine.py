from __future__ import annotations

import collections.abc
import typing


class PromiseNotResolved(Exception):
    pass


class Handler[C, I, O]:

    def __init__(self, container: Service | Workflow, name: str, fn: collections.abc.Callable[[C, I], O]) -> None:
        self.container = container
        self.name = name
        self.fn = fn


class Context:
    pass


class Promise[T]:

    def __init__(self, promises: dict[str, object], name: str) -> None:
        self._promises = promises
        self._name = name

    def value(self) -> T:
        if self._name not in self._promises:
            raise PromiseNotResolved(self._name)
        return typing.cast(T, self._promises[self._name])

    def resolve(self, value: T) -> None:
        self._promises.setdefault(self._name, value)


class WorkflowSharedContext:

    def __init__(self, workflow: Workflow, key: str) -> None:
        self._workflow = workflow
        self._key = key

    def key(self) -> str:
        return self._key

    def promise[T](self, name: str, type_hint: type[T]) -> Promise[T]:
        return Promise(self._workflow.promises.setdefault(self._key, {}), name)


class WorkflowContext(WorkflowSharedContext):

    def service_call[I, O](self, handler: Handler[Context, I, O], arg: I) -> O:
        return service_call(handler, arg)


class Service:

    def __init__(self, name: str) -> None:
        self.name = name
        self.handlers: dict[str, Handler[Context, typing.Any, typing.Any]] = {}

    def handler[I, O](
        self,
    ) -> collections.abc.Callable[[collections.abc.Callable[[Context, I], O]], Handler[Context, I, O]]:
        def register(fn: collections.abc.Callable[[Context, I], O]) -> Handler[Context, I, O]:
            registered = Handler(self, fn.__name__, fn)
            self.handlers[registered.name] = registered
            return registered

        return register


class Workflow:

    def __init__(self, name: str) -> None:
        self.name = name
        self.handlers: dict[str, Handler[typing.Any, typing.Any, typing.Any]] = {}
        self.main_names: set[str] = set()
        self.promises: dict[str, dict[str, object]] = {}

    def main[I, O](
        self,
    ) -> collections.abc.Callable[[collections.abc.Callable[[WorkflowContext, I], O]], Handler[WorkflowContext, I, O]]:
        def register(fn: collections.abc.Callable[[WorkflowContext, I], O]) -> Handler[WorkflowContext, I, O]:
            registered = Handler(self, fn.__name__, fn)
            self.handlers[registered.name] = registered
            self.main_names.add(registered.name)
            return registered

        return register

    def handler[I, O](
        self,
    ) -> collections.abc.Callable[
        [collections.abc.Callable[[WorkflowSharedContext, I], O]], Handler[WorkflowSharedContext, I, O]
    ]:
        def register(fn: collections.abc.Callable[[WorkflowSharedContext, I], O]) -> Handler[WorkflowSharedContext, I, O]:
            registered = Handler(self, fn.__name__, fn)
            self.handlers[registered.name] = registered
            return registered

        return register


def service_call[I, O](handler: Handler[Context, I, O], arg: I) -> O:
    return handler.fn(Context(), arg)


def workflow_call[C: WorkflowSharedContext, I, O](handler: Handler[C, I, O], key: str, arg: I) -> O:
    workflow = handler.container
    if not isinstance(workflow, Workflow):
        raise TypeError(f"{handler.name} is not registered on a workflow")
    context = (
        WorkflowContext(workflow, key) if handler.name in workflow.main_names else WorkflowSharedContext(workflow, key)
    )
    return handler.fn(typing.cast(C, context), arg)
