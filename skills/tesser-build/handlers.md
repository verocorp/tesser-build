# Handler

<!-- tb-status: full -->

An **inbound adapter**: it translates one delivery mechanism's wire format
(HTTP, CLI, an event) to and from one context's public `Client`, and nothing
else. Handlers are one of the two adapter types in the anatomy — inbound
receives, outbound reaches out (`map.md#adapters`); the app-level host that
mounts handlers and runs the server is a separate layer (`srv.md`).

## Is this what I'm building?

**Test:** *Am I receiving a request from outside (HTTP/CLI/event), translating
it for exactly one context's `Client`, and translating the answer back?*
Yes → handler.

**Near-misses that are NOT a handler:**
- The **host** (`srv.md`) — mounts *all* contexts' handlers for one delivery
  mechanism, applies cross-cutting middleware, owns the server and process
  lifecycle. A handler is per-context; a host is app-wide.
- A **gateway** — the outbound direction: it *initiates* a call to persistence
  or a peer (`repositories.md`, `gateway-cross-context.md`). Inbound needs a
  server (something calls *in*); outbound doesn't.
- An **application service** (`application-services.md`) — the use-case
  coordinator the handler calls *through the `Client`*; it never parses wire
  formats.

## Rules

1. **The one handler rule.** A handler parses and authenticates the request,
   then calls the application service **through the component's public `Client`
   interface** (`public-interface.md`) — depending on that contract, never a
   concrete service or repository it constructed itself. It does **no domain
   math and touches no repository** — a `for`-loop over domain objects or a DB
   call in a handler belongs in the application service or the domain
   (`application-services.md#domain-logic-leakage-checks`).
2. **A handler is a total transform: request DTO in, response DTO out.** Every
   endpoint method has the same signature — `(HttpRequest) -> Response` — and
   the handler touches nothing else: no socket, no framework request object, no
   `self.path` parsing, no status line. It cannot reach transport state, so
   every case it must answer is in its argument, and it is unit-testable by
   constructing one value. **The corollary is the split with the host**: the
   host owns the *transport* — raw bytes on the socket, framing (Content-Length,
   the size cap, refusing a streaming body), routing (which endpoint, which path
   parameters), and writing back the status + headers the handler produced. The
   handler owns the *content* — `req.body` arrives as **raw `bytes`** and the
   handler decodes it (`decode_body` for JSON, or reads it as an image), calls
   the `Client`, and serializes the answer, choosing the representation and its
   `Content-Type` (`json_response`, `redirect`, …). The host never parses or
   serializes a body and never names a field; the handler never parses a URL.
   That is why a `.png` upload or a redirect is expressible without touching the
   host: the body is opaque bytes to it, and the content type is the handler's
   call.
3. **The `Client` is injected.** The handler is constructed with the `Client`
   (`bootstrap.md` wires it, via the host); it never builds or fetches one.
4. **Cross-cutting concerns belong to the host, not the handler.** Auth
   *policy*, logging, recovery, rate limits are middleware at the host layer
   (`srv.md`); a handler that imports another context to do auth has leaked a
   host concern into a context adapter.
5. **The wire shape is not the contract.** The JSON/flag/event shape is
   translated to and from `Client` DTOs *inside the handler*, field by field —
   never deserialized straight into a DTO or domain type. That translation is
   the point of the layer: a wire rename touches the handler; the `Client`
   and everything below it never hear about it.
6. **A context a host exposes owns a handler.** `adapters` is optional only
   while a context has no edge; the moment a host serves it, the wire
   translation is that context's handler, not the host's inline code. A
   context that composes peers through their `Client`s (a cross-context read
   model) still gets a handler the moment it is routed — reaching peers
   through injected `Client`s is an *outbound* property and says nothing about
   the inbound edge.
7. **Errors map to the wire at the edge, exhaustively — and the host uses the
   same table.** One `respond` path catches: shape failures (malformed JSON,
   wrong-typed field) → 400; domain errors → status via the one pure kind→status
   mapper (the closed `Kind` set, `errors.status_for`); infra errors → 503;
   anything unexpected → 500 with no internals leaked. The host's *transport*
   rejections go through the **same** `respond`/`problem` vocabulary — an
   oversized body → 413, a streaming body it can't buffer → 411, an unmatched
   route → 404 — so a client sees one error format from the whole process, not
   the framework's default HTML for the host's failures and problem-JSON for the
   handler's. No per-endpoint ad-hoc mapping — two endpoints must not disagree on
   what `not_found` means.

## Shape

```
<context>/adapters/handlers/
  http.py          ← Handler(client), one method per endpoint, one respond path

class Handler:
    def __init__(self, client: Client) -> None: ...     # injected, held as the contract
    def add_link(self, req: HttpRequest) -> Response:   # request DTO → Client → response DTO
        body = decode_body(req.body)                     # raw bytes → JSON; the handler's call
        view = self._client.add_link(AddLinkRequest(
            campaign_id=string_field(body.get("campaign_id")),   # shape guard → 400
            slug=string_field(body.get("slug")),
            target_url=string_field(body.get("target_url"))))
        return json_response(200, _campaign_body(view))  # DTO → wire; sets Content-Type
```

One `Client` call per endpoint; the same `(HttpRequest) -> Response` signature
on every one, so the host can hold them as one `Endpoint` type and route by
table. The request DTO carries `method`, `path`, `path_params`, `query_params`,
`headers`, and the **raw `bytes` body**; the response DTO carries `status_code`,
the **raw `bytes` body**, and `headers`. **The names deliberately mirror
FastAPI/Starlette** (`path_params`, `query_params`, `status_code`), stripped to
what a hand-written host needs, so the shape is recognizable and a later move
onto a framework is mechanical. The body is bytes on both sides precisely so the
edge is content-type-agnostic — the handler decodes/encodes and owns the type.
**Keep these DTOs faithful to HTTP's own request/response shape** — method /
path / params / headers + an opaque byte body in, status + headers + an opaque
byte body out. That fidelity is what lets a reader *derive* the cases this
example doesn't ship (streaming via a `stream()` body, auth via a header,
content negotiation via `Accept`) instead of being boxed in; collapsing the body
back to a decoded `dict` for convenience is the regression that forecloses them.
The shape is locked against that drift by
`examples/python-app/tests/test_httpwire.py` (the request/response fidelity
tests). Construction mechanics: `python.md#inbound-handlers-and-hosts`; verified impl:
`examples/python-app/campaign/adapters/handlers/http.py` (full case) and
`examples/python-app/reports/adapters/handlers/http.py` (minimal case: one
read endpoint over a cross-context read model).

## Decisions you must make

1. **One handler per mechanism, per context.** The HTTP handler and an event
   consumer's handler are siblings under `adapters/handlers/` — same `Client`,
   different wire. Don't fuse mechanisms into one class; their failure
   vocabularies differ.
2. **Does a CLI need a handler class?** A genuinely *single-command* CLI can
   translate inline in the host's dispatch — the handler *role* is still played
   (translate, call, render), just not extracted. But the split is
   mechanism-independent, and **multiple commands earn it**: the verified impl's
   CLI is the same shape as its HTTP one — a per-command transform
   `(CliRequest) -> CliResponse` in `campaign/adapters/handlers/cli.py`, a
   `srv/cli` host that routes a command name to it, prints, and exits. The
   `CliRequest` (positional `args`, and stdin/options if ever needed) and
   `CliResponse` (`exit_code`, `stdout`, `stderr`) are the CLI's request/response
   DTOs; `cliwire.py` is their shared vocabulary, the analog of `httpwire.py`.
   The one CLI-specific piece is the error mapper: the same closed domain `Kind`
   set maps to an **exit code** (`errors.exit_code_for`) exactly as HTTP maps it
   to a status (`status_for`) — one taxonomy, two total edge mappers. It obeys
   the same rules: no domain math, no repository, no transport in the signature.
3. **What is the problem-shape on the wire?** The verified impl renders
   errors as a problem object (`type` + `detail`, RFC 9457-shaped) with the
   domain error's open `Code` as the type — decided once at the `respond`
   path for the whole mechanism.
4. **Where does the shared wire vocabulary live?** The request/response DTOs,
   the problem renderer, and the `respond` error table describe the
   *mechanism*, not any one context — so once a second context serves the same
   mechanism they belong in one app-level module (verified impl:
   `examples/python-app/httpwire.py`). Leaving them in the first context's
   handler forces its peers to import a sibling's adapter internals, which is
   a public-interface violation dressed up as reuse. That module is the
   **contract between the host and every handler**, so both sides import it and
   neither owns it — which is also what keeps the dependency straight: a
   handler must never import from `srv/`, because a context has to be
   constructible and testable with no host in the process.
5. **Does the route table belong to the host or the context?** The host. A
   context knowing its own URLs means the app can't mount it twice, can't
   version it, and can't move it behind a prefix without editing the context.
   The host declares `(method, pattern, endpoint)` and passes the extracted
   parameters in the request DTO; the handler never sees a URL
   (verified impl: `examples/python-app/srv/http/host.py:routes_for`).
6. **Buffered body, or streamed?** The verified impl **buffers**: the host reads
   a declared, finite, under-cap body into `bytes`, and refuses the rest — an
   oversized body is a 413, a `Transfer-Encoding: chunked` body is a 411, both
   decided from the framing headers before a handler runs. That covers JSON, a
   form post, and a single bounded file. It does **not** cover a large upload or
   a live audio feed: a streamed body isn't a value, so it can't ride in a
   frozen request DTO — it needs a different shape (the request exposing a
   pull-source, `stream()`, and the host de-chunking the wire), which is a
   **documented boundary here, not built** — the same discipline as the deferred
   worker host and SQL backend. The 411 is the honest in-code marker of that
   line: the host says "I buffer; declare a length" rather than silently
   mis-reading a stream. Reach for a framework (`srv.md`) when you actually need
   streaming, multipart, or content negotiation — that is the point where the
   hand-rolled host has earned its replacement.

## How the machine sees it

No shipped analyzer targets handlers in this cut. What is machine-checked is
the host↔handler boundary, in the verified impl only. Two halves:
`examples/python-app/tests/test_enforcement.py` (AST) checks that every context
a host reaches owns a handler role, and that the HTTP host never *calls* a
context `Client` — proven on injected violations, including the aliased form
`reports = app.reports` that a naive attribute check would miss. That one is
reach-but-never-call, not an import rule, so no linter covers it. The import
half is a `forbidden` contract in `examples/python-app/.importlinter`: the host
imports nothing from a context except its `adapters.handlers`, so a `client`,
`application`, or `domain` import in the host is the router reaching past the
transform. Everything else is review plus the domain-logic leakage signal list
(`application-services.md#domain-logic-leakage-checks`). Review-side tells:
- an import of a **repository or concrete service** in a handler module;
- **domain arithmetic or a domain `for`-loop** between parse and `Client`
  call;
- a **DTO or domain type deserialized directly from the wire**
  (`Model.parse_raw`, `json → dataclass(**body)`) — the translation layer
  skipped;
- **status codes chosen per-endpoint** instead of through the one mapper.

## Tests you must write

- **Wire → DTO translation:** a well-formed request produces exactly the
  `Client` call's DTO (assert on a recording fake `Client`).
- **The error table, one row per class:** malformed wire → 400; each domain
  `Kind` → its mapped status through the shared mapper; infra → 503;
  unexpected → 500 with a generic body. The mapper itself is tested once,
  exhaustively, at the errors layer — the handler test locks that the respond path
  *uses* it.
- **No leak on the unexpected path:** the 500 body carries no exception
  text/stack.
- **The handler is testable with no transport:** every endpoint test builds a
  request DTO by hand and asserts on the returned response DTO — no server, no
  socket, no client library. If a handler test needs one, the handler is
  reaching past its argument.

## Common mistakes

- **The fat handler.** Validation-beyond-parsing, pricing math, a repository
  call — domain logic living at the edge, invisible to the domain's tests.
  Move it through the `Client`.
- **Wire-as-contract.** Handing the parsed JSON dict (or the deserialized
  request struct) down into the service — now the wire format *is* the API
  and every wire change ripples inward.
- **Ad-hoc statuses.** `except DomainError: return 400` — collapsing the
  kind set at one endpoint; conflict and not-found become indistinguishable
  on the wire. Always the shared mapper.
- **Handler builds its dependencies.** Constructing the service or fetching
  the `Client` from a registry — construction belongs to wiring/bootstrap;
  the handler receives.
- **The transport leaking into the signature.** A handler method taking the
  framework's request object, or a loose `campaign_id: str` and `raw: bytes`
  passed alongside the request instead of *through* it. The whole request rides
  in one `HttpRequest`; splitting a piece out (the body, a path param) makes the
  endpoint set non-uniform, so the host can no longer route by table — it grows
  a branch per endpoint instead.
- **The host parsing the body.** `json.loads` in the host, or handing the
  handler a decoded `dict` instead of raw `bytes`. Now the host is committed to
  one content type — a `.png` or a plain-text body breaks it — and the decode
  lives outside the layer whose job is translation. The host reads bytes; the
  handler decodes.
- **The host translates.** One context gets a proper handler and the next one
  is answered by a few lines of body-building in the host, usually because it
  looked too small to deserve a class. The rule it broke is rule 6, and the
  cost is that the wire shape of that context now lives outside it: its DTO
  rename is a host edit, and the two endpoints drift on error mapping because
  only one of them goes through `respond`.

## Now build it

<!-- tb-allow-missing: examples/app -->

- Python: `python.md#inbound-handlers-and-hosts` — the `Handler` class, the
  transport guard, and the one `respond` path, backed by
  `examples/python-app/campaign/adapters/handlers/http.py` and
  `examples/python-app/reports/adapters/handlers/http.py`.
- Go: not yet materialized — the settled anatomy's Go mirror
  (`examples/app`) is pending; note the gap, don't invent a convention. The
  same role split (handler translates, host mounts) applies; the v3
  transport shape in `examples/ddd` predates the settled anatomy.
