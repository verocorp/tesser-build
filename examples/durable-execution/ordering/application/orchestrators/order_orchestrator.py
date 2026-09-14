from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays
import ordering.domain as domain


class MapToPriceProductRequest(ts.Mapper, relays.PriceProductRequest):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(sku=str(order.sku))


class MapToPriceSpec(ts.Mapper, domain.PriceSpec):

    def __init__(self, price_product_response: relays.PriceProductResponse) -> None:
        super().__init__(cents=price_product_response.prices[0].cents)


class MapToConfirmOrderResponseFromPrice(ts.Mapper, relays.ConfirmOrderResponse):

    def __init__(self, order: domain.Order, price: domain.Price) -> None:
        super().__init__(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=str(order.identity),
            confirmed_orders=(relays.ConfirmedOrder(total_cents=int(price)),),
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

    def __init__(self, order_actions_runner: relays.OrderActionsRunner) -> None:
        self._order_actions_runner = order_actions_runner

    async def confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        order = confirm_order_request.order
        price_product_response = await self._order_actions_runner.run_price_product(
            MapToPriceProductRequest(order)
        )
        match price_product_response.outcome:  # tesser:debt TB082
            case relays.PriceProductOutcome.PRICED:
                price = order.total(MapToPriceSpec(price_product_response))
                return MapToConfirmOrderResponseFromPrice(order, price)
            case relays.PriceProductOutcome.PRICE_NOT_FOUND:
                return MapToConfirmOrderResponseFromPriceProductResponse(
                    order, price_product_response
                )
            case _ as never:
                typing.assert_never(never)
