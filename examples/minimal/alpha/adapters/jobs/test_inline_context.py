from __future__ import annotations

import asyncio

import alpha.adapters.jobs.inline_context as inline_context


class TestInlineJobContext:

    def test_call_runs_the_step_in_place(self) -> None:
        async def echo(ctx: object, request: str) -> str:
            return request

        assert asyncio.run(inline_context.InlineJobContext().call(echo, "a")) == "a"
