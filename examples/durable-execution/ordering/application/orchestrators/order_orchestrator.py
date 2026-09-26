from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays
import ordering.domain as domain


class MapToPriceProductRequest(ts.Mapper, relays.PriceProductRequest):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(sku=str(order.sku))


class MapToPriceQuoteSpec(ts.Mapper, domain.PriceQuoteSpec):

    def __init__(self, price_product_response: relays.PriceProductResponse) -> None:
        super().__init__(
            outcome=price_product_response.outcome.value,
            prices=tuple(domain.PriceSpec(cents=price.cents) for price in price_product_response.prices),
        )


class MapToOrderConfirmationSpec(ts.Mapper, domain.OrderConfirmationSpec):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(order_id=str(order.identity), quantity=int(order.quantity))


class MapToConfirmOrderResponseFromOrderConfirmation(ts.Mapper, relays.ConfirmOrderResponse):

    def __init__(self, order_confirmation: domain.OrderConfirmation) -> None:
        super().__init__(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=str(order_confirmation.identity),
            confirmed_orders=(relays.ConfirmedOrder(total_cents=int(order_confirmation.total)),),
            reasons=(),
        )


class MapToConfirmOrderResponseFromPriceProductResponse(ts.Mapper, relays.ConfirmOrderResponse):

    def __init__(
        self, order: domain.Order, price_product_response: relays.PriceProductResponse
    ) -> None:
        super().__init__(
            outcome=relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND,
            order_id=str(order.identity),
            confirmed_orders=(),
            reasons=price_product_response.reasons,
        )


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, order_actions_relay: relays.OrderActionsRelay) -> None:
        self._order_actions_relay = order_actions_relay

    async def confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        order = confirm_order_request.order
        order_confirmation = domain.OrderConfirmation(MapToOrderConfirmationSpec(order))
        price_product_response = await self._order_actions_relay.run_price_product(
            MapToPriceProductRequest(order)
        )
        match order_confirmation.confirm(MapToPriceQuoteSpec(price_product_response)):
            case domain.OrderConfirmationOutcome.CONFIRMED:
                return MapToConfirmOrderResponseFromOrderConfirmation(order_confirmation)
            case domain.OrderConfirmationOutcome.PRICE_NOT_FOUND:
                return MapToConfirmOrderResponseFromPriceProductResponse(
                    order, price_product_response
                )
            case _ as never:
                typing.assert_never(never)
