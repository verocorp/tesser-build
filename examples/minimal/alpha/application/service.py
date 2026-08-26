from __future__ import annotations

import tesser.application as ts

import alpha.application.mapping as mapping
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.thing_repository as thing_repository
import alpha.client.client as client
import alpha.domain.thing as thing


class AlphaService(ts.ApplicationService):

    def __init__(self, things: thing_repository.ThingRepository, checks: beta_check.BetaCheck) -> None:
        self._things = things
        self._checks = checks

    def add(self, request: client.AddRequest) -> client.AddResponse:
        added = thing.Thing(thing.ThingSpec(name=request.name, part=thing.PartSpec(id=request.name)))
        added_name = str(added.identity)
        self._checks.check(beta_check.CheckRequest(name=added_name))
        self._things.save(thing_repository.SaveRequest(name=added_name))
        return mapping.MapToAddResponse(added=added)
