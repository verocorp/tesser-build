from __future__ import annotations

import typing

import tesser.context as ts


class SubmitOrderRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class SubmitOrderResponse(ts.Response):

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class PlaceOrderRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class PlaceOrderResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class PurchaseRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity


class PurchaseResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int, payment_reference: str) -> None:
        self.order_id = order_id
        self.total_cents = total_cents
        self.payment_reference = payment_reference


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Missing(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Conflict(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Unavailable(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


ERRORS: typing.Final[
    tuple[type[Rejected], type[Missing], type[Conflict], type[Unavailable]]
] = (Rejected, Missing, Conflict, Unavailable)


class OrderingClient(ts.Client, typing.Protocol):

    async def submit_order(self, submit_order_request: SubmitOrderRequest) -> SubmitOrderResponse: ...

    async def place_order(self, place_order_request: PlaceOrderRequest) -> PlaceOrderResponse: ...

    async def purchase(self, purchase_request: PurchaseRequest) -> PurchaseResponse: ...
