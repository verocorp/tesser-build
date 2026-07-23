# Strategic design — subdomains, bounded contexts, ubiquitous language

<!-- tb-status: full -->

Strategic design decides **where the model boundaries go and what language holds
inside them** — the problem-and-solution-space concepts that sit *above* the tactical
building blocks (value objects, entities, aggregates). The building blocks fill a
boundary once it is drawn; strategic design draws it. Concept authority: Evans
(*Domain-Driven Design*, Part IV — Strategic Design) and Vernon (*Implementing
Domain-Driven Design*, chs. 2–3), paraphrased.

Load this when you are deciding **where a context boundary goes**, whether two areas
are one model or two, what to **name** the domain language, how much to invest in a
given area, or how two parts of the system should talk. It is an oracle to reason
with, not a construction recipe — none of these has an analyzer; they are review
and judgment.

## The strategic taxonomy in one pass

| Concept | One-question test | Section |
|---|---|---|
| **Subdomain** | Is this a distinct area of the *business* — its own purpose, its own importance? | [#subdomains](#subdomains) |
| **Bounded context** | Is this a boundary — of model, team, codebase, or schema — within which one model and one language hold, and outside which the same word may mean something else? | [#bounded-contexts](#bounded-contexts) |
| **Ubiquitous language** | Is this the agreed vocabulary — one term, one meaning — spoken inside one context? | [#ubiquitous-language](#ubiquitous-language) |

**Problem space vs solution space.** A subdomain is the *business's* shape; a bounded
context is *your model's* shape. Prefer aligning them one-to-one where it keeps the
model coherent — but this is a heuristic, not a law: a core concern can span several
contexts, and one problem area can hold more than one context (Evans; Fowler).
Ubiquitous language is the medium that makes a context a context — the boundary is
the definition, and the definition is carried in the language.

---

## Subdomains

A subdomain is a distinct area of the **problem** domain — a slice of the business
with its own purpose. You do not invent subdomains; you discover them by asking what
the business actually does. Their value is **classification**: not every area deserves
the same modeling effort, and pretending otherwise wastes it.

### Is this what I'm modeling?

**Test:** *Is this a distinct area of the business, with its own purpose and its own
level of importance to why the company wins?* Yes → a subdomain worth classifying.

### The three tiers

Classify each subdomain by how much it differentiates the business — this sets the
modeling investment:

| Tier | What it is | Invest |
|---|---|---|
| **Core** | The thing that makes the business win. Your competitive edge. | **High** — rich domain model (careful VOs, entities, aggregates, invariants). This is where the tactical skill earns its keep. |
| **Supporting** | Necessary, but not a differentiator. Specific to you, but not special. | **Medium** — model it well enough; do not gold-plate. |
| **Generic** | A commodity every business needs (auth, tax, notifications). | **Low** — prefer to buy, adopt, or reuse; build only thinly, and only where nothing off-the-shelf fits. |

### Rules

1. **Classify before you model.** The tier decides the effort. A Core subdomain gets
   the full tactical treatment; a Generic one gets a thin adapter.
2. **Core is small and precious.** If everything looks Core, the classification is
   wrong — most of any system is Supporting or Generic.
3. **Generic: prefer buy over build.** Evans gives a generic subdomain low priority
   and says reach for an off-the-shelf or published solution first; hand-rolling your
   own auth/tax/billing-rails spends your scarcest effort where it buys no advantage.
   Build it yourself only when nothing off-the-shelf fits.

### Common mistakes

- **Everything is Core.** Uniform investment across the whole system; the real
  differentiator gets the same care as the notification queue.
- **Lovingly building a Generic subdomain.** A hand-rolled commodity where an
  off-the-shelf one would do — effort spent where it wins nothing.

---

## Bounded contexts

A bounded context is a boundary within which **one domain model and one ubiquitous
language apply**. Inside, every term has a precise meaning; cross the boundary and the
same word can mean something else. The classic case: "Order" means a customer
commitment to Sales, an invoice trigger to Billing, and a pick list to Fulfillment.
Force all three into one `Order` and you get a god object that serves none of them;
give each context its own `Order` — only the fields and behavior that context needs —
and each model stays coherent.

Evans draws the boundary around more than code — team organization, the way an
application is used, the codebase, and the database schema all mark it. The
`internal/` + public `Client` structure below is *this skill's Go enforcement* of a
context boundary, not the DDD definition of one.

### Is this what I'm modeling?

**Test:** *Am I drawing a boundary inside which one model and one language hold, that
another part of the system should only reach through a deliberate contract?* Yes →
bounded context.

**Near-misses that are NOT a bounded context:**
- **A package** — a unit of code organization *within* one context, sharing that
  context's model and language. A context is a *language/model* boundary, not merely
  a folder.
- **An aggregate** (`aggregates.md`) — a *consistency* boundary *inside* one context
  (a cluster that changes together under one root). A context contains many
  aggregates; it is not one.
- **A component's public interface** (`public-interface.md`) — that is the *boundary* a
  context exposes, not the context itself. (See "How it connects" below.)

### Rules

1. **Each context owns its model.** `billing.Invoice` and `ordering.Order` are
   different types even where fields overlap. No shared internal domain objects across
   the boundary — the overlap is a coincidence of the business, not a shared type.
2. **Contexts talk through a deliberate contract, never internals.** Communication
   crosses the boundary as a **public `Client` interface + DTOs**
   (`public-interface.md`) — never by importing another context's
   internal packages. The `Client` *is* the boundary between contexts.
3. **Dependencies point one way.** If A imports B and B imports A, they are not
   separate contexts — a cycle means they cannot evolve, deploy, or test
   independently. Break it with an interface or merge them.
4. **No shared mutable state across the boundary.** Two contexts reading and writing
   one table couples their schemas and lifecycles. Each owns its persistence.

### Shape

```
app/
├── ordering/               ← bounded context
│   ├── client.go           ← public: the Client interface + DTOs (what others import)
│   └── internal/           ← hidden: this context's model, services, adapters
├── billing/                ← bounded context
│   ├── client.go
│   └── internal/
└── main.go                 ← the only place that wires contexts together
```

In Go, `internal/` makes the boundary **compiler-enforced** — a package under
`internal/` cannot be imported from outside its parent, so a cross-context reach into
another context's model does not compile. In Python there is no `internal/`
equivalent; the boundary is a convention review upholds (import-linters can approximate
it). Either way, the rule is the same: cross the boundary only through the `Client`.

### How contexts relate — integration patterns

When one context consumes another, name the relationship explicitly — it is a design
decision about coupling. These are the four **consumption** patterns you meet most
often; Evans's full Context Map also has the *symmetric/collaborative* patterns —
**Shared Kernel**, **Partnership**, **Customer/Supplier** — and names **Big Ball of
Mud** for a context with no coherent model. Those are not covered here; reach for the
DDD Reference when a relationship isn't one of these four:

- **Open Host Service + Published Language** — two combinable patterns: the *Open Host
  Service* is the stable, documented service protocol the upstream offers any consumer;
  the *Published Language* is the documented interchange schema they exchange in (the
  `Client`'s DTOs can *serve as* it once documented as a stable contract). Best when the
  upstream is stable and serves many consumers.
- **Conformist** — the downstream adopts the upstream's model as-is, no translation —
  usually a position of *weakness*: you can't influence the upstream and translating
  isn't worth it, so you conform to what you're given. Cheap, but the downstream breaks
  when the upstream changes; only tolerable when the upstream is stable enough to live
  with.
- **Anticorruption Layer (ACL)** — the downstream translates the upstream's shape into
  its own model at the boundary, so upstream churn stops at the translation. Worth its
  cost only when the upstream is unstable or a poor fit. (This is what a vendor
  `compiler`/adapter is: it keeps a kernel vendor-free.)
- **Separate Ways** — the contexts do not integrate at all. Correct when integration
  would add coupling that buys nothing.

### Decisions you must make — when to split, and when NOT to

Split into a separate context when the signals are *clear* — start with a package
boundary and graduate, because splitting too early costs integration overhead:

- **Different ubiquitous languages** — the same word means different things, or each
  area needs different words for one concept. The strongest signal (see below).
- **Different rates of change** — one area churns weekly, another is stable; coupling
  them forces churn on the stable one.
- **One-way data flow** — A produces what B consumes and B never writes back; the
  asymmetry maps cleanly to a boundary.
- **Different owners** — different teams; a shared model creates coordination cost.

Do **not** split when:

- **Tight transactional coupling** — the two must succeed or fail in one transaction.
  Splitting forces distributed-transaction machinery where none was needed. Ask: "must
  these be atomic, or can they be eventually consistent?"
- **Shared aggregate** — both operate on the same entity under the same invariants;
  a boundary would force one to reach into the other's state.
- **It's just a package** — same language, same rate of change, same owners. A package
  boundary within one context is enough.

### How the machine sees it

**No analyzer backs this.** A cross-context internal import, a bidirectional
dependency, or a `Client` that leaks a domain object are caught by **review** — except
that Go's `internal/` makes the *import* boundary compiler-enforced, and the
`Client`-speaks-DTOs rule (`public-interface.md`) is where the leak shows up. The tells
a reviewer looks for:
- an import of another context's `internal/` package — a boundary breach;
- a cycle between two contexts — they are not really separate;
- a domain object in a `Client` signature — a boundary leak (map to a DTO).

### Common mistakes

- **The god model.** One `Order` (or `Customer`, or `Product`) shared across contexts,
  accreting every team's fields until it serves none. Give each context its own.
- **Bidirectional dependency.** A imports B and B imports A — not separate contexts.
- **Shared mutable table.** Two contexts on one table; a schema change needs both
  teams and one context's write breaks the other's read.
- **Inline cross-context call.** One context calls another's service inline, coupling
  their lifecycles and failure modes. Cross the boundary through the `Client`, and
  prefer async/batch where you can.
- **Leaking upstream into downstream.** Adding a downstream-specific field to the
  upstream model — now the upstream knows about the downstream, breaking the one-way
  dependency.

---

## Ubiquitous language

The ubiquitous language is the **shared vocabulary of one bounded context** — one term,
one meaning, used identically by the domain experts *and* in the code. It is not
documentation about the model; it *is* the model's surface. A bounded context is
defined by where its language holds, so getting the language right is how you find the
boundary.

### Is this what I'm modeling?

**Test:** *Is this the word a domain expert would use for this concept, and does it
mean exactly one thing inside this context?* Yes → it belongs to the ubiquitous
language.

### Rules

1. **The code speaks the domain's words.** A type, method, or field is named for the
   domain concept (`Charge`, `settle`, `AnnualPlan`), not for the technology or the
   pattern (`DataManager`, `process`, `RecordDTO`). If the domain expert would not
   recognize the name, it is wrong.
2. **One term, one meaning — per context.** Within a context a word denotes exactly
   one concept. If "policy" means an insurance policy in one place and an access rule
   in another, the language has fractured — that is two concepts (and probably two
   contexts), not one word.
3. **One concept, one term.** Do not let `Customer` / `Account` / `Party` /
   `Client` all name the same thing in one context; synonym sprawl is drift. Pick the
   word the business uses and hold it.
4. **A term that forks meaning is a strong split signal — after you rule out drift.**
   First test whether the language can be *clarified* within one model; often the fork
   is just inconsistency to reconcile, not a boundary. If the same word genuinely must
   mean two different things, that is the signal to split contexts, each with its own
   precise definition — not to overload one type.

### How the machine sees it

**No analyzer backs this** — it is review. Two smells a reviewer hunts for: a **term
forking meaning** (one word, different fields/behavior in different places) and
**synonym sprawl** (several words for one concept). Both say the language has drifted;
the first often marks a latent context boundary.

### Common mistakes

- **Technology names for domain concepts.** `UserDataManager` where the business says
  "membership"; `processRecord` where it says "settle a charge."
- **Silent term-fork.** One `Status` enum meaning three different lifecycles across the
  system, so a change to one meaning silently corrupts the others.
- **Synonym sprawl.** `Customer`, `Account`, and `Party` all live in one context and no
  one can say which to use — every new call site picks one at random.

---

## How this connects to the tactical skill

- The public **`Client` interface** (`public-interface.md`) is the
  boundary **between** contexts — a component's contract is the boundary another context
  reaches through. The callers note in `public-interface.md` is this section.
- An **aggregate** (`aggregates.md`) is a consistency boundary **within** one context,
  not a context boundary — a context holds many aggregates.
- A **subdomain's tier** sets how much tactical modeling to invest: a **Core** context
  gets rich value objects, entities, and aggregates with real invariants; a **Generic**
  one gets a thin wrapper. Read the tier here, then build with `SKILL.md` Mode 1.
- The unsettled **cross-aggregate boundary** question (`SKILL.md` Mode 1, step 5) often
  turns out to be a context question: if a rule spans objects no single aggregate owns,
  ask whether those objects even belong in the same context before forcing a
  god-aggregate.
