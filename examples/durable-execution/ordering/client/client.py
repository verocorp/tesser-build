from __future__ import annotations

import typing

import tesser.context as ts


class PlaceRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class PlaceResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class Client(ts.Client, typing.Protocol):

    async def place(self, request: PlaceRequest) -> PlaceResponse: ...


class RunRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class Orchestrator(ts.Client, typing.Protocol):

    async def run(self, request: RunRequest) -> RunResponse: ...


class QuoteRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class QuoteResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class Actions(ts.Client, typing.Protocol):

    def quote(self, request: QuoteRequest) -> QuoteResponse: ...
