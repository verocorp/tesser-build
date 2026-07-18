# Handler

<!-- tb-status: partial -->

An **inbound adapter**: it translates one delivery mechanism's wire format
(HTTP, CLI, an event) to and from one context's public `Client`, and nothing
else. Handlers are one of the two adapter types in the anatomy — inbound
receives, outbound reaches out (`map.md#adapters`); the app-level host that
mounts handlers and runs the server is a separate layer (`srv.md`).

> **Status: partially materialized.** The one handler rule below is settled,
> verified doctrine. The fuller treatment — wire-format translation patterns,
> error → status mapping, per-mechanism shapes — is **not yet materialized**:
> note the gap, don't invent a convention; the verified impl is
> `examples/python-app/campaign/adapters/handlers/`.

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
2. **The `Client` is injected.** The handler is constructed with the `Client`
   (`bootstrap.md` wires it, via the host); it never builds or fetches one.
3. **Cross-cutting concerns belong to the host, not the handler.** Auth
   *policy*, logging, recovery, rate limits are middleware at the host layer
   (`srv.md`); a handler that imports another context to do auth has leaked a
   host concern into a context adapter.

## Now build it

Not yet materialized (see status note above). The verified impl to imitate:
`examples/python-app/campaign/adapters/handlers/http.py` — a `Handler`
constructed with `campaign.Client`, translating request paths/bodies to DTO
requests and mapping domain error kinds to statuses at the edge.
