from __future__ import annotations

import tesser.testing as ts

import specification.adapters.repositories as repositories
import specification.application.ports as ports


@ts.helper
def save_story_request(
    jtbd_id: str = "j-root", story_id: str = "j-root-s0", position: int = 0
) -> ports.SaveStoryRequest:
    return ports.SaveStoryRequest(
        jtbd_id=jtbd_id, story_id=story_id, level=1, position=position, given="g", when="w", then="t"
    )


class TestMemorySpecificationRepository:

    def test_an_unknown_jtbd_is_found_at_the_user_level_with_no_stories(self) -> None:
        memory_specification_repository = repositories.MemorySpecificationRepository()
        find_jtbd_response = memory_specification_repository.find_jtbd(ports.FindJtbdRequest(jtbd_id="j-root"))
        assert find_jtbd_response.jtbd_id == "j-root"
        assert find_jtbd_response.level == 1
        assert find_jtbd_response.story_count == 0

    def test_a_save_answers_the_saved_story_id(self) -> None:
        memory_specification_repository = repositories.MemorySpecificationRepository()
        save_story_response = memory_specification_repository.save_story(save_story_request())
        assert save_story_response.story_id == "j-root-s0"

    def test_a_saved_story_is_counted_under_its_jtbd(self) -> None:
        memory_specification_repository = repositories.MemorySpecificationRepository()
        memory_specification_repository.save_story(save_story_request())
        memory_specification_repository.save_story(save_story_request(story_id="j-root-s1", position=1))
        find_jtbd_response = memory_specification_repository.find_jtbd(ports.FindJtbdRequest(jtbd_id="j-root"))
        assert find_jtbd_response.story_count == 2

    def test_a_close_forgets_what_was_saved(self) -> None:
        memory_specification_repository = repositories.MemorySpecificationRepository()
        memory_specification_repository.save_story(save_story_request())
        memory_specification_repository.close()
        find_jtbd_response = memory_specification_repository.find_jtbd(ports.FindJtbdRequest(jtbd_id="j-root"))
        assert find_jtbd_response.story_count == 0
