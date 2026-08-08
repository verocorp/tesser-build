# spike-llmport — the LLM tool-call edge as a conformant bounded context

A workflow whose next step is decided by an LLM tool call, built as a real
`scheduling` context in the `ts.*` shell idiom and held to the spike-shells
bar. The whole tree is sigcheck-clean — zero findings, gated plainly in CI.
The two findings the tree's ratchet used to carry were resolved by the srv
vocabulary (`tesser.srv`: `Host`, `Port`, `Record`, `Request`, `Response`) and the
wire-module rules: `ToolAgent` declares itself a `ts.Host`, and
`voicewire.py` is a governed wire module (see "The host/handler split"
below for the history). mypy --strict and pytest gate the pure modules.

## The shape

```
scheduling/
  client.py       requests/responses (primitive DTOs) + SchedulingClient
  domain.py       Step/CustomerName/Slot VOs, Booking aggregate, step constants
  application.py  BookingParts, SlotDirectory + BookingRepository ports, BookingService
  adapters/
    handlers.py   LlmToolHandler — the LLM wire: tool vocabulary, schemas, dispatch
tests/            domain/application/handler tests; each declares its own @ts.fake port doubles
voicewire.py      wire module: ToolSurface (ts.Port), ToolTurn (ts.Response), and
                  Tool (ts.Record) — the voice analog of httpwire, imported by host
                  and handler, owned by neither
srv/
  voice/agent.py  ToolAgent (ts.Host) — the context-generic LiveKit host
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
- **`srv/voice/agent.py`** translates the wire onto LiveKit Agents:
  `function_tool(raw_schema=...)` per schema, one shim, `ToolError` for
  `ValueError` (model-correctable, with a tools rebind), halt on anything
  else. It is in sigcheck's walk (pure AST) but outside the mypy/pytest gate —
  it needs `livekit-agents` installed and a real session to exercise.
- **The wire speaks turns, not state.** A `ToolTurn` is the mechanism's own
  record: the reply to speak plus the tool schemas now in play. The handler
  translates its context DTO into it, exactly as an HTTP handler renders a
  `Response` — the context's DTOs never cross into the host.

## What conformance cost — the collisions worth knowing

Restructuring to zero findings surfaced four places where the rulebook and
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
- **The tool declaration got its word — on the wire side.** `LlmToolHandler`
  used to maintain three parallel structures keyed on the same tool-name
  strings (`TOOLS_FOR_STEP`, the `dispatch` chain, the `_schema` chain) plus
  inline per-tool parsing — the dispatch smell Chris named during the
  srv-wire ship. Resolved 2026-08-07 by building both candidate shapes and
  letting sigcheck rule. The declared-tool-CLASS shape (name + schema +
  parse + invoke as one context-side class) is unbuildable inside the srv
  vocabulary — probed verbatim: an undeclared class in the adapter draws
  "declares no ts.* base; every context class declares its block", and
  declaring it with the wire vocabulary draws "is a wire record; a host
  lives in srv and a wire kind in a wire module, never a context" — a tool
  class would need a new adapters kind, which is a ruling this spike may
  not improvise. What IS buildable: `voicewire.Tool` (`ts.Record`, the new
  generic wire-record kind) carries the declaration as data (name +
  description + parameters, `schema()` renders the raw dict the host
  mounts), `ToolTurn.tools` speaks `Tool` records instead of loose dicts,
  and the handler owns ONE binding table (name → description +
  schema-builder + invoke) from which both `dispatch` and the offered
  schemas derive. Unknown-name drift is structurally gone; a new tool is
  one table entry plus its `TOOLS_FOR_STEP` row.

## The host/handler split, answered in code — and then enacted

Where does the `AgentSession`-owning LiveKit wrapper belong — the context's
adapters, or a voice host in `srv/`? This tree originally carried both
options so the structure could answer. The wrapper turned out to be **fully
context-generic**: once `instructions()` moved onto the handler (it was
content, misplaced in the transport), `ToolAgent` imports nothing from any
context — it speaks to the `voicewire.ToolSurface` port. One voice host
mounts any context's LLM handler, exactly as the HTTP host mounts HTTP
handlers: the host owns the transport, the handler owns the content.

The srv vocabulary and the wire-module rules then enacted the verdict:
`ToolAgent` declares itself a `ts.Host` in `srv/voice/agent.py`, the
option-A adapter shim (`scheduling/adapters/livekit.py`) was deleted, and
`voicewire.py` became a governed wire module. Per handlers.md, the wire
vocabulary is the contract both sides import and neither owns (the voice
analog of `httpwire.py`) — sigcheck now enforces exactly that ownership:
a wire module imports no context and never imports srv or bootstrap, which
keeps contexts constructible with no host in the process.

The migration also deleted the wire's structural-state machinery. The old
contract passed the context's own response through the host behind a
`ToolState` protocol and a state-generic `ToolHandler[S]` — the shape that
produced the contravariance defect four pre-landing reviewers found
independently. The host only ever read `reply` and handed the state back to
`tools()`, so the wire now owns a concrete `ToolTurn` record (reply + the
tool schemas now in play) and the handler translates into it, symmetric
with HTTP. No TypeVar, no generic protocol, no conformance edge case — the
typed assertion in the handler tests is a plain assignment.

## Run it

```sh
PYTHONPATH=examples/spike-shells:tesser-py python3 -m sigcheck examples/spike-llmport
cd examples/spike-llmport
MYPYPATH=.:../../tesser-py mypy --strict scheduling voicewire.py tests
pytest -q
```

The sigcheck run prints nothing and exits 0 — the tree is finding-free and
CI gates it at zero.

## Documented production boundaries

This is teaching code; five simplifications are deliberate, named here so
they are copied knowingly or not at all:

- **The wire contract is synchronous.** `voicewire.ToolSurface` and every
  port below it are sync; the host calls `dispatch` inside the event loop.
  A real implementation with real IO must either make the contract async or
  have the host absorb the hop (`await asyncio.to_thread(...)` at the three
  handler call sites). The per-session `asyncio.Lock` in the agent
  serializes tool calls; it does not unblock the loop.
- **Ports must not raise `ValueError` for infrastructure faults.** The
  edge's whole classification is "`ValueError` is model-correctable,
  anything else halts" (the collapsed error-kind taxonomy). A repository or
  directory that raises `ValueError` on a driver fault would be misrouted
  to the model as correctable. The error-shell ruling (`ts.Error`) replaces
  this contract-by-convention with types.
- **`confirm` reserves before it saves.** A `save` failure after a
  successful `reserve` leaves the reservation held with the booking at
  `confirm` — an operator-recoverable window, not silent loss, but real.
  The outbox/idempotency-key answer is out of scope here.
- **`save` carries no concurrency token.** Concurrent tool calls could
  interleave read-modify-write. The agent serializes per session with a
  lock; cross-session writers need an expected-version parameter on the
  port.
- **A slot's label is its identity.** Two distinct resources with equal
  labels would collide; a production directory needs an opaque slot id
  beside the display label. Likewise `booked` is terminal (no cancel, no
  name correction) and an exhausted directory surfaces as a combined
  "taken; no slots are available" error rather than a terminal state —
  state-machine growth left for a consumer with real requirements.

The sigcheck-vs-ruff F401 collision this tree used to document (a mandated
`ts` import that nothing used) resolved itself with the srv vocabulary:
`srv/voice/agent.py`'s `import tesser.srv as ts` is now load-bearing —
`ToolAgent` subclasses `ts.Host`.

One more named boundary, since closed: `ToolTurn` (like the migrated
httpwire/cliwire records) briefly lost the frozen-dataclass guarantee in
the shell migration. The srv matrix ruled it per-kind (2026-08-07):
`ts.Record` now owns one-shot construction, attribute immutability, and
value equality for every wire record, so `ToolTurn` and `Tool` carry the
guarantee without a per-class patch. The freeze is SHALLOW by design —
it stops rebinding, not mutation of a field's referent — so a record
holding a container copies it at the door: the httpwire records copy
their header and param maps, and `Tool` deep-copies its schema in and
out of `schema()` because the host hands that dict to a provider SDK.

## Non-goals

No wiring module (no concrete gateways exist to select — the precedent is
spike-shells' contexts), no bootstrap or composition root (`srv/voice/agent.py`
is the one host and nothing in-tree constructs it), no evals. The eval tiers
this design supports are the subject of the test-structure ruling, not this
code.
