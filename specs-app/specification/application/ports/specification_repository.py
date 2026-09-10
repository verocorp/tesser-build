from __future__ import annotations

import typing

import tesser.application as ts


class FindJtbdRequest(ts.Request):

    def __init__(self, jtbd_id: str) -> None:
        self.jtbd_id = jtbd_id


class FindJtbdResponse(ts.Response):

    def __init__(self, jtbd_id: str, level: int, story_count: int) -> None:
        self.jtbd_id = jtbd_id
        self.level = level
        self.story_count = story_count


class SaveStoryRequest(ts.Request):

    def __init__(self, jtbd_id: str, story_id: str, level: int, position: int, given: str, when: str, then: str) -> None:
        self.jtbd_id = jtbd_id
        self.story_id = story_id
        self.level = level
        self.position = position
        self.given = given
        self.when = when
        self.then = then


class SaveStoryResponse(ts.Response):

    def __init__(self, story_id: str) -> None:
        self.story_id = story_id


class SpecificationRepository(ts.Port, typing.Protocol):

    def find_jtbd(self, find_jtbd_request: FindJtbdRequest) -> FindJtbdResponse: ...

    def save_story(self, save_story_request: SaveStoryRequest) -> SaveStoryResponse: ...
