from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.relays as relays


class AlphaApplicationClient(ts.Client, typing.Protocol):

    def quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse: ...
