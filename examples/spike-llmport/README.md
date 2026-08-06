# spike-llmport — the LLM tool-call port, single-sourced and total

A workflow application service whose next step is decided by an LLM tool
call, built so that the tool surface is **data owned by the application**,
not code owned by the adapter. One worked context (`scheduling/`, an
appointment-booking flow) in the `ts.*` shell idiom, plus a LiveKit Agents
translation kept deliberately thin.

## The design points, each locked by a test

- **One generic port operation, tools as values.** The LLM surface is
  `llm_tools(booking)` — the allowed tool names for the current workflow
  step, each with its schema. The adapter has zero per-tool code; the
  question "does the adapter implement all N tools?" dissolves.
- **Totality, three ways.** `allowed_tools` is an exhaustive match over
  `Step`; `schema_for` and `parse` are exhaustive matches over `ToolName`;
  the service's command dispatch is an exhaustive match over the command
  union. All four end in `assert_never`, so mypy --strict proves an
  unhandled case at type-check time (`test_tools.py` re-proves it at
  runtime by iterating the enums).
- **Invocation-time values, constrained twice from one source.** The slots
  a caller may choose exist only at request-build time. `schema_for` embeds
  them as a JSON-schema `enum` (constraining generation), and the aggregate
  re-validates on execution (authoritative — state can move between schema
  build and tool execution). Both derive from `booking.offered_slots()`, so
  they cannot drift (`test_the_choose_slot_schema_offers_exactly_the_current_slots`,
  `test_a_slot_taken_between_choice_and_confirm_reoffers_fresh_slots`).
- **Three-way error mapping.** Model-correctable kinds (`validation`,
  `not_found`, `conflict`) map to an LLM-visible message via the exhaustive
  `llm_visible_message`; `InfraError` passes through untranslated — the
  wiring halts the session explicitly, because the framework would
  otherwise feed the model an opaque error and keep going.

## The LiveKit translation (`scheduling/livekit_wiring.py`)

Not CI-checked and not covered by these tests — it needs `livekit-agents`
installed and a real session to exercise. It leans on four behaviors read
in the LiveKit Agents source (August 2026), not yet exercised here:

- `function_tool(handler, raw_schema=...)` builds a tool from a plain dict,
  so the tool list is generated from `llm_tools()` in a loop; the handler
  receives the whole `raw_arguments` dict unbound.
- Raising `ToolError(message)` feeds the message back to the model, which
  gets another turn — that is the auto-retry. Any other exception is
  sanitized to a generic error and the loop continues, which is why the
  wiring handles `InfraError` explicitly.
- `Agent.update_tools(...)` swaps the tool list mid-session; the shim
  rebinds after every execution so schemas always reflect current state.
- The LLM plugin's `chat(chat_ctx=, tools=)` runs without a session — the
  right surface for adapter-tier evals (single decisions; no retry loop
  there).

## Run it

```sh
cd examples/spike-llmport
MYPYPATH=.:../../tesser-py mypy --strict scheduling/domain.py scheduling/tools.py \
  scheduling/application.py scheduling/llm.py tests
pytest -q
```

## Non-goals

This spike is about the port shape. It does not carry a `client/` surface,
sigcheck conformance, or evals; the eval tiers this design supports are the
subject of the test-structure ruling, not this code.
