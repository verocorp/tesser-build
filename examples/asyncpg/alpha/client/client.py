from __future__ import annotations

import typing

import tesser.context as ts


class AddPartRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class AddPartResponse(ts.Response):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class TakePartRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class TakePartResponse(ts.Response):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class FindWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class FindWidgetResponse(ts.Response):

    def __init__(self, found: str) -> None:
        self.found = found


class WidgetRejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class WidgetNotFound(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WidgetExists(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


ERRORS: typing.Final[
    tuple[type[WidgetRejected], type[WidgetNotFound], type[WidgetExists]]
] = (WidgetRejected, WidgetNotFound, WidgetExists)


class AlphaClient(ts.Client, typing.Protocol):

    async def add_part(self, add_part_request: AddPartRequest) -> AddPartResponse: ...

    async def take_part(self, take_part_request: TakePartRequest) -> TakePartResponse: ...

    async def find_widget(self, find_widget_request: FindWidgetRequest) -> FindWidgetResponse: ...
