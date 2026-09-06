from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays.order_job_context as order_job_context


class Client(ts.Client, typing.Protocol):

    def quote(self, request: order_job_context.QuoteRequest) -> order_job_context.QuoteResponse: ...
