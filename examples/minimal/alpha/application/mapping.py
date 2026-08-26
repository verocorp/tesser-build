from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.whole_repository as whole_repository
import alpha.client.client as client
import alpha.domain.thing as thing


class MapToWholeView(ts.Mapper, client.WholeView):

    def __init__(self, record: whole_repository.WholeRecord) -> None:
        super().__init__(id=record.id, name=record.name, count=record.count)


class MapToAddedWholeView(ts.Mapper, client.WholeView):

    def __init__(self, whole: thing.Whole) -> None:
        super().__init__(id=str(whole.identity), name=str(whole.pair.name), count=int(whole.pair.count))


class MapToGetResponse(ts.Mapper, client.GetResponse):

    def __init__(self, found: whole_repository.FindWholeResponse) -> None:
        wholes: tuple[client.WholeView, ...]
        match found.outcome:
            case whole_repository.Lookup.PRESENT:
                wholes = tuple(MapToWholeView(record=record) for record in found.wholes)
            case whole_repository.Lookup.ABSENT:
                wholes = ()
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(wholes=wholes)


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(self, whole: thing.Whole, checked: beta_check.CheckResponse) -> None:
        wholes: tuple[client.WholeView, ...]
        match checked.verdict:
            case beta_check.Verdict.OK:
                wholes = (MapToAddedWholeView(whole=whole),)
            case beta_check.Verdict.REFUSED:
                wholes = ()
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(wholes=wholes)
