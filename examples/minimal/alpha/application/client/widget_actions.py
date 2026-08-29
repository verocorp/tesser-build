from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports.widget_actions as widget_actions


class Client(ts.Client, typing.Protocol):

    def quote(self, request: widget_actions.QuoteRequest) -> widget_actions.QuoteResponse: ...
