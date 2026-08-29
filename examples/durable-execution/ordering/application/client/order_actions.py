from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.ports.quoting as quoting


class Client(ts.Client, typing.Protocol):

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse: ...
