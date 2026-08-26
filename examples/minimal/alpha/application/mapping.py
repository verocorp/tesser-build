from __future__ import annotations

import tesser.application as ts

import alpha.client.client as client
import alpha.domain.thing as thing


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(self, added: thing.Thing) -> None:
        super().__init__(name=str(added.identity))
