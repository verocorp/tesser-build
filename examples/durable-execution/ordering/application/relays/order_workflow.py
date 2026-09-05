from __future__ import annotations

import typing

import tesser.application as ts

import ordering.domain.order as domain


class StartRequest(ts.Request):

    order: domain.Order

    def __init__(self, order: domain.Order) -> None:
        self.order = order


class StartResponse(ts.Response):

    order_id: str

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class OrderWorkflow(ts.Relay, typing.Protocol):

    async def start(self, request: StartRequest) -> StartResponse: ...
