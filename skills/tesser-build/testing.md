# Norm: testing

<!-- tb-status: partial -->

**v0 of the testing norm covers how a test is written and what it must
prove — not how the suite is laid out.** Rules 1 and 9 are machine-checked
today; rule 2 is ruled doctrine whose checker is specified by its fixture pair
and lands next; the rest is guidance enforced by review. What is genuinely undecided is
listed as open at the bottom rather than smuggled in as prose (Chris ruling
2026-07-20).

The per-component `## Tests you must write` sections say *what* to test. This
file says *how*, and it is the cross-cutting layer they assume.

## The norm

1. **Test doubles are hand-written.** Never a mocking library — not
   `unittest.mock`, not the `mock` backport, not `pytest-mock`'s `mocker`, and
   not pytest's `monkeypatch`/`MonkeyPatch` runtime patchers. Write a double
   that implements the collaborator's interface and inject it through the interface.
   Two tiers, both hand-written:
   - **isolated unit test** — a small hand-written double standing in for one
     collaborator;
   - **orchestration / integration test** — a real in-memory implementation of
     the port (an in-memory repository), not a bespoke stub.

   A mock library couples the test to the *call shape* instead of the
   *observable outcome*, and it is blind to interface drift: change the
   collaborator's signature and the mock-based test stays green while the real
   integration is broken. A hand-written double fails loudly at exactly that
   change, which is the point.

2. **Every spec-constructed type has one completeness test.** Construct a valid
   instance from a full spec, then assert that *every* spec field round-tripped
   to its accessor — compared against the spec's value, never a hardcoded
   literal.

   ```go
   func TestNewPassenger_Valid(t *testing.T) {
       spec := validPassengerSpec()
       p, err := NewPassenger(spec)
       if err != nil { t.Fatalf("NewPassenger(%+v) returned unexpected error: %v", spec, err) }
       if got, want := p.ID().String(),   spec.ID;   got != want { t.Errorf("ID() = %q, want %q", got, want) }
       if got, want := p.Name().String(), spec.Name; got != want { t.Errorf("Name() = %q, want %q", got, want) }
       if got, want := p.Seat().String(), spec.Seat; got != want { t.Errorf("Seat() = %q, want %q", got, want) }
   }
   ```

   ```python
   def test_constructs_from_spec() -> None:
       spec = _valid_spec()
       link = ShortLink(spec)
       assert str(link.slug) == spec.slug
       assert str(link.target_url) == spec.target_url
       assert link.active is spec.active
   ```

   A field added to the spec but never asserted is a silent site: construction
   can drop or mis-assign it and nothing fails. This test is the one place the
   full construction contract is stated, which is why it is exhaustive where
   behavior tests deliberately are not (rule 3). Comparing against `spec.X`
   rather than a literal is what makes it a round-trip rather than a
   restatement of the fixture.

3. **Assert only what you control or what was computed.** Two categories are
   legitimate: a value you explicitly set in the test input, and a value the
   code under test computed. Anything else is a **hidden default** — a value
   supplied by a fixture or constructor default that the test never chose.
   Asserting it couples the test to the fixture's internals, so an unrelated
   default change breaks tests that were never about it. Golden rule: *if you
   cannot trace where a value came from in your test input, do not assert it.*

   The completeness test (rule 2) is the deliberate exception: proving complete
   construction *is* its claim, so it asserts the full field set.

4. **Test one claim.** One test proves one thing. The "unit" is the claim, not
   the function count — a claim that spans two operations is still one claim.
   A test that would need "and" to describe it is two tests.

5. **Trust your layers.** Exhaustive edge cases belong at the value-object
   layer; composition and orchestration at entities and aggregates; real
   scenarios and error paths at services. Do **not** re-test a lower layer's
   edge cases higher up — if `Slug` already proves it rejects malformed input,
   the aggregate's tests prove the aggregate *uses* `Slug`, not that `Slug`
   validates. Re-asserting the same claim at every layer means one rule change
   edits N suites.

6. **Fail fast on what invalidates the rest.** In Go, `require` for a check
   whose failure makes later assertions meaningless or panicky (construction
   returned an error, a slice is the expected length), `assert` for independent
   checks that can each report. In Python the distinction largely collapses —
   a bare `assert` already halts — so the residue is ordering: establish that
   the object constructed before asserting anything about it.

7. **Arrange-Act-Assert, structurally.** Separate the three phases with blank
   lines. Never with comments — `comments.md` is zero, tests included, so the
   comment-delimited form of AAA is unavailable here by construction.

8. **Name the scenario and the outcome.** `test_rejects_duplicate_slug_at_construction`,
   not `test_duplicate` or `test_1`. The name is what a failure report shows;
   it should say what broke without opening the file.

9. **A test helper builds a spec or a DTO. Nothing else.** A helper's entire job
   is to hold the values a test does not care about, so the test can state only
   the one or two that make it *that* test. It never returns a constructed
   domain object, and it never calls anything.

   ```python
   def _spec(slug: str = "spring-sale", active: bool = True) -> ShortLinkSpec:
       return ShortLinkSpec(slug=slug, target_url="https://a.example", active=active)


   def test_deactivate_is_guarded() -> None:
       link = ShortLink(_spec(active=False))
       ...
   ```

   The construction stays in the test, where the reader can see it. `active=False`
   is the whole reason this test exists, and it is the only argument written.

   Four consequences, each of which is the rule doing its work:

   - **Never return a constructed domain object.** `_money(...) -> Money` hides
     the construction the test is about; `_spec(...) -> MoneySpec` and
     `Money(_spec(...))` at the call site does not. If a helper returns an
     aggregate, the test that "sets up a campaign" no longer shows what a
     campaign is.
   - **Never call.** A helper that invokes a service, a builder, or a
     composition root is not holding defaults, it is performing the arrangement
     — and the arrangement is what the test needs to show. `_campaign_with_link(svc)`
     reads as one line and hides two service calls; write them out. This is the
     same defect as a helper that is a pure rename of the thing it wraps.
   - **Defaults go in keyword arguments, not functional options.** Functional
     options exist to work around Go's lack of keyword arguments; Python has
     them. The ported form declares every field three times (draft class,
     per-field `with_` function, final mapping) — 63 lines against 26 — nested
     specs compose worse because names flatten to positional, and a field
     nobody wrote an option for is silently unreachable.
   - **A spec field holds a primitive or another spec, never a converted type.**
     This is what keeps the rule above achievable: building a child spec needs
     no parsing, so every override is a plain assignment. A converted field
     (a `Decimal`, a parsed timestamp) forces the helper to parse and handle
     failure, and a helper with error handling in it is logic.

   **Threshold: two fields or more.** A single-field type is constructed
   directly — `MoneyAmount("1.5")` needs no helper and a helper would only
   hide it. Two or more fields earns one, because that is where the defaults
   start costing the reader.

   **Assertion helpers are out of scope**, deliberately. A helper that asserts
   is a different tool with different trade-offs; a library can provide those.
   This rule is about construction.

## Where the norm applies

- **Constructed-app code** — the tests the skill routes you to write in a
  consumer repo, at every layer.
- **The example trees** (`examples/`) — the norm's verified impls; they conform
  and are gated in CI.
- **Not the toolkit's own internals** (analyzers, generator, `rationale/`
  contenders), which are outside the governed surface, same as `comments.md`.

## How the machine sees it

- **`TB030` (no-mock-libraries)** — rule 1. Flags a mocking-library import in
  any shape (`unittest.mock`, the `mock` backport, the
  `import unittest` → `unittest.mock.patch` reach-through) and
  `pytest.MonkeyPatch`; the import branches are **global**, because domain code
  has no business importing a mock library either. The `monkeypatch` / `mocker`
  **fixture-parameter** branch is narrower on purpose — it fires only inside a
  pytest-shaped function (`test_*` or a `@fixture` factory), since a parameter
  with that name anywhere else is an ordinary identifier.

  **The escape hatch, and its one honest use.** A test that must patch a boundary it
  cannot inject through carries `# tessercheck:ignore` (suppression scans the
  reported statement's whole line span, so it works on a formatter-wrapped
  import). Today the only sanctioned uses are the composition-root wiring tests
  in `examples/python-app`, which patch a wiring module's own `build` function
  to force a partial-failure path — there is no injection point above the
  composition root, which is exactly why they qualify. Note this is a *narrower*
  claim than "a process boundary": giving `bootstrap` an injectable builder would
  let those tests use a hand-written double and delete the suppressions
  entirely. That is tracked as a follow-up, not a blessed pattern to copy.
- **`TB031` (construction-completeness)** — rule 2. **Not shipped yet:** its
  contract is fixed by the reviewed fixture pair
  (`tessercheck-py/testdata/tb031/{good_tree,bad_tree}/`), authored before the
  checker per the fixtures-first discipline. When it lands it will compare a
  spec-constructed type's field set against the fields asserted in its
  completeness test and flag the difference. Until then rule 2 is enforced by
  review.
- **`TB071` + `TB073` (test-module totality)** — rule 9, and the analyzer's
  first **totality** check (they superseded the frozen-dataclass era's
  `TB032`). Every other check hunts a known-bad shape and stays quiet
  otherwise. That is the wrong instrument here, because the failure mode is
  *variety* — there is no single bad helper to match, and new ways to smuggle
  logic into a test module arrive with every feature. So this one inverts it:
  **every module-level function in a test module must classify**, and what does
  not is reported. Read the output as a worklist, not an accusation.

  Classification is declared, never inferred: a test module holds tests,
  **`@ts.helper`** builders, and **`@ts.fake`** doubles, and a module-level
  function that is none of those is a `TB071` finding. `TB073` is the shape
  half: a declared helper takes only defaulted primitives, has no control
  flow, and builds a spec. A helper that legitimately builds something else —
  a wired object graph for an end-to-end test, a JSON payload — declares
  itself with `@ts.helper` and opts out of the shape rule with a per-instance
  `# tessercheck:ignore TB073` on its `def` line; the declaration half is
  never optional.

  Two scope facts worth knowing before you argue with a finding:
  **methods are not judged** — every non-test method on a class in a test file
  is a hand-written double, which rule 1 *requires*, so judging them would
  report the norm's own mandated shape as a violation. And **a test module is
  one whose basename starts with `test_`**; a helper-only module beside the
  tests (`tests/support.py`, a `conftest.py`) is judged as ordinary code under
  the other rules, not under these, so parking helpers there buys nothing.

- Rules 3-8 are **guidance, not checked.** Each is either a semantic judgment
  (3, 4, 5) or not mechanically decidable in a way worth the false positives
  (6, 7, 8). That is deliberate: semantic correctness is test territory,
  structure is analyzer territory.

## Open — deliberately not decided in v0

These have no ruling and are **not yet materialized** — no rule here, no
example, no checker. They are listed so their absence is visible rather than
silently filled by whatever the examples happen to do. If you hit one,
**don't invent a convention**: ask, or leave the existing shape alone until it
is ruled.

- **Test file layout.** Colocated beside the module vs a separate `tests/`
  tree. Go and Python differ on the axis itself — Go's question is the package
  declaration (`package foo` vs `package foo_test`, same directory), Python's
  is directory placement — so the Go convention does not port. Unresolved, and
  we have declined once already to let a checker dictate test placement.
- **Test grouping / structure.** Whether a type's scenarios group under a test
  class, and at what grain ("unit" = a type, a callable, or a concern). Cut
  from v0: too ambiguous on the right shape to encode as doctrine.
- **Table tests / `@pytest.mark.parametrize`.** Prior art points both ways.
  Currently used for rejection cases in the worked trees; not ruled.
- **Coverage stance.** No percentage gate anywhere, and v0 inherits that —
  binary pass/fail. Revisit only if live use shows coverage gaming.
- **An equality-test tripwire.** A checker requiring each value object to carry
  an explicit equality test was built once on the Go side and parked; it is a
  candidate for a later wave, not a v0 rule.

## Common mistakes

- **The mock that can't fail.** `sender.send.assert_called_once_with(...)`
  passes forever, including after `send` changes shape. Assert the observable
  outcome through a hand-written double instead.
- **Asserting the fixture.** `assert money.currency == "USD"` when the test
  never set a currency — the helper's default leaked into the claim.
- **The re-tested layer.** Proving invalid input is rejected at the aggregate
  when the value object already proves it. One rule, one home.
- **The literal round-trip.** A completeness test asserting
  `str(link.slug) == "spring-sale"` instead of `== spec.slug` — it restates the
  fixture rather than proving the spec reached the field.
- **The partial completeness test.** Constructing from a full spec and
  asserting one field. That is a behavior test wearing the completeness test's
  name; the other fields are unproven.
- **The helper that arranges.** `id = _campaign_with_link(svc)` reads as one
  line and performs two service calls. Eight tests shared that line and not one
  of them showed what it was arranging.
- **The rename in helper's clothing.** `def json_body(resp): return decode_body(resp.body)`
  supplies no default and saves no reader anything — it just adds a name they
  have to learn. If a helper has no default in it, it is not a helper.
- **The over-supplied call.** `_spec(slug="spring-sale")` when `"spring-sale"`
  is already the default. The argument reads as significant and is not; it
  buries the one that is.
