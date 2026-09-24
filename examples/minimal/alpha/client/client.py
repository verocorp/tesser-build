from __future__ import annotations

import typing

import tesser.context as ts


class AddPartRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class AddPartResponse(ts.Response):

    def __init__(self, name: str, standing: str) -> None:
        self.name = name
        self.standing = standing


class CreateWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class CreateWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class ApproveWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class ApproveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


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


ERRORS: typing.Final[tuple[type[WidgetRejected]]] = (WidgetRejected,)


class AlphaClient(ts.Client, typing.Protocol):

    async def add_part(self, add_part_request: AddPartRequest) -> AddPartResponse: ...

    async def create_widget(self, create_widget_request: CreateWidgetRequest) -> CreateWidgetResponse: ...

    async def approve_widget(self, approve_widget_request: ApproveWidgetRequest) -> ApproveWidgetResponse: ...

    async def find_widget(self, find_widget_request: FindWidgetRequest) -> FindWidgetResponse: ...
