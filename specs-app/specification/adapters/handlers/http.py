from __future__ import annotations

import tesser.adapters as ts

import protocol as protocol
import specification.client as client


class HttpHandler(ts.Handler):

    def __init__(self, specification_client: client.SpecificationClient) -> None:
        self._specification_client = specification_client

    def add_story(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        jtbd_id = http_request.path_param("jtbd_id")
        body = http_request.json_body()
        given = body.get("given")
        if not isinstance(given, str):
            raise protocol.BadRequest("expected a string field: given")
        when = body.get("when")
        if not isinstance(when, str):
            raise protocol.BadRequest("expected a string field: when")
        then = body.get("then")
        if not isinstance(then, str):
            raise protocol.BadRequest("expected a string field: then")
        add_story_response = self._specification_client.add_story(
            client.AddStoryRequest(jtbd_id=jtbd_id, given=given, when=when, then=then)
        )
        return protocol.HttpResponse.json(201, {
            "story_id": add_story_response.story_id,
            "level": add_story_response.level,
            "position": add_story_response.position,
        })
