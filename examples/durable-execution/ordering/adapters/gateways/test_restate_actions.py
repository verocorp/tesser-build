from __future__ import annotations

import asyncio
import typing

import pytest
import restate

import ordering.adapters.gateways.restate_actions as restate_actions
import ordering.application.ports.order_actions as order_actions
import tesser.errors as errors


class TestRestateOrderActions:

    def test_the_quoted_cents_come_back_as_the_ports_response(self) -> None:
        service = restate.Service("OrderingActions")

        @service.handler()
        async def quote(
            ctx: restate.Context, request: order_actions.QuoteRequest
        ) -> order_actions.QuoteResponse:
            return order_actions.QuoteResponse(cents=250)

        class Answering:
            async def service_call(
                self,
                tpe: restate.context.HandlerType[
                    order_actions.QuoteRequest, order_actions.QuoteResponse
                ],
                arg: order_actions.QuoteRequest,
            ) -> order_actions.QuoteResponse:
                return order_actions.QuoteResponse(cents=250)

        gateway = restate_actions.RestateOrderActions(
            typing.cast(restate.Context, Answering()), quote
        )
        quoted = asyncio.run(gateway.quote(order_actions.QuoteRequest(sku="widget")))
        assert quoted.cents == 250

    def test_a_terminal_error_from_the_action_becomes_a_domain_error(self) -> None:
        service = restate.Service("OrderingActions")

        @service.handler()
        async def quote(
            ctx: restate.Context, request: order_actions.QuoteRequest
        ) -> order_actions.QuoteResponse:
            return order_actions.QuoteResponse(cents=250)

        class Refusing:
            async def service_call(
                self,
                tpe: restate.context.HandlerType[
                    order_actions.QuoteRequest, order_actions.QuoteResponse
                ],
                arg: order_actions.QuoteRequest,
            ) -> order_actions.QuoteResponse:
                raise restate.TerminalError("no price for sku 'nope'", status_code=404)

        gateway = restate_actions.RestateOrderActions(
            typing.cast(restate.Context, Refusing()), quote
        )
        with pytest.raises(errors.DomainError):
            asyncio.run(gateway.quote(order_actions.QuoteRequest(sku="nope")))
