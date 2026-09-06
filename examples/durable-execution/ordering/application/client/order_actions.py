from __future__ import annotations  # tesser:debt TB067

import typing

import tesser.application as ts

import ordering.application.relays as relays  # tesser:debt TB067


class OrderingApplicationClient(ts.Client, typing.Protocol):

    def prepare_quote(  # tesser:debt TB081
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse: ...
