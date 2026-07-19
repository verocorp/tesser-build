# Acceptance-gate record — skills/ddd v3, the wiring layer (2026-07-12)

The v3 increment adds two concepts to the skill: the **public interface** (a
`Client` + DTOs, a decoupling boundary satisfied by embedding the application
service) and the **composition root** (the single place that chooses the concrete
implementations, composes them behind the `Client`, and constructs + injects the
handler). This is the gate that proves the skill *alone* teaches an agent to
produce that structure — the same bar v1 and v2 had to clear.

## Setup — Go gate, Claude Code host (fresh Sonnet agent) — PASS

A fresh Sonnet agent with **no knowledge of the design** was given only the skill
entry point (`skills/ddd/SKILL.md`, which routes onward under progressive
disclosure) and a neutral **link-campaign** task: a marketing team runs campaigns
that own short links, with a slug format rule, a URL-scheme rule, a unique-slug
invariant, an at-most-25-links invariant, and a deactivation lifecycle; four use
cases (create, add link, deactivate, fetch); and the instruction to expose "a
public way for other code to call the service without knowing how it is built,"
to add an HTTP handler, and to "wire everything together" into a runnable `main`.

The temptations were **embedded but never named** — the prompt never said
`Client`, public interface, composition root, DTO, or embed. The agent had to
reach those from the skill. It was told not to consult `examples/` and not to
edit outside `examples/running/`.

Output: `examples/running/` — 24 files, 6 packages, 1706 lines. Package layout:

```
examples/running/
  main.go                 package main — the composition root (wire()) + end-to-end wiring test
  campaign/               the domain: Slug, TargetURL, CampaignName, CampaignID (VOs),
                          ShortLink (entity, active→deactivated lifecycle),
                          Campaign (aggregate root; unique-slug + at-most-25 invariants)
  campaignapp/            the seam: CampaignRepository interface + CampaignService (4-step use cases)
  linkcampaign/           the public contract: Client interface + DTOs only, zero internal imports
  linkcampaignimpl/       the impl: in-memory repo + `client` struct embedding *CampaignService
  transport/              HTTP handlers, depend on linkcampaign.Client only
```

## Objective criteria (verified independently — I read the code, not the report)

The design's five concrete gate assertions, each checked against the source:

1. **Public `Client` + DTOs in a package separate from the impl.** ✅
   `linkcampaign/client.go` declares the `Client` interface and every DTO;
   `linkcampaignimpl` is a different package. The public package imports **no**
   internal package (verified by grep — only `context`).
2. **The composition root returns / injects the `Client`, never a concrete.** ✅
   `linkcampaignimpl.NewClient(svc) linkcampaign.Client` returns the interface;
   `main.wire()` passes it into `transport.NewHandler`.
3. **`Client` methods return DTOs, never domain objects.** ✅ All four methods
   take/return `*Request`/`*Response` DTOs with primitive leaves; a compile-time
   `var _ linkcampaign.Client = (*client)(nil)` locks the contract.
4. **The handler depends on `Client` only.** ✅ `transport.Handler` holds a
   `linkcampaign.Client` field and imports only the public package — never
   `linkcampaignimpl`, `campaignapp`, or `campaign` (grep-verified).
5. **The composition root is the single production site choosing the concrete.** ✅
   In non-test code, `linkcampaignimpl` is imported by **`main.go` only**. (The
   `_test.go` files that import it are tests wiring their own graphs — which is
   criterion 3 of the example-test set, below, not a violation.)

Required example tests, all present and passing:

- **End-to-end wiring:** `TestWiring_EndToEnd` boots `wire()` under `httptest`,
  POSTs a campaign, GETs it back — the whole graph from handler to in-memory repo.
- **No-leak:** responses decode into the public DTO types; a domain object would
  not compile against the `Client` signature.
- **Fake-repo substitution:** `service_test.go` defines its own
  `fakeCampaignRepository` satisfying the v2 `CampaignRepository` interface and
  runs the use cases against it — "a test provides its own repo impl" (v2's
  repository-is-an-interface), not an inmem-vs-real doctrine.

Plus the v1/v2 substance is real, not cargo-culted: the `Campaign` aggregate
enforces its cross-object invariants (unique slug, ≤25 links) in **both** the
constructor and the guarded `AddShortLink` transition; the `CampaignService`
methods are textbook four-step (convert → delegate → persist → respond), with
create = construct and add/deactivate = load-then-guarded-transition.

Verification (re-run independently from repo root):

```
go build ./examples/running/...     # clean
go vet ./examples/running/...        # clean
gofmt -l examples/running/           # no output
go test ./examples/running/...       # all packages pass
```

The agent also smoke-tested `go run ./examples/running` + `curl`; the service
serves.

## Sound judgment calls the agent made from the skill alone

- **CampaignName = non-empty.** The task said only "a name"; the agent applied the
  primitive-obsession guidance and picked the simplest defensible VO rule,
  annotated in `campaign_name.go`.
- **ID generation in the Convert step.** The skill genuinely does not cover
  identifier generation; the agent generated an opaque random-hex ID at Convert,
  before constructing the aggregate, and said so in a comment. Reasonable, and a
  candidate skill gap to note (not fix now).
- **The service speaks the *public* package's DTOs directly.** This is what makes
  the embed satisfy the `Client` with zero forwarding — and it is exactly what
  `go.md#the-composition-root` teaches ("the service's methods must already have
  the `Client`'s signatures … because Convert and Respond already speak DTOs").
  The agent noted it read as ambiguous until the composition-root section resolved
  it. Acceptable progressive disclosure (wiring concerns resolve in the wiring
  section); an optional one-line forward-reference from `application-services.md`
  is a possible fast-follow, weighed against over-coupling the v2 doc to v3.

## Known friction confirmed (not a gate failure)

Out of curiosity the agent ran the repo's own `cmd/ddd-vet` over
`examples/running/` and it flagged `Campaign`/`ShortLink` as VO candidates and
the service/repo/handler for lacking a validating `NewX(...) (X, error)` — the
**seam/entity/aggregate misclassification** already harvested in v2 (any
`New*→X` read as a VO constructor; `-gen-excludes` auto-excludes only
entity/aggregate by ID/collection signal, so seams need a manual exclude list).
CI runs `ddd-vet` **only** on `examples/ddd/` (the consumer-config dogfood), so
`examples/running` — like `examples/lending` — is kept conformant by
`go test ./...` + `go vet` + `gofmt`, not by `ddd-vet`, and needs no
`.go-ddd.yaml`. The friction remains the standing analyzer fast-follow: teach
`ddd-vet` the service/repo/public-interface shapes.

## Verdict

**PASS.** A fresh agent, from the skill alone and with the patterns never named,
produced the public/impl split, the embed-to-satisfy `Client`, the composition
root that owns the impl choice and injects the handler, and the handler that
depends only on the public contract — with all five assertions and all three
required tests satisfied, build/test/vet/gofmt clean, and genuinely runnable. The
skill teaches v3.

Remaining v3 work: the pilot copy-in + observed discovery-loop session (gated on
pilot access) — the only unshipped piece.
