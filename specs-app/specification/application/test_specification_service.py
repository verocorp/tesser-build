from __future__ import annotations

import tesser.testing as ts

import specification.application as application
import specification.application.ports as ports
import specification.client as client


@ts.fake
class FakeSpecificationRepository(ports.SpecificationRepository):

    def __init__(self, level: int = 1, story_count: int = 0) -> None:
        self.level = level
        self.story_count = story_count
        self.found: list[str] = []
        self.saved: list[ports.SaveStoryRequest] = []

    def find_jtbd(self, find_jtbd_request: ports.FindJtbdRequest) -> ports.FindJtbdResponse:
        self.found.append(find_jtbd_request.jtbd_id)
        return ports.FindJtbdResponse(jtbd_id=find_jtbd_request.jtbd_id, level=self.level, story_count=self.story_count)

    def save_story(self, save_story_request: ports.SaveStoryRequest) -> ports.SaveStoryResponse:
        self.saved.append(save_story_request)
        return ports.SaveStoryResponse(story_id=save_story_request.story_id)


@ts.helper
def add_story_request(
    jtbd_id: str = "j-root", given: str = "a jtbd exists", when: str = "I click add story", then: str = "I see it nested"
) -> client.AddStoryRequest:
    return client.AddStoryRequest(jtbd_id=jtbd_id, given=given, when=when, then=then)


class TestSpecificationService:

    def test_add_story_answers_the_story_id_its_level_and_its_position(self) -> None:
        specification_service = application.SpecificationService(FakeSpecificationRepository(level=2, story_count=3))
        add_story_response = specification_service.add_story(add_story_request(jtbd_id="j-page-c"))
        assert add_story_response.story_id == "j-page-c-s3"
        assert add_story_response.level == 2
        assert add_story_response.position == 3

    def test_the_jtbd_named_by_the_request_is_the_one_looked_up(self) -> None:
        fake_specification_repository = FakeSpecificationRepository()
        application.SpecificationService(fake_specification_repository).add_story(add_story_request(jtbd_id="j-page-c"))
        assert fake_specification_repository.found == ["j-page-c"]

    def test_the_story_is_saved_under_its_jtbd_with_its_lines(self) -> None:
        fake_specification_repository = FakeSpecificationRepository()
        application.SpecificationService(fake_specification_repository).add_story(
            add_story_request(given="g", when="w", then="t")
        )
        saved = fake_specification_repository.saved[0]
        assert saved.jtbd_id == "j-root"
        assert saved.story_id == "j-root-s0"
        assert saved.position == 0
        assert (saved.given, saved.when, saved.then) == ("g", "w", "t")
