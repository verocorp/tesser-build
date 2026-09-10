from __future__ import annotations

import tesser.adapters as ts

import specification.application.ports as ports


class MemorySpecificationRepository(ts.Repository):

    def __init__(self) -> None:
        self._stories_by_jtbd: dict[str, list[str]] = {}

    def find_jtbd(self, find_jtbd_request: ports.FindJtbdRequest) -> ports.FindJtbdResponse:
        stories = self._stories_by_jtbd.get(find_jtbd_request.jtbd_id, [])
        return ports.FindJtbdResponse(jtbd_id=find_jtbd_request.jtbd_id, level=1, story_count=len(stories))

    def save_story(self, save_story_request: ports.SaveStoryRequest) -> ports.SaveStoryResponse:
        stories = self._stories_by_jtbd.setdefault(save_story_request.jtbd_id, [])
        stories.append(save_story_request.story_id)
        return ports.SaveStoryResponse(story_id=save_story_request.story_id)

    def close(self) -> None:
        self._stories_by_jtbd.clear()
