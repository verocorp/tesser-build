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


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[Rejected]]] = (Rejected,)


class AlphaClient(ts.Client, typing.Protocol):

    def add_part(self, add_part_request: AddPartRequest) -> AddPartResponse: ...

    def create_widget(self, create_widget_request: CreateWidgetRequest) -> CreateWidgetResponse: ...
