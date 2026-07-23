# Gateway: cross-context

<!-- tb-status: partial -->

An **outbound adapter** from one context to a peer context you own: it satisfies
a port the calling context defines, by calling the peer's public `Client`
(`public-interface.md`). One of the gateway types in the anatomy
(`map.md#adapters`) — its siblings are the repository (`repositories.md`, a
gateway to persistence) and the vendor/ACL gateway (no file yet — no verified
impl exists anywhere; note the gap, don't invent a convention).

> **Status: stub.** The rules below are the settled, machine-verified core
> (dependency direction and fail-closed behavior are locked by tests in the
> verified impl). The fuller treatment — translation depth, error mapping,
> async/event-shaped crossings — is **not yet materialized**: note the gap,
> don't invent a convention; the verified impl is
> `examples/python-app/campaign/adapters/gateways/target_checker.py`.

## Is this what I'm building?

**Test:** *Am I making one context call another context's public `Client`,
behind an interface the calling context owns?* Yes → cross-context gateway.

**Near-misses:**
- A **repository** (`repositories.md`) — a gateway to *persistence*, not a peer.
- A **vendor/ACL gateway** — defends against a model you *don't* own (a
  third-party SDK or schema). Same port+adapter shape, different purpose; no
  verified impl or file yet.
- A **cross-context read that belongs to neither peer** — that is not a gateway
  problem but a *context* question: it gets its own small context above both
  peers (`map.md#how-contexts-connect`).

## Rules

1. **The consumer owns the port.** The calling context declares the interface it
   needs (campaign's `TargetChecker`), in its own vocabulary, on its own side of
   the boundary. The peer never learns the caller exists.
2. **The adapter lives in the caller's `adapters/gateways`.** It wraps the
   peer's `Client` and translates the peer's DTOs into the caller's own types —
   the peer's vocabulary never crosses inward. The composition root constructs
   the adapter (it is the one place allowed to know both contexts) and injects
   it (`bootstrap.md`).
3. **Dependencies run one way.** campaign → linkpolicy means linkpolicy never
   imports campaign — locked by a direction test in the verified impl
   (`examples/python-app/tests/test_direction.py`). A would-be cycle is a
   boundary error, not a wiring problem (`strategic-design.md#bounded-contexts`).
4. **Synchronous calls are fail-closed.** A policy rejection *or* a peer outage
   fails the use case honestly — the gateway propagates the peer's infra error,
   it never swallows it into a default (locked by
   `examples/python-app/tests/test_call_fail_closed.py`).

## Now build it

Not yet materialized beyond the rules above (see status note). The verified impl
to imitate: `examples/python-app/campaign/adapters/gateways/target_checker.py`
(port + `CheckOutcome` declared beside campaign's `Client`; adapter over
`linkpolicy.Client`; wired in `examples/python-app/bootstrap/bootstrap.py`).
