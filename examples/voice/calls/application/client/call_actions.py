from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class CallsApplicationClient(ts.Client, typing.Protocol):

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse: ...
