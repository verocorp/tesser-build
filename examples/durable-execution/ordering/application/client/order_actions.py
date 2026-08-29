from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.ports.order_actions as order_actions


class Client(ts.Client, typing.Protocol):

    def quote(self, request: order_actions.QuoteRequest) -> order_actions.QuoteResponse: ...
