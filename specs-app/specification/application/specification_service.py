from __future__ import annotations

import tesser.application as ts

import specification.application.ports as ports
import specification.client as client
import specification.domain as domain


class MapToFindJtbdRequest(ts.Mapper, ports.FindJtbdRequest):

    def __init__(self, identity: domain.Identity) -> None:
        super().__init__(jtbd_id=str(identity))


class MapToJtbdSpec(ts.Mapper, domain.JtbdSpec):

    def __init__(self, find_jtbd_response: ports.FindJtbdResponse) -> None:
        super().__init__(
            id=find_jtbd_response.jtbd_id,
            level=find_jtbd_response.level,
            story_count=find_jtbd_response.story_count,
        )


class MapToStorySpec(ts.Mapper, domain.StorySpec):

    def __init__(self, add_story_request: client.AddStoryRequest) -> None:
        super().__init__(given=add_story_request.given, when=add_story_request.when, then=add_story_request.then)


class MapToSaveStoryRequest(ts.Mapper, ports.SaveStoryRequest):

    def __init__(self, jtbd: domain.Jtbd, placement: domain.Placement, story: domain.Story) -> None:
        super().__init__(
            jtbd_id=str(jtbd.identity),
            story_id=str(placement.identity),
            level=int(placement.level),
            position=int(placement.position),
            given=str(story.given),
            when=str(story.when),
            then=str(story.then),
        )


class MapToAddStoryResponse(ts.Mapper, client.AddStoryResponse):

    def __init__(self, placement: domain.Placement) -> None:
        super().__init__(
            story_id=str(placement.identity),
            level=int(placement.level),
            position=int(placement.position),
        )


class SpecificationService(ts.ApplicationService):

    def __init__(self, specification_repository: ports.SpecificationRepository) -> None:
        self._specification_repository = specification_repository

    def add_story(self, add_story_request: client.AddStoryRequest) -> client.AddStoryResponse:
        identity = domain.Identity(add_story_request.jtbd_id)
        find_jtbd_response = self._specification_repository.find_jtbd(MapToFindJtbdRequest(identity))
        jtbd = domain.Jtbd(MapToJtbdSpec(find_jtbd_response))
        story = domain.Story(MapToStorySpec(add_story_request))
        placement = jtbd.add_story(story)
        self._specification_repository.save_story(MapToSaveStoryRequest(jtbd, placement, story))
        return MapToAddStoryResponse(placement)
