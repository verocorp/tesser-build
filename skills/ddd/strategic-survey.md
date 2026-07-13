# Strategic survey — reading an existing codebase for its contexts and layers

You are **not building** here. You are **reading an existing codebase** to make it
legible: to surface the **bounded contexts** and **ubiquitous language** it already
exhibits, tag each area's **hexagonal layer**, and flag where boundaries are
violated — so a human can decide what to rewrite, re-architect, keep, or iterate.

This is the survey that precedes the architecture work in `SKILL.md` (Mode 1).
The tactical skill assumes you know where you are; this one is for when you land in
a large, coupled, unfamiliar codebase and *don't*.

Concept authority: bounded context, ubiquitous language, subdomain classification,
and the context-mapping patterns are Evans (*Domain-Driven Design*) and Vernon
(*Implementing DDD*), paraphrased. The survey *method* — reading these out of
existing code rather than designing them forward — is the ported vero practice,
genericized.

## The prime directive: as-is, not to-be

A survey reports **what the code already is**, and **candidates** for what it
could become. It never emits the target design as fact.

- In a well-structured codebase, modules approximate contexts and the survey gets
  you most of the way. In a **coupled, agent-written mess, the boundaries in the
  code are accidental** — so a survey that "discovers the contexts" from that
  structure will faithfully reify arbitrary divisions and hand them over as if
  they were a design. That is the trap.
- The target contexts and the go-forward language are a **design act**, triangulated
  with the domain (the people who know the business), not extracted from the code.
- So every finding is a **candidate presented as a question with its evidence
  attached**, for a human to ratify — never a verdict. The machine flags
  candidates; the human ratifies. This is the same discipline the analyzers use
  (`value-objects.md#how-the-machine-sees-it`), applied one level up.

## Is this what I'm doing?

**Test:** *Am I reading code I did not write to understand its latent structure —
before deciding what to change?* Yes → survey.

**Near-misses that are NOT this skill:**
- **Architecting a feature** — you know the domain and are placing new nouns/rules.
  That is `SKILL.md` Mode 1.
- **Splitting a module you own into contexts** — a forward design decision. Use the
  ratification heuristic below for the criteria, but you are *designing*, not
  surveying.
- **Reviewing a diff** — bounded to a change set, not a whole-codebase read.

## What you produce (the output contract)

A two-axis, per-area map plus a staged disposition. Fix this target before you start.

- **Axis 1 — contexts + language:** candidate bounded contexts; the **existing**
  ubiquitous language per candidate; **term-forks** (one word, different
  shape/meaning in different places) and **synonym sprawl** (several words for one
  concept) called out explicitly. Gated on *ratified* contexts (annotations, not
  verdicts): subdomain tier and per-edge integration-pattern label.
- **Axis 2 — layers + violations:** the current hexagonal layer of each area, and
  where the boundary discipline is broken (reach-through, domain-depends-outward,
  logic-in-the-wrong-place).
- **Disposition per area (staged, not decided by the tool):** a candidate
  rewrite / re-architect / keep / iterate from the rubric below, for a human to
  ratify.

**Two rules bind every line of output** — the survey's own contract (they echo the
scoring discipline in `rationale/changeability/SCORING.md`, made this survey's own):
1. **Anchor every finding to `file:line`.** A claim with no location is not a
   finding; it is a vibe.
2. **Every finding triggers a named action.** A logged finding that changes
   nothing is not an accepted outcome.

## The survey loop

The skill *is* this loop. Run it per area, iteratively:

1. **Scope** — pick the area set. The **bootstrap unit is whatever physical
   grouping the code already has** (directory / package / module); you do not need
   contexts to exist to scope an area, because on day one an area is just "a
   directory." Confirm the scope fits one honest read (see *Running it at scale*).
2. **Evidence pass** — run the signals below over the area, gathering `file:line`
   evidence. (Which signals are cheap to run depends on tooling — see *The
   signals*.)
3. **Present candidates as questions** — surface each candidate seam, term-fork,
   layer tag, and violation *with its evidence*, phrased as a question. "`order`
   carries different fields in `checkout/` than in `fulfillment/` — one context or
   two?" Never assert the boundary.
4. **Capture ratification** — the human accepts / rejects / redraws each candidate.
   Their domain knowledge is the arbiter, not the code's current shape.
5. **Emit** — the ratified two-axis map + staged dispositions, every line anchored
   and action-bearing.

---

## Axis 1 — bounded contexts + ubiquitous language

A **bounded context** is a boundary within which one domain model, and one meaning
per term, holds; cross the boundary and the same word can mean something else
(Evans). The survey's job is to find where the code's *language* fractures — because
**a term that forks meaning is the single best code-derived signal of a latent
context boundary.**

### The signals that survive a mess

Four signals suggest a real boundary. They are the diagnostic inversion of the
design-time split criteria — instead of "should I split here?", ask "what does the
code already show?" Each maps to an evidence pass; the passes are ordered by how
well they survive a coupled codebase.

1. **Different ubiquitous languages — term-fork / vocabulary divergence.** The same
   concept named differently, or one name carrying different shapes, in different
   areas. *Evidence:* per-area identifier and type-name inventories; then diff them
   for the same word with divergent fields, and for different words that clearly
   name one concept. **This is the primary signal** — it is what a context boundary
   *is*, and it survives coupling because vocabulary lives in names, not structure.
2. **Different rates of change — behavioral / change coupling.** Areas that change
   on different clocks are different contexts; areas whose files consistently
   **co-change** are a candidate cohesive unit *regardless of how tangled the
   imports are*. *Evidence:* commit history — files that change together, and
   per-area change frequency. **Caveat that decides its worth:** in a codebase
   written by agents in large batch commits, co-change collapses to noise. Check
   commit granularity before trusting this signal (see *Running it at scale*).
3. **One-way data flow — dependency direction.** Area A produces what B consumes but
   B never writes back — a natural asymmetry that maps to a boundary. *Evidence:*
   cross-area import/call direction. In a mess the static graph is largely noise
   (everything reaches everything), so weight this **below** the two signals above.
4. **Different owners — authorship.** Different people maintaining different areas is
   a boundary candidate. *Evidence:* commit authorship per area. Weakest signal;
   use only to corroborate.

### Counter-signals — when an apparent seam is NOT a context

An apparent boundary is *not* a real context if:
- **Tight transactional coupling** — the two areas must succeed or fail together in
  one transaction. Splitting them forces distributed-transaction machinery where
  none was needed. Ask: "must these be atomic, or can they be eventually consistent?"
- **Shared aggregate** — both areas operate on the same entity under the same
  invariants (`aggregates.md`). A boundary between them would force one to reach
  into the other's state — defeating the boundary.
- **"Just a package"** — same language, same rate of change, same owners. That is a
  package boundary *within* one context, not a context boundary.

### The ratification heuristic

For each candidate, present the code-evidence and ask the ratifying question — the
*observation* is the tool's, the *verdict* is the human's. This is the diagnostic
inversion of the design-time decision heuristic: a read to confirm, not a rule the
tool applies. Never let an item resolve to "→ separate contexts" on its own; the
human's answer is the resolution.

1. The code shows **different language for the same concept** across these areas —
   a real context boundary, or drift to reconcile inside one?
2. These areas **change at different rates or have different owners** — separate
   contexts, or one context living with churn?
3. The **data flow reads as one-directional** here — a natural boundary, or an
   accident of the current wiring?
4. Must operations be **atomic across both** areas? If so, likely one context
   despite the surface split.
5. Would the **integration cost** (DTOs, interfaces, mapping) outweigh the isolation
   benefit? If so, keep together behind a package boundary.

### Gated on ratified contexts (annotations, not verdicts)

Only *after* the human ratifies a context do these apply — labeling them on
*speculative* contexts is itself a to-be act:

- **Subdomain tier** (Evans): **Core** (the differentiator — invest in a rich model),
  **Supporting** (necessary, not differentiating — good enough), **Generic**
  (commodity — buy or wrap off-the-shelf). Tier tells you where modeling effort is
  worth it, and it feeds the disposition rubric.
- **Integration pattern per edge** (Evans/Vernon), as a label on the relationship
  between two ratified contexts: **Open Host / Published Language** (stable upstream
  interface many consume), **Conformist** (downstream adopts upstream's model
  as-is), **Anticorruption Layer** (downstream translates at the boundary to stay
  clean of upstream churn), **Separate Ways** (no integration). In a legacy survey
  the common finding is **no clean pattern at all** — inline cross-area calls and
  shared mutable state — which is itself the flag.

---

## Axis 2 — hexagonal layers + boundary violations

For each area, tag which layer it currently occupies, in this repo's terms
(`SKILL.md`, `composition-root.md`): **domain** (value objects / entities /
aggregates), **application service** (coordination), **repository / port**
(persistence boundary), **adapter** (a concrete impl behind a port), **handler**
(transport), **composition root** (wiring). In a coupled codebase most areas will be
**smeared across layers** — that smearing is the finding.

**The boundary is the definition, not the collection** (`aggregates.md`): you are
looking for where the *rules a boundary should guard* have leaked past it. The
violation flags:

- **Reach-through** — a caller depends on a concrete/backend type instead of the
  contract, so a change forces every dependent that reached through the boundary to
  move. The coupled anti-pattern the whole hex discipline exists to prevent.
- **Domain depends outward** — a domain type imports or emits an outward
  representation (SQL, JSON, a framework type). The direction rule is inward-only:
  the domain depends on no outward layer, and the representation never leaks.
- **Verb-placement / logic in the wrong home** — the most common smell in
  agent-written code: business logic living in a handler or a framework endpoint,
  and persistence living in the domain. Ask the placement question of each line:
  *where does this behavior go?* (`SKILL.md` Mode 1, step 4). A `for`-loop over
  domain objects or a DB call inside a handler is misplaced behavior, not
  architecture.

Every violation is a `file:line` finding that names its corrective action (move the
logic to the owning type, introduce the port, invert the dependency).

---

## From findings to disposition

The tool **proposes**, from a transparent rubric; the human **ratifies**. Draft
rubric (pressure-test it against real code and adjust):

- **Rewrite** — high violation density **and** Core tier **and** no salvageable
  seam. The area is central, wrong, and has no boundary to preserve.
- **Re-architect** — the domain logic is sound but **mis-placed** (classic
  verb-placement). Pull it out of handlers/adapters into the right layer; the rules
  survive, their home changes.
- **Keep** — low violation density, or Generic-tier commodity. Leave it.
- **Iterate** — Supporting-tier with **localized** violations. Incremental fixes,
  not a rebuild.

Tie each disposition to its evidence (the tier from Axis 1, the violation count from
Axis 2) so the human can check the reasoning, not just the verdict.

---

## Running it at scale

A single linear read of a few-hundred-KLOC codebase **will sample-and-miss**. Honest
coverage needs one of:

- **Fan-out** — parallel readers, one per top-level area, each returning its
  per-area map, then a synthesis pass that reconciles them and finds the
  cross-area seams. This is how the survey *executes* at scale; it is not a
  different method.
- **Deterministic evidence** — where a signal is worth trusting mechanically (term
  inventories, a change-coupling matrix), a script produces the complete signal so
  the reader reasons over ground truth instead of a sample. Which one to build
  first is an open decision that a hand-run should settle — start with the primary
  signal (term-fork) unless the codebase's commit history is granular enough to make
  change-coupling reliable.

**When there are no subsystems to pick.** A coupled blob with no module boundaries is
the common legacy case — and the *absence* of boundaries is itself the headline
as-is finding. Take the whole target (e.g. the whole backend) as the unit, fan out
by whatever top-level grouping exists, and treat the result as a **coverage-partial
first cut**, not a complete map.

**The commit-granularity check.** Before trusting the change-coupling signal (2),
inspect a sample of commits: do they touch dozens of unrelated files at once? If so,
co-change is noise on this repo — lean on term-fork (1) and drop change-coupling to
corroboration. This one observation decides which deterministic extractor is worth
building.

## The honest limits

- The survey finds **candidates**; the contexts and the go-forward language are the
  human's design call. Do not let the tool's confidence read as authority.
- The static dependency graph is **noise** in a coupled codebase — do not build the
  context map from it.
- Change-coupling **dies on batch commits**; authorship is the weakest signal;
  term-fork carries the primary axis. Weight accordingly.
- No analyzer backs any of this — it is **review, not the compiler**. That is
  expected: this layer is judgment-first by nature, which is exactly why it is a
  human-partnered survey and not a gate.
