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


class PayForOrderRequest(ts.Request):

    def __init__(self, order_id: str, sku: str, quantity: int, payment_method: str) -> None:
        self.order_id = order_id
        self.sku = sku
        self.quantity = quantity
        self.payment_method = payment_method


class PayForOrderResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int, payment_reference: str) -> None:
        self.order_id = order_id
        self.total_cents = total_cents
        self.payment_reference = payment_reference


class OrderRejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProductPriceNotFound(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OrderNotConfirmed(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PaymentDeclined(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OrderAlreadyStarted(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


ERRORS: typing.Final[
    tuple[
        type[OrderRejected],
        type[ProductPriceNotFound],
        type[OrderNotConfirmed],
        type[PaymentDeclined],
        type[OrderAlreadyStarted],
    ]
] = (OrderRejected, ProductPriceNotFound, OrderNotConfirmed, PaymentDeclined, OrderAlreadyStarted)


class OrderingClient(ts.Client, typing.Protocol):

    async def submit_order(self, submit_order_request: SubmitOrderRequest) -> SubmitOrderResponse: ...

    async def place_order(self, place_order_request: PlaceOrderRequest) -> PlaceOrderResponse: ...

    async def pay_for_order(
        self, pay_for_order_request: PayForOrderRequest
    ) -> PayForOrderResponse: ...
