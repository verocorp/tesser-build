from __future__ import annotations

import pytest

import tesser.testing as ts

import protocol as protocol
import specification.adapters.handlers as handlers
import specification.client as client


@ts.fake
class FakeSpecificationClient(client.SpecificationClient):

    def __init__(self, story_id: str = "j-root-s0", level: int = 1, position: int = 0) -> None:
        self.story_id = story_id
        self.level = level
        self.position = position
        self.requests: list[client.AddStoryRequest] = []

    def add_story(self, add_story_request: client.AddStoryRequest) -> client.AddStoryResponse:
        self.requests.append(add_story_request)
        return client.AddStoryResponse(story_id=self.story_id, level=self.level, position=self.position)


@ts.helper
def add_story_http_request(
    jtbd_id: str = "j-root", body: str = '{"given": "g", "when": "w", "then": "t"}'
) -> protocol.HttpRequest:
    return protocol.HttpRequest("POST", "/jtbd/j-root/stories", {"jtbd_id": jtbd_id}, {}, {}, body.encode("utf-8"))


class TestHttpHandlerAddStory:

    def test_answers_201_with_the_story_id_level_and_position(self) -> None:
        http_handler = handlers.HttpHandler(FakeSpecificationClient(story_id="j-root-s4", level=1, position=4))
        http_response = http_handler.add_story(add_story_http_request())
        assert http_response.status_code == 201
        assert http_response.json_body() == {"story_id": "j-root-s4", "level": 1, "position": 4}

    def test_forwards_the_jtbd_off_the_path_and_the_three_lines_off_the_body(self) -> None:
        fake_specification_client = FakeSpecificationClient()
        handlers.HttpHandler(fake_specification_client).add_story(add_story_http_request(jtbd_id="j-page-c"))
        request = fake_specification_client.requests[0]
        assert request.jtbd_id == "j-page-c"
        assert (request.given, request.when, request.then) == ("g", "w", "t")

    def test_refuses_a_body_missing_a_line(self) -> None:
        fake_specification_client = FakeSpecificationClient()
        with pytest.raises(protocol.BadRequest):
            handlers.HttpHandler(fake_specification_client).add_story(add_story_http_request(body='{"given": "g"}'))
        assert fake_specification_client.requests == []

    def test_refuses_a_line_that_is_not_a_string(self) -> None:
        fake_specification_client = FakeSpecificationClient()
        with pytest.raises(protocol.BadRequest):
            handlers.HttpHandler(fake_specification_client).add_story(
                add_story_http_request(body='{"given": 1, "when": "w", "then": "t"}')
            )
        assert fake_specification_client.requests == []

    def test_refuses_a_request_with_no_jtbd_on_the_path(self) -> None:
        fake_specification_client = FakeSpecificationClient()
        with pytest.raises(protocol.BadRequest):
            handlers.HttpHandler(fake_specification_client).add_story(add_story_http_request(jtbd_id=""))
        assert fake_specification_client.requests == []
