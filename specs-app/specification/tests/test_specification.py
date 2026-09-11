from __future__ import annotations

import protocol as protocol
import specification.adapters.handlers as handlers
import specification.component as component


class TestSpecificationContext:

    def test_an_http_add_story_reaches_the_wired_service(self) -> None:
        specification = component.Specification(component.Config(component.Spec(storage="memory")))
        http_response = handlers.HttpHandler(specification.client).add_story(
            protocol.HttpRequest(
                "POST", "/jtbd/j-root/stories", {"jtbd_id": "j-root"}, {}, {},
                b'{"given": "a jtbd exists", "when": "I click add story", "then": "I see it nested"}',
            )
        )
        assert http_response.status_code == 201
        assert http_response.json_body() == {"story_id": "j-root-s0", "level": 1, "position": 0}

    def test_a_second_story_on_the_same_jtbd_takes_the_next_position(self) -> None:
        specification = component.Specification(component.Config(component.Spec(storage="memory")))
        http_handler = handlers.HttpHandler(specification.client)
        http_request = protocol.HttpRequest(
            "POST", "/jtbd/j-root/stories", {"jtbd_id": "j-root"}, {}, {}, b'{"given": "g", "when": "w", "then": "t"}'
        )
        http_handler.add_story(http_request)
        http_response = http_handler.add_story(http_request)
        assert http_response.json_body() == {"story_id": "j-root-s1", "level": 1, "position": 1}
