# spike-llmport — the LLM tool-call edge as a conformant bounded context

A workflow whose next step is decided by an LLM tool call, built as a real
`scheduling` context in the `ts.*` shell idiom and held to the spike-shells
bar. The `scheduling` context is sigcheck-clean; the tree carries exactly
three accepted findings, all in `srv/voice/agent.py` — deliberate evidence
for the host-vocabulary ruling (see "The host/handler split" below),
ratcheted in CI so nothing new can hide behind them. mypy --strict and
pytest gate the pure modules.

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
srv/
  voice/agent.py  option B of the host/handler split: a context-generic ToolAgent
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

## The host/handler split, answered in code

Where does the `AgentSession`-owning LiveKit wrapper belong — the context's
adapters, or a voice host in `srv/`? Both options live in this tree so the
structure can answer:

- **Option A — `scheduling/adapters/livekit.py`** (`SchedulingAgent`).
  Conforms to the current rulebook. But it is transport glue wearing an
  adapter's name: every context serving voice would re-implement the same
  shim/rebind/error mechanics, the way no context re-implements the HTTP
  server.
- **Option B — `srv/voice/agent.py`** (`ToolAgent`). The wrapper turns out
  to be **fully context-generic**: once `instructions()` moved onto the
  handler (it was content, misplaced in the transport), `ToolAgent` imports
  nothing from any context — it speaks to a structural `ToolHandler`
  protocol (instructions/begin/status/tools/dispatch). One voice host can
  mount any context's LLM handler, exactly as the HTTP host mounts HTTP
  handlers. This matches the settled anatomy: the host owns the transport,
  the handler owns the content.

The verdict the code gives: **B is the doctrinal answer** — the
handler/host split that already existed inside the LiveKit wiring
(`LlmToolHandler` = content, agent class = transport) is the anatomy's own
split, and genericity proves the agent class was never context code. What
blocks enacting it is one known gap: srv modules currently admit no
classes ("a srv or bootstrap module holds only imports, declared functions,
and Final constants" — the host-vocabulary question the import-totality
wave deliberately surfaced). The three findings in `sigcheck-ratchet` are
that gap, made exact. When a host vocabulary is ruled (a declarable srv
class kind), option A gets deleted, the baseline burns down to zero, and
the plain zero-findings CI step comes back.

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
