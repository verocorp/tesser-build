from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports as ports


class Client(ts.Client, typing.Protocol):

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse: ...
