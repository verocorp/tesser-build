# Start here: learning DDD with this repo

You've landed in a toolkit that enforces domain-driven design conventions.
This page is the human on-ramp: what the concepts are, why the conventions
exist, and where everything lives. (Agents don't start here — they load
`skills/tesser-build/SKILL.md`, which routes them task-by-task.)

## The idea in three sentences

Domain-driven design's tactical patterns (Evans, *Domain-Driven Design*, 2003;
Vernon, *Implementing Domain-Driven Design*, 2013) give every domain concept a
home with rules: values that validate themselves, identities that persist, and
boundaries that keep multi-object rules true. This repo's bet is narrower and
testable: **consistently-built domain objects make change cheaper**, because a
change to a concept lands in one place instead of rippling through every call
site — and inconsistently-applied conventions buy you nothing. So the
conventions here are enforced by machines (analyzers in CI), demonstrated by
executable evidence (`rationale/`), and taught to agents (`skills/tesser-build/`), not
just written down.

## The three building blocks (v1)

| Concept | One-question test | In one line |
|---|---|---|
| **Value object** | Could I swap this for another instance with the same attributes and nothing changes? | A validated value with no identity — `EmailAddress`, `Money`. Immutable, always. |
| **Entity** | Must the system track *this specific one*, even if another has identical attributes? | Identity over time — a `Transfer`, a `Contract`. Mutable only if the domain has a lifecycle. |
| **Aggregate** | Does this enforce rules across a group of objects it owns, as their single entry point? | A consistency boundary with a root — an `Operation` whose transfers must balance. |

Identity and consistency scope are the axes — **not** mutability, and not
importance. Most domain nouns are value objects; identity must be earned.

The **seams** around those blocks are now covered too — **application services**
(coordinate a use case, hold no business logic) and **repositories** (the
persistence boundary), plus a **domain-service stub** for the rare operation
owned by no single object. Together they answer the placement question — where a
line of behavior goes — which is where most spaghetti actually forms. Still on
the roadmap: bounded contexts, the transport/HTTP layer beyond the one handler
rule, and domain events.

## Where everything lives

- **[`faq.md`](faq.md)** — the questions everyone actually asks ("entity vs
  aggregate — when do I use which?"), answered as decisions. Start there when
  a distinction feels fuzzy.
- **[`skills/tesser-build/`](../skills/tesser-build/)** — the agent-facing skill: a router plus
  per-concept and per-language (Go, Python) construction guides. Also the most
  precise statement of the conventions — humans can read it too.
- **[`rationale/`](../rationale/)** — the executable "why": three competing
  implementations of one domain, with tests that *assert* the conventions'
  wins (and benchmarks that admit their costs) instead of narrating them.
- **[`passes/`](../passes/) + the README** — the analyzers that enforce the
  value-object conventions in CI, and how to install them.
- **[`docs/design-three-contender-changeability.md`](design-three-contender-changeability.md)**
  — the change-speed metric behind the whole repo, and the adoption ladder:
  docs → skills → CI.
- **[`field-audit-checklist.md`](field-audit-checklist.md)** — the
  consumer-side field-audit runbook: run it inside a consumer repo, behind
  that repo's IP wall.

## The adoption ladder

You don't have to take all of it at once:

1. **Docs** — read this page and the FAQ; agree the concepts name real things
   in your domain.
2. **Skill** — copy `skills/tesser-build/` into your repo (see the README's
   "Distribution" section) so agents build new domain objects consistently
   from day one. This is the highest-leverage step for agent-heavy codebases.
3. **CI** — install `tessercheck` (README) so the conventions can't silently
   erode. Generate your exclude list with `-gen-excludes` and ratify it by
   hand — the machine flags candidates; you make the domain calls.
