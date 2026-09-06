from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays.order_relay as order_relay


class Client(ts.Client, typing.Protocol):

    def quote(self, request: order_relay.QuoteRequest) -> order_relay.QuoteResponse: ...
