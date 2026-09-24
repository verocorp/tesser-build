from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.relays as relays


class WidgetApplicationClient(ts.Client, typing.Protocol):

    async def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse: ...
