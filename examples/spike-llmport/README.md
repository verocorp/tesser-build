# spike-llmport — the LLM tool-call edge as a conformant bounded context

A workflow whose next step is decided by an LLM tool call, built as a real
`scheduling` context in the `ts.*` shell idiom and held to the spike-shells
bar: **sigcheck reports zero findings over this tree**, mypy --strict and
pytest gate the pure modules in CI.

## The shape

```
scheduling/
  client.py       requests/responses (primitive DTOs) + SchedulingClient
  domain.py       Step/CustomerName/Slot VOs, Booking aggregate, step constants
  application.py  BookingParts, SlotDirectory + BookingRepository ports, BookingService
  adapters/
    handlers.py   LlmToolHandler — the LLM wire: tool vocabulary, schemas, dispatch
    livekit.py    SchedulingAgent — the LiveKit translation over the handler
tests/            domain/application/handler tests; each declares its own @ts.fake port doubles
```

The division of labor the checkers enforce:

- **The service speaks only Requests and Responses** — one `ts.Request` in,
  one `ts.Response` out, per use case (`begin`, `provide_name`, `choose_slot`,
  `confirm`, `reoffer`, `status`), each body inline and under ten lines. The
  booking is loaded from parts, driven through one guarded transition, and
  decomposed back to parts; a rejected transition persists nothing.
- **Ports speak records, never domain objects** — `SlotDirectory` and
  `BookingRepository` carry strings and `BookingParts` only.
- **The LLM wire lives entirely in the adapter.** `handlers.py` owns the tool
  names, the JSON schemas (the choose-slot schema embeds the *current* offered
  slots as an enum, rebuilt from every response), the raw-argument parsing,
  and the tool→use-case dispatch. The context below it never hears the word
  "tool".
- **The conflict choreography is edge behavior.** A confirm that fails
  because the slot was taken makes the adapter call the `reoffer` use case and
  re-raise with the fresh slots in the message — the model sees what is now
  bookable; the service stays four-step.
- **`adapters/livekit.py`** translates the handler onto LiveKit Agents:
  `function_tool(raw_schema=...)` per schema, one shim, `ToolError` for
  `ValueError` (model-correctable, with a tools rebind), halt on anything
  else. It is in sigcheck's walk (pure AST) but outside the mypy/pytest gate —
  it needs `livekit-agents` installed and a real session to exercise.

## What conformance cost — the collisions worth knowing

Restructuring to zero findings surfaced three places where the rulebook and
the original design genuinely collided:

- **The error-kind taxonomy is not expressible.** The settled error norm
  (closed kind set, `DomainError` with kind-as-field, exhaustive
  `status_for`-style mappers) has no shell: an exception class or an enum in a
  role module is "declares no ts.* base". This tree does what spike-shells
  does — the domain raises `ValueError` — and the edge rule collapses to
  "`ValueError` is model-correctable, anything else halts". The
  validation/not-found/conflict distinction is gone from the types; an errors
  block for the rulebook is the open gap.
- **`assert_never` totality became test totality.** Closed sets are `Final`
  string constants, so the exhaustive-match proofs over steps and tool names
  moved from mypy to tests (`test_the_tool_map_covers_exactly_the_domain_steps`
  iterates both sets).
- **Step literals exist twice.** The domain owns its step constants; the
  adapter keys `TOOLS_FOR_STEP` on the strings that cross in DTOs, and the
  import matrix forbids it from importing the domain's constants. The same
  totality test is the drift tripwire.

## Run it

```sh
PYTHONPATH=examples/spike-shells:tesser-py python3 -m sigcheck examples/spike-llmport
cd examples/spike-llmport
MYPYPATH=.:../../tesser-py mypy --strict scheduling/domain.py scheduling/client.py \
  scheduling/application.py scheduling/adapters/handlers.py tests
pytest -q
```

## Non-goals

No wiring module (no concrete gateways exist to select — the precedent is
spike-shells' contexts), no srv/bootstrap, no evals. The eval tiers this
design supports are the subject of the test-structure ruling, not this code.
