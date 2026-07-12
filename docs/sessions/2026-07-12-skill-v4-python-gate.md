# Acceptance-gate record — skills/ddd v4, the verified Python rendering (2026-07-12)

The v4 increment closes the one place the toolkit violated its own principle —
that the skill encodes only how-to a **verified implementation** backs. Before
v4, `python.md` was an unverified port of the Go doctrine (no Python existed in
the repo). v4 ships the verified Python rendering — a reference example
(`examples/python`, hand-authored then debugged against `mypy --strict` +
`pytest`) plus this **fresh-agent gate**, which proves the skill *alone* teaches
an agent to produce correct DDD Python. It is the Python peer of the Go gates
that produced `examples/lending` (v2) and `examples/running` (v3).

Because a genuine compound value object and a collection value object turned out
to be exercised by **no** runnable example in either language (every VO in
`examples/{ddd,lending,running}` is single-field), v4 also added
`examples/catalog` (Go, `*big.Rat` Money + map `Labels`) and
`examples/python/catalog` (Python, `Decimal` Money + sorted-tuple `Labels`) so
`go.md` and `python.md`'s VO exemplars are backed rather than illustrative.

## Setup — Python gate, Claude Code host (fresh Sonnet agent) — PASS

A fresh Sonnet agent with **no knowledge of the design** was given only the skill
entry point (`skills/ddd/SKILL.md`, which routes onward under progressive
disclosure) and a neutral **expense-report** task ("Expensewell"): a team member
creates a report holding expenses, each with an exact-money amount, a category,
and a receipt number; a report totals its expenses and may not exceed 1000.00; no
two expenses may share a receipt number; at most 20 expenses; one currency; a
draft→submitted lifecycle that can only fire once; a system-assigned report id;
a set of freeform labels; four operations (create, add expense, submit, fetch)
exposed over HTTP as a runnable service; with tests.

The temptations were **embedded but never named** — the prompt never said value
object, entity, aggregate, application service, repository, public interface,
composition root, or DTO. The agent had to reach those from the skill. It was
told to build in a scratchpad, to use the standard library only, to make
`mypy --strict` and `pytest` clean, and **not to consult `examples/`, `docs/`,
`rationale/`, or any memory/session files**.

Output: `examples/python-expenses/` (committed as-produced) — 25 source files,
6 packages. Layout:

```
examples/python-expenses/
  main.py                 the composition root: wire() + main()
  transport.py            stdlib http.server JSON handler (the one-handler-rule layer)
  expenses/               the domain: Money (compound VO, Decimal), Labels (collection VO),
                          ReportID/ReportTitle/ReceiptNumber/Category (simple VOs),
                          Expense (VO), ExpenseReport (aggregate root; draft→submitted;
                          ≤20 / unique-receipt / one-currency / ≤1000 invariants)
  expensewell/            the public contract: Client Protocol + DTOs only, zero internal imports
  expensewellapp/         the seam: ExpenseReportService (4-step) + ExpenseReportRepository Protocol
  expensewellimpl/        the impl: in-memory repo + new_client(svc)->Client (structural satisfaction)
  tests/                  unit + end-to-end-over-wire() tests
```

## Objective criteria (verified independently — I read the code and re-ran the tools, not the agent's report)

- **`mypy --strict` clean** (25 source files) and **`pytest` green** (60 tests),
  re-run from the committed location.
- **Aggregate is the consistency boundary.** All four cross-object rules live in
  `_validate_expenses`, called from `ExpenseReport.__init__` (an invalid report
  is unrepresentable) **and re-run in `add_expense`** before a new expense is
  admitted. `submit()` and `add_expense()` guard `status is DRAFT` and raise
  `InvalidTransition`; a report can be submitted once.
- **Domain math is on the domain, not the service.** The report total is
  `ExpenseReport.total()` (summing via `Money.add`); the service never sums —
  it asks the aggregate. No `for`-over-domain-for-computation, no arithmetic on
  amounts, no `if` on domain state in the service.
- **Application service is 4-step, responses are DTOs.** `create_report`,
  `add_expense`, `submit_report`, `get_report` each convert → delegate → persist
  → respond; every response is a `*Response` wrapping a `ReportView`/`ExpenseView`
  DTO — no domain object crosses the boundary (the no-leak property).
- **Public / impl split.** The public `expensewell` package imports nothing
  internal (only stdlib). The concrete `expensewellimpl` is imported only by
  `main.py` (production) and by two tests exercising substitution.
- **Composition root.** `wire()` chooses the in-memory repository, injects it
  into the service, composes the service behind the public `Client` via
  `new_client`, and constructs the handler injecting the `Client`.
  `new_client(svc) -> Client: return svc` — structural Protocol satisfaction,
  the `-> Client` annotation as the compile-time proof. The handler depends on
  `Client` only.
- **Repository** takes and returns the whole aggregate, reconstructing it
  through its constructor (invariants re-run on load).
- **Value objects.** `Money` is a compound VO backed by `Decimal` (default
  frozen-dataclass equality, correct across representations); `Labels` is a
  collection VO with sorted-tuple storage and a defensive copy out; simple VOs
  validate in `__post_init__`; no `.String()`/`str()` equality.

## Modeling divergence (sound) and friction (honest)

- **`Expense` modeled as a value object, not an entity** — the opposite of the
  reference example's `ShortLink` (an entity). The call is correct: an expense
  has no lifecycle and is interchangeable by its attributes, so it earns no
  identity; the receipt-number uniqueness is an *aggregate invariant*, not entity
  identity. The reference's `ShortLink` is an entity because it *does* have a
  lifecycle (active→deactivated). Two agents, opposite calls, both right for
  their domain — exactly the judgment the taxonomy is meant to support.
- **Real skill friction (candidate refinement, not a failure):** the agent noted
  the taxonomy doesn't sharply address "a value with a business-unique field the
  domain didn't intend as identity" (the receipt number) — a worked example or a
  sentence distinguishing *uniqueness constraint* (aggregate invariant) from
  *assigned identity* (entity) would have shortened its reasoning. It reached the
  right answer via the taxonomy tests regardless.
- **Task-spec ambiguity, not skill friction:** "may not exceed 1000.00" vs "all
  amounts share one currency" — the agent read the cap as 1000.00 in the report's
  shared currency rather than hard-coding USD. A reasonable resolution.
- The only `mypy --strict` frictions were the agent's own (a redundant
  enum-narrowing assert; `object` vs `Any` in a test helper) — self-fixed, not
  the skill's.

## Verdict

**PASS.** From the skill alone, a fresh agent produced a correct, type-checked,
runnable DDD Python service across the full arc — domain building blocks, the
seam, the public interface, and the composition root — with invariants placed on
the aggregate, no domain-object leak, and structural Protocol satisfaction. The
verified Python rendering meets the same bar as the Go mechanics; `python.md` is
no longer an unverified port.
