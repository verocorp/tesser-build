# llmport — the LLM tool-call edge as a conformant bounded context

A workflow whose next step is decided by an LLM tool call, built as a real
`scheduling` context in the `ts.*` shell idiom and held to the shared example
bar. The whole tree is sigcheck-clean — zero findings, gated plainly in CI.
The two findings the tree's ratchet used to carry were resolved by the srv
vocabulary (`tesser.srv`: `Host`, `Port`, `Record`, `Rejection`, `Request`,
`Response`) and the protocol-module rules: `ToolAgent` declares itself a
`ts.Host`, and `protocol/voice.py` is a governed protocol module (see "The
host/handler split" below for the history — it lived as the "wire module"
`voicewire.py` until the 2026-08-08 vocabulary ruling). mypy --strict and pytest gate the pure modules.

## The shape

```
scheduling/
  client/
    client.py     requests/responses (primitive DTOs) + SchedulingClient
  domain/
    scheduling.py Step/CustomerName/Slot/BookingID VOs, Booking aggregate,
                  step constants
    test_domain.py       sibling test — reaches the role it sits in
  application/
    ports/
      slot_directory.py     SlotDirectory port + its Request/Response DTOs,
                             ReservationOutcome (RESERVED / SLOT_TAKEN)
      booking_repository.py BookingRepository port + its Request/Response
                             DTOs, BookingPresence (PRESENT / ABSENT)
    views.py      the MapTo* mappers the service bodies are written in, each
                  one its target spec or port DTO — MapToBookingSpec,
                  MapToBegunBookingSpec, MapToResumptionSpec, MapToNamingSpec,
                  MapToSaveBookingRequest, MapToReoffersSpec
    service.py    BookingService, depending on the two ports above
    test_views.py / test_service.py  sibling tests; the service test declares
                  its own @ts.fake port doubles
  adapters/
    handlers.py   LlmToolHandler — one endpoint method per tool, plus the schema
                  declarations the model sees
  tests/
    test_handlers.py     the context tier — reaches the whole context
conftest.py       the tree-root conftest: a leaf, imports nothing from the tree
protocol/
  voice.py        the protocol module: ToolSurface + ToolEndpoint (ts.Port),
                  ToolCall (ts.Request), ToolTurn (ts.Response), Tool and Route
                  (ts.Record), BadToolCall (ts.Rejection) — the voice analog of
                  protocol/http.py; the app owns it, handlers define it, hosts
                  conform to it
srv/
  voice/agent.py  ToolAgent (ts.Host) — the context-generic LiveKit host; it
                  takes the name -> endpoint table in and walks it inline,
                  TB051 having left no module a routing function could live in
  voice/test_agent.py  sibling test; hand-written @ts.fake surface and
                  endpoints drive the real livekit Agent with no session
```

The division of labor the checkers enforce:

- **The service speaks only Requests and Responses** — one `ts.Request` in,
  one `ts.Response` out, per use case (`begin`, `provide_name`, `choose_slot`,
  `confirm`, `status`), each body inline.
  The booking id arrives as a `BookingID` before any port sees it. The
  booking is loaded from the repository port's `BookingView`, driven through
  one guarded transition, and decomposed back to a `SaveBookingRequest`; a
  rejected transition persists nothing.
- **Ports speak records, never domain objects** — `SlotDirectory` and
  `BookingRepository` live in `application/ports/`, one port per module, and
  their DTOs carry strings and `BookingView` only. `BookingRepository` used
  to expose a check-then-get pair (`has` / `get`); it is now a single `find`
  returning a `BookingPresence` outcome plus payload, closing the
  time-of-check-to-time-of-use gap between the two calls.
- **The handler translates; the host routes.** `handlers.py` owns the tool
  names, the JSON schemas (the choose-slot schema embeds the *current* offered
  slots as an enum, rebuilt from every response), and the raw-argument
  parsing — one endpoint method per tool, exactly as an HTTP handler carries
  one method per route. The name→endpoint table is handed to the host, which
  walks it inline, because routing is the host's job in every other srv. The
  context below the handler never hears the word "tool".
- **A taken slot is an outcome, not an error.** `SlotDirectory.reserve`
  returns a `ReservationOutcome` enum (`RESERVED` / `SLOT_TAKEN`) plus payload
  rather than raising or returning a union. The service does not read that
  enum: `MapToReoffersSpec` carries it into `Reoffers`, `Booking.settle`
  answers a `Settled` outcome (`BOOKED` / `REOFFERED`), and `confirm` matches
  that one answer with `typing.assert_never` for exhaustiveness — reserved
  books, taken re-offers the slots that are free now and persists that.
  `begin` does the same with the repository's `BookingPresence`, through
  `Resumption.resumed()`. One call, one turn — the caller is told what happened and what to do
  next in the same response, and the state it is told about is the state that
  was saved. This was edge choreography until 2026-08-08 (the adapter caught
  the failure, called a `reoffer` use case, and re-raised with the fresh slots
  in the message). Chris's handler definition — map request, invoke service,
  map response — named it: three service calls and a domain-state branch is
  not mapping. Moving it also removed `reoffer` from the client surface (its
  only caller was that `except` block) and closed a real defect, since the
  `try` had grown wide enough to swallow a `ValueError` from schema-table
  drift and answer it with "that slot was taken".
- **`srv/voice/agent.py`** translates the protocol onto LiveKit Agents:
  `function_tool(raw_schema=...)` per schema, one shim, `ToolError` for
  `ValueError` (model-correctable, with a tools rebind), halt on anything
  else. Its sibling test drives the real `livekit.agents.Agent` — no session,
  no model, no mocking library: a hand-written `@ts.fake` `ToolSurface` and
  three `@ts.fake` endpoints, and the mounted tool is awaited directly. That
  is what `livekit-agents` is doing in `requirements-dev.txt`. It stays
  outside the mypy gate, which runs on `scheduling protocol conftest.py`.
- **The protocol speaks turns, not state.** A `ToolTurn` is the mechanism's own
  record: the reply to speak plus the tool schemas now in play. The handler
  translates its context DTO into it, exactly as an HTTP handler renders a
  `Response` — the context's DTOs never cross into the host.

## What conformance cost — the collisions worth knowing

Restructuring to zero findings surfaced four places where the rulebook and
the original design genuinely collided:

- **The error-kind taxonomy is not expressible.** The settled error norm
  (closed kind set, `DomainError` with kind-as-field, exhaustive
  `status_for`-style mappers) has no shell: an exception class or an enum in a
  role module is "declares no ts.* base". This tree does what the retired
  spike-shells tree did — the domain raises `ValueError` — and the edge rule
  collapses to
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
  class would need a new adapters kind, which is a ruling this tree may
  not improvise. What IS buildable: `voicewire.Tool` (`ts.Record`, the new
  generic wire-record kind) carries the declaration as data (name +
  description + parameters, `schema()` renders the raw dict the host
  mounts), `ToolTurn.tools` speaks `Tool` records instead of loose dicts,
  and the handler owns the schema declarations (name → description +
  schema-builder) the model sees.

  Chris then named the structural consequence (2026-08-08): if the tool call
  really is a handler, routing belongs where every other srv keeps it. It
  moved. `dispatch` is gone from the handler and from `ToolSurface`; the
  handler exposes one endpoint method per tool (`provide_name`,
  `choose_slot`, `confirm`, each a `voicewire.ToolEndpoint`), and
  `srv/voice/router.py` holds the `name → endpoint` table and the lookup —
  the exact shape `srv/http/host.py` uses when it names each handler method
  in a `Route`. Two things fell out of that: the table entry (`Route`) is a
  wire record, because it is a value the handler authored and the host
  mounts, and it therefore lives in the wire module rather than in `srv` —
  which is *why* this router is sigcheck-clean while python-app's HTTP
  router still carries six ratchet findings for its undeclared
  `Route`/`Match` dataclasses. A new tool is now one endpoint method, one
  declaration entry, and one route.

## The host/handler split, answered in code — and then enacted

Where does the `AgentSession`-owning LiveKit wrapper belong — the context's
adapters, or a voice host in `srv/`? This tree originally carried both
options so the structure could answer. The wrapper turned out to be **fully
context-generic**: once `instructions()` moved onto the handler (it was
content, misplaced in the transport), `ToolAgent` imports nothing from any
context — it speaks to the `ToolSurface` port. One voice host
mounts any context's LLM handler, exactly as the HTTP host mounts HTTP
handlers: the host owns the transport, the handler owns the content.

The srv vocabulary and the protocol-module rules then enacted the verdict:
`ToolAgent` declares itself a `ts.Host` in `srv/voice/agent.py`, the
option-A adapter shim (`scheduling/adapters/livekit.py`) was deleted, and
the module (then `voicewire.py`, now `protocol/voice.py`) became governed.
The protocol is the contract the app owns and both sides abide by — the
handlers define it, the hosts conform to it (the voice analog of
`protocol/http.py`) — and sigcheck enforces exactly that ownership: a
protocol module imports no context and never imports srv or bootstrap,
which keeps contexts constructible with no host in the process.

The migration also deleted the protocol's structural-state machinery. The old
contract passed the context's own response through the host behind a
`ToolState` protocol and a state-generic `ToolHandler[S]` — the shape that
produced the contravariance defect four pre-landing reviewers found
independently. The host only ever read `reply` and handed the state back to
`tools()`, so the protocol now owns a concrete `ToolTurn` record (reply + the
tool schemas now in play) and the handler translates into it, symmetric
with HTTP. No TypeVar, no generic protocol, no conformance edge case — the
typed assertion in the handler tests is a plain assignment.

## Run it

```sh
(cd tessercheck-py && PYTHONPATH=.:../tesser-py python3 -m srv.cli.main ../examples/llmport)
cd examples/llmport
MYPYPATH=.:../../tesser-py mypy --strict scheduling protocol conftest.py
pytest -q
```

The sigcheck run prints nothing and exits 0 — the tree is finding-free and
CI gates it at zero.

## Documented production boundaries

This is teaching code; five simplifications are deliberate, named here so
they are copied knowingly or not at all:

- **The protocol contract is synchronous.** `ToolSurface` and every
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
HTTP/CLI protocol records) briefly lost the frozen-dataclass guarantee in
the shell migration. The srv matrix ruled it per-kind (2026-08-07):
`ts.Record` now owns one-shot construction, attribute immutability, and
value equality for every wire record, so `ToolTurn` and `Tool` carry the
guarantee without a per-class patch. The freeze is SHALLOW by design —
it stops rebinding, not mutation of a field's referent — so a record
holding a container copies it in its constructor: the HTTP protocol records copy
their header and param maps, and `Tool` deep-copies its schema in and
out of `schema()` because the host hands that dict to a provider SDK.

## Non-goals

No wiring module (no concrete gateways exist to select), no bootstrap or composition root (`srv/voice/agent.py`
is the one host and nothing in-tree constructs it), no evals. The eval tiers
this design supports are the subject of the test-structure ruling, not this
code.
