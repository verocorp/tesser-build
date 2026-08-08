# Spike: the total-return rule — where it breaks

**The rule under test, stated purely:**

> Every method on a domain object returns another domain object. No primitives.
> Not `bool`. Not an enum — enums are primitives here.

`probe.py` encodes that rule with **zero licensed exits** and runs it over the
Python domain corpus (`examples/`, `tesser-py/`). `main.go` is the same probe
for the Go corpus; it needs a Go toolchain, absent from this sandbox, so the Go
sites below are cited individually rather than tallied.

Run: `python3 examples/spike-totalreturn/probe.py examples tesser-py`

```
  AggregateRoot classes: 4      Entity: 3      ValueObject: 16
  methods measured:      120
  conform already:        44
  break, LANGUAGE-fixed:  38   <- rule is unsatisfiable here
  break, private helper:  15   <- out of contract
  break, PUBLIC authored: 23   <- the rule's real scope
  public breaks by verdict: {PRIMITIVE: 14, COMMAND: 7, UNKNOWN: 2}
```

The rule breaks in four distinct places. Only the fourth is a bug list.

---

## Break 1 — Unsatisfiable: the language fixes the return type (38 sites)

`__eq__ -> bool`, `__hash__ -> int`, `__str__ -> str`, `__init__ -> None` are
not authorial choices. Go is the same: `Equal(other T) bool`.

- `tesser-py/tesser/domain/valueobject.py:18` — `__eq__` returns `bool`, and
  `:23` `__hash__` returns `int`. These are **the shipped runtime base class**.
  The rule condemns tesser's own VO contract.
- `examples/python-app/campaign/domain/short_link.py:18` — `ShortLink(ts.Entity)`
  overrides `__eq__`/`__hash__` for identity equality, exactly as
  `skills/tesser-build/entities.md:51-52` requires.
- `rationale/valueobject/temperature.go:25` —
  `func (t Temperature) Equal(other Temperature) bool`.

**Why it can't be fixed by modelling.** Promote the result to a `Truth` value
object and `Truth` needs its own equality — `Truth.Equal(Truth) -> Truth` never
bottoms out. Boolean is the terminator of the algebra, not a leak in it. And
even granting the regress: `if`, `sort`, and `in` consume a `bool` at the call
site, so the primitive resurfaces one frame up. Go has no pattern match to fold
the branch into the type; `switch c { case Greater: }` is enum comparison —
the thing the proposal declares primitive.

**Verdict: the total form of the rule is unsatisfiable, not merely expensive.**

---

## Break 2 — Direct conflict with a shipped norm (the canonical exit)

`skills/tesser-build/serialization.md` rule 3 does not merely tolerate a
primitive-returning method on a leaf value object — it **mandates exactly one**,
locked by a round-trip law.

- `examples/python-app/campaign/domain/money.py:33` — `MoneyAmount.__str__`
  returning `str` via `canonical_decimal`. This is the norm being obeyed.
- `rationale/valueobject/navigation.go:12,17,27` — `Meters.Float() float64` etc.

The probe counts these as breaks because the pure rule has no exception for
them. **This is a contradiction between the proposal and an already-ruled
convention**, and one of the two has to move. The canonical exit is load-bearing
(it is how domain data crosses an edge at all), so the proposal is what moves.

---

## Break 3 — The enum position leaves state with no legal type

Two positions collide:

1. `skills/tesser-build/value-objects.md:29-30` — an enum / type code "is a
   primitive with a name, **not** a value object." Listed as a near-miss.
2. The proposal — enums are primitive, so a method may not return one.

Together: a domain object holding a state or type code has **no legal return
type for it**. The flagship case is in the conformant app:

- `examples/python-app/campaign/domain/short_link.py:34` — `active -> bool`.
  It cannot become `-> ShortLinkStatus` (an enum, banned by 2 and not a VO by 1),
  and it cannot stay `bool`.

This is the one place the proposal exposes a genuine hole in the existing
rules rather than colliding with them.

### Ruled (2026-08-08): enums stay primitive. They are not value objects.

`value-objects.md:29-30` stands. So the hole is closed from the other side —
and `statearms/` measures what that costs, using the repo's own silent-site
metric (`docs/design-three-contender-changeability.md`). Three arms, same
domain, then a third state (`suspended`) arrives:

```
PYTHONPATH=tesser-py:examples/spike-totalreturn/statearms \
  python3 examples/spike-totalreturn/statearms/test_arms.py     # 9 pass, 0 fail
```

| arm | silent sites when `suspended` arrives | probe verdict |
|---|---|---|
| `arm_bool.py` — `active -> bool` (today's shape) | **2** + an invalid state becomes representable (`active=True, suspended=True`) | 3 public breaks |
| `arm_enum.py` — `status -> LinkStatus(Enum)` | **1**, plus 1 *accidentally* correct | 2 public breaks, incl. `[ENUM]` |
| `arm_vo.py` — the branch folds into the type | **0**; consumers never touched | **0 public breaks** |

The load-bearing result is not that arm 3 wins on count. It is **what arm 3
had to become**. The rule does *not* turn `active -> bool` into
`active -> StatusVO`; that is arm 2 in a value object's coat, and the probe
still flags it. What the rule forces is that **the predicate stops existing**:

- `arm_bool.py:38` / `arm_enum.py:38` — `should_redirect(link) -> bool`, a
  question the caller asks and then answers itself.
- `arm_vo.py:114` — `resolve(link) -> Resolution`. There is no predicate to get
  wrong, because nothing is handed out to branch on
  (`statearms/test_arms.py:127` asserts the Resolution exposes no selector).

Two consequences worth naming before this goes near the skill:

1. **The domain absorbs the public message** (`arm_vo.py:68-72`). That is a
   real transfer of responsibility from the edge into the domain, and it is not
   obviously right — `value-objects.md:46` currently says "display formatting is
   a presentation concern, never the value's." Arm 3 as written is in tension
   with that line. Resolving it is a second ruling, not a detail.
2. **The exhaustiveness win is the registry, not the rule.** `arm_vo.py:68-72`
   makes every state's behavior mandatory at one site, so an undecided state
   fails construction (`test_arms.py:113`). An enum arm with the same registry
   would get the same win. The value object is what makes the registry the
   *only* door; it is not itself the source of the exhaustiveness.

---

## Break 4 — The real scope: 23 public methods, of two kinds

**PRIMITIVE queries (14) — genuine representation leaks.** These are already
banned in prose by `skills/tesser-build/value-objects.md:38-41` ("An accessor
that hands the wrapped primitive straight back … is banned outright"), and are
not caught mechanically:

- `examples/spike-shells/spike/domain.py:17` — `Note.text -> str`
- `examples/spike-llmport/scheduling/domain.py:88,91,94,97` — `Booking.step_label`,
  `name_label`, `slot_label`, `offered_labels`, all `-> str`
- `examples/spike-shells/sigcheck/domain.py:215,218,224-236` — `Module.name -> str`,
  `is_package -> bool`, and six tuple-of-primitive accessors

**Go equivalents the current checker misses.** `passes/primitiveaccessor/primitiveaccessor.go:69-71`
only matches a `To`-prefixed name, so it catches `ToCents()` and lets the same
leak through under a plain noun:

- `examples/lending/money.go:24` — `func (m Money) Cents() int64`
- `examples/catalog/labels.go:17` — `Labels.Get(key string) (string, bool)`
- `examples/catalog/labels.go:22` — `Labels.Len() int`
- `rationale/valueobject/navigation.go:51` — `Altitude.Meters() float64`
- `rationale/valueobject/tags.go:18` — `Tags.Get(key string) string`

**COMMAND mutators (7) — a different question entirely.** `-> None` transitions
have no value to promote; the question is command-style vs. returning new state,
which `entities.md:71-79` already settles as a per-domain fact-vs-lifecycle
decision:

- `examples/python-app/campaign/domain/campaign.py:45,48` — `Campaign.add_short_link`,
  `deactivate_short_link`
- `examples/python-app/campaign/domain/short_link.py:37` — `ShortLink.deactivate`

**UNKNOWN (2) — a leak the proposal does not even name.** Leaking a *foreign
library type* is at least as bad as leaking a primitive:

- `examples/spike-shells/sigcheck/domain.py:221,239` — `Module.body -> tuple[ast.stmt, ...]`,
  `class_defs -> tuple[ast.ClassDef, ...]`

---

## What survives — the satisfiable form

Not "no primitives." A **totality** rule in the shape of TB032 (every function
classifies or declares itself):

> Every public method on a domain object returns a domain object, **or** is one
> of a closed, declared set of licensed exits.

The licensed set, derived from what the probe measured as unavoidable:

| exit | what it covers | already ruled by |
|---|---|---|
| `protocol` | `__eq__`/`__hash__`/`__str__`/`__init__`; Go `Equal`/`String` | valueobject.py:18,23 |
| `canonical` | the one canonical exit per leaf | serialization.md rule 3 |
| `command` | a transition returning `None`/`error` | entities.md:71-79 |

That reclassifies 38 unsatisfiable + 15 private sites as *declared*, and leaves
the 23 public breaks as the actual work — of which the 14 primitive queries are
a real bug class the checkers do not catch today.

## The entity/aggregate half — what's actually missing

The probe's other finding. `ValueObject` carries a real enforced contract
(`tesser-py/tesser/domain/valueobject.py:1-34`: immutability, equality, no
`__slots__`, no override). Its siblings carry nothing:

- `tesser-py/tesser/domain/entity.py:1-2` — `class Entity: pass`
- `tesser-py/tesser/domain/aggregate.py:1-5` — `class AggregateRoot(Entity): pass`

Every entity and aggregate rule in `entities.md` and `aggregates.md` — identity
immutable, equality by ID only, defensive copies, native equality blocked — is
prose with **zero runtime or static enforcement**. That is a larger and much
cheaper win than the total-return rule, and it is the same move already made
for value objects.

## Open questions for a human (the probe cannot settle these)

1. **Break 3's ruling** — enums as a domain kind, or a closed-set VO, or `bool`
   licensed for predicates? Three coherent answers; the corpus does not prefer one.
2. **Scope of "domain object"** — `Module`/`Codebase` in `sigcheck/domain.py`
   account for 8 of the 14 primitive queries. They are `ts.` types wrapping
   `ast`. If tooling-domain types are out of scope, the real leak count is 6.
