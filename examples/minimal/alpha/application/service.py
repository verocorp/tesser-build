from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.mapping as mapping
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.whole_repository as whole_repository
import alpha.client.client as client
import alpha.domain.thing as thing

_NO_PARTS: typing.Final[tuple[thing.PartSpec, ...]] = ()


class AlphaService(ts.ApplicationService):

    def __init__(self, wholes: whole_repository.WholeRepository, checks: beta_check.BetaCheck) -> None:
        self._wholes = wholes
        self._checks = checks

    def add(self, request: client.AddRequest) -> client.AddResponse:
        whole = thing.Whole(
            thing.WholeSpec(
                id=request.id,
                pair=thing.PairSpec(name=request.name, count=request.count),
                parts=_NO_PARTS,
                other=request.id,
            )
        )
        whole_id = str(whole.identity)
        checked = self._checks.check(beta_check.CheckRequest(id=whole_id))
        whole_name = str(whole.pair.name)
        whole_count = int(whole.pair.count)
        save_request = whole_repository.SaveWholeRequest(id=whole_id, name=whole_name, count=whole_count)
        self._wholes.save(save_request)
        return mapping.MapToAddResponse(whole=whole, checked=checked)

    def get(self, request: client.GetRequest) -> client.GetResponse:
        whole_id = thing.Name(request.id)
        whole_id_text = str(whole_id)
        found = self._wholes.find(whole_repository.FindWholeRequest(id=whole_id_text))
        return mapping.MapToGetResponse(found=found)
