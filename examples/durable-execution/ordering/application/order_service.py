from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain
import tesser.errors as errors

_ALREADY_STARTED: typing.Final[str] = "the order was already started"


class MapToOrderSpecFromSubmitOrderRequest(ts.Mapper, domain.OrderSpec):

    def __init__(self, submit_order_request: client.SubmitOrderRequest) -> None:
        super().__init__(
            order_id=submit_order_request.order_id,
            sku=submit_order_request.sku,
            quantity=submit_order_request.quantity,
        )


class MapToOrderSpecFromPlaceOrderRequest(ts.Mapper, domain.OrderSpec):

    def __init__(self, place_order_request: client.PlaceOrderRequest) -> None:
        super().__init__(
            order_id=place_order_request.order_id,
            sku=place_order_request.sku,
            quantity=place_order_request.quantity,
        )


class MapToSubmitOrderResponse(ts.Mapper, client.SubmitOrderResponse):

    def __init__(self, start_confirm_order_response: relays.StartConfirmOrderResponse) -> None:
        super().__init__(order_id=start_confirm_order_response.order_id)


class MapToPlaceOrderResponse(ts.Mapper, client.PlaceOrderResponse):

    def __init__(self, confirm_order_response: relays.ConfirmOrderResponse) -> None:
        super().__init__(
            order_id=confirm_order_response.order_id,
            total_cents=confirm_order_response.confirmed_orders[0].total_cents,
        )


class OrderService(ts.ApplicationService):

    def __init__(self, confirm_order_relay: relays.ConfirmOrderRelay) -> None:
        self._confirm_order_relay = confirm_order_relay

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        try:
            order = domain.Order(MapToOrderSpecFromSubmitOrderRequest(submit_order_request))
        except errors.DomainError as domain_error:
            raise client.OrderRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        start_confirm_order_response = (
            await self._confirm_order_relay.start_confirm_order(
                relays.ConfirmOrderRequest(order=order)
            )
        )
        match start_confirm_order_response.outcome:  # tesser:debt TB082
            case relays.StartConfirmOrderOutcome.STARTED:
                return MapToSubmitOrderResponse(start_confirm_order_response)
            case _ as never:
                typing.assert_never(never)

    async def place_order(
        self, place_order_request: client.PlaceOrderRequest
    ) -> client.PlaceOrderResponse:
        try:
            order = domain.Order(MapToOrderSpecFromPlaceOrderRequest(place_order_request))
        except errors.DomainError as domain_error:
            raise client.OrderRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        confirm_order_response = await self._confirm_order_relay.run_confirm_order(
            relays.ConfirmOrderRequest(order=order)
        )
        match confirm_order_response.outcome:  # tesser:debt TB082
            case relays.ConfirmOrderOutcome.CONFIRMED:
                return MapToPlaceOrderResponse(confirm_order_response)
            case relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND:
                raise client.ProductPriceNotFound(confirm_order_response.reasons[0])
            case relays.ConfirmOrderOutcome.ALREADY_STARTED:
                raise client.OrderAlreadyStarted(_ALREADY_STARTED)
            case _ as never:
                typing.assert_never(never)
