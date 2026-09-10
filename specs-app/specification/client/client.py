from __future__ import annotations

import typing

import tesser.context as ts


class AddStoryRequest(ts.Request):

    def __init__(self, jtbd_id: str, given: str, when: str, then: str) -> None:
        self.jtbd_id = jtbd_id
        self.given = given
        self.when = when
        self.then = then


class AddStoryResponse(ts.Response):

    def __init__(self, story_id: str, level: int, position: int) -> None:
        self.story_id = story_id
        self.level = level
        self.position = position


class SpecificationClient(ts.Client, typing.Protocol):

    def add_story(self, add_story_request: AddStoryRequest) -> AddStoryResponse: ...
