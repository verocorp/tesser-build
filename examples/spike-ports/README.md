# spike-ports — where a context's ports live, and what shape their answers take

A spike, not a shipped tree. Seven sibling trees over one neutral domain
(`catalog`), identical except at **one seam**: how a repository port expresses a
two-outcome answer (item found / item missing). `final/` is the selected
combination.

The question this spike answers: **adapters were allowed to import the whole
`application` role, which means a gateway imports the service implementation it
is supposed to be decoupled from.** Ports move to `application/ports/`, adapters
reach only that, and the port's answer has to survive without a union.

## The seam, seven ways

| Tree | Encoding of "found / missing" |
|---|---|
| `union/` | `FoundItem \| MissingItem` — the control; what the codebase did before |
| `cardinality/` | `FindItemResponse(items: tuple[ItemView, ...])`, 0 or 1 |
| `flag/` | `FindItemResponse(found: bool, id: str, name: str)`, blanked payload |
| `outcome/` | `FindItemResponse(outcome: str, items: ...)`, `"found"` / `"missing"` |
| `enum/` | `FindItemResponse(outcome: ItemLookup, items: ...)` + `match`/`assert_never` |
| `split/` | two port methods — `exists()` then `get()` |
| `final/` | the selected shape — enum outcomes, tuple collections, two ports |

Every tree is `mypy --strict` clean and green under `pytest`. The differences
below are measured, not argued.

## Experiment 1 — the changeability metric: silent sites on a third outcome

The repo's own metric (`docs/design-three-contender-changeability.md`) is the
**silent-site count**: after a change, how many call sites keep compiling and
keep passing tests while being wrong. A third outcome arrives — an item can now
be *archived* — and the reader (`application/mapping.py`) is left untouched.

| Tree | Writers flagged | Reader flagged | Silent sites | Result |
|---|---|---|---|---|
| `union/` | — | **yes** — `assert_never` argument stops being `Never` | 0 | loud |
| `enum/` | — | **yes** — `assert_never` argument stops being `Never` | 0 | loud |
| `cardinality/` | adapter + fake (`call-arg`) | no | **1** | silent |
| `flag/` | adapter + fake (`call-arg`) | no | **1** | silent |

The exact mypy error, from `enum/`:

```
catalog/application/mapping.py:37: error: Argument 1 to "assert_never" has
incompatible type "Literal[ItemLookup.ARCHIVED]"; expected "Never"  [arg-type]
```

And the silent case, from `cardinality/` — after satisfying the two writers
mypy named, with the reader still mapping every item through as live:

```
Success: no issues found in 17 source files
3 passed
```

An archived item is served to the client as a live one; nothing objects.

**`enum` is the only union-free encoding that scores zero.** It reproduces
exactly the protection the union control gives, without a union.

One asymmetry in the enum's favour over the control: the union's protection
only fires if the *reader's own annotation* is widened to track the new variant
(otherwise the error lands upstream at the call site, not at the missed branch).
The enum's response type never changes, so the error lands precisely on the
unhandled branch.

## Experiment 2 — what the rules say about each encoding

Running the shipped ports checker over each tree:

| Tree | Findings | What fired |
|---|---|---|
| `cardinality/` | 0 | — |
| `enum/` | 0 | — |
| `final/` | 0 | — |
| `union/` | 1 | TB081 — `find` does not return a `ts.Response` |
| `flag/` | 1 | TB080 — `found` is a bare bool |
| `outcome/` | 2 | TB051 — module constants for the outcome strings |
| `split/` | 48 | TB020 comments ×45, TB080, TB052, TB082 |

Three of these are worth stating plainly, because two were not designed for:

- **`union/` needs no bespoke rule.** "A port method returns a `ts.Response`"
  already rejects a union, at the port *and* at the fake that implements it.
- **`split/` is self-refuting under the comments norm.** The exists-then-get
  encoding cannot be written without comments explaining the precondition ("only
  legal to call when `exists()` said True") and the absent-item behaviour — and
  TB020 forbids comments. An encoding whose contract cannot be expressed in code
  is the wrong encoding. It also opens a time-of-check-to-time-of-use gap.
- **`flag/` is rejected by a rule added *because* of Experiment 1** (below).

## Experiment 3 — the outcome string has no compiler behind it

`outcome/` was probed twice:

1. Removing the reader's fallthrough produced `Missing return statement` — which
   *looks* like exhaustiveness checking but is ordinary control-flow analysis.
   mypy has no idea `outcome` is drawn from a two-element set.
2. Changing the adapter to return `outcome="fnud"` (a typo) type-checked
   **clean**. The bug surfaced only at runtime.

A bare string closes over nothing.

## Making Experiment 1 binding

The first draft of this spike *selected* the enum and then shipped a rule set
that permitted both encodings Experiment 1 had just measured as silent. A probe
response carrying `allowed: bool`, `outcome: str`, and `hit: NameView | None`
passed the checker clean. Measuring an encoding and then not enforcing the
result is advice wearing a checker's clothes, so four field rules were added,
each of which turns a measured result into a guarantee:

- **never a bare `bool`** — kills the `flag/` encoding. Parallel to TB016, which
  already bans a bool inside a value object, and to `domain-return.md` rule 5:
  a public predicate answer is a concept, not a boolean.
- **never a union, optional included** — kills `item: ItemView | None`, an
  eighth encoding this spike never measured and the one real code reaches for
  first. It is `cardinality/`'s silent case with a different spelling.
- **never subclassed** — a response hierarchy is a union in all but name, and
  *strictly worse* than the union we ban: Python has no sealed classes, so mypy
  cannot exhaustiveness-check it and `assert_never` is unavailable.
- **`enum.Enum` only, never `StrEnum`/`IntEnum`/`Flag`** — a str-backed member
  compares equal to a raw literal, which reopens the exact typo channel
  Experiment 3 closes.

### What the rules still do not decide

Two encodings remain writable, and honesty is better than an overclaim:

- **A bare `str` outcome field.** `outcome: str` is not distinguishable from any
  other string field. `outcome/` trips TB051 only because its author hoisted the
  values into module constants; inlined, it is clean. Experiment 3 is the
  argument against it, not a rule.
- **0-or-1 cardinality used as an outcome.** A tuple response is the correct
  shape for a genuine collection, so it cannot be banned; using one as a
  found/missing signal is a convention call.

Neither is mechanically decidable without banning legitimate code.

## The selected shape

`final/` demonstrates it, with two ports so the no-sharing rule is visible:

- **A collection answer carries a tuple** — `ListItemsResponse(items=...)`. No
  outcome enum; cardinality *is* the answer.
- **A multi-outcome answer carries an enum plus payload** —
  `FindItemResponse(outcome: ItemLookup, items=...)`, read with `match` +
  `typing.assert_never`. Growing the outcome set is a compile error at every
  reader.
- **Mapping stays in application.** `application/mapping.py` holds the
  domain ↔ port-DTO transforms; ports hold no logic and no bodies.
- **The empty request and the empty response are the established shape**, not
  new ceremony: `client.py` already ships `ListLinksRequest.__init__(self) ->
  None: return None`.

### What an adapter imports now

```python
import tesser.adapters as ts
import catalog.application.ports.item_repository as item_repository
```

That is the whole import block. Across `final/`, every adapter import is a
protocol — its context's ports, the app shell's `protocol`, or a client. **No
adapter imports an implementation module anywhere in the tree.**

## The rule set (all enforced; see `tessercheck-py/RULES.md`)

| Code | Rule |
|---|---|
| TB041 | ports is a package, never a module |
| TB042 | a ports `__init__` is empty |
| TB050 | a ports module imports only `tesser.application`, exactly once, as `ts` |
| TB051 | a ports module holds only imports and classes |
| TB051 | a port method declares a shape and never a body |
| TB052 | a ports class declares its block |
| TB052 | only a port and the requests and responses it speaks live in a ports module |
| TB052 | a ports module declares exactly one port, so no two ports can share a request or a response |
| TB052 | a port DTO is never subclassed |
| TB052 | a ports enum is an `enum.Enum` |
| TB060 | adapters reach `application/ports`, never the rest of application |
| TB067 | a ports module is a leaf and imports nothing from its tree, its own siblings included |
| TB068 | an import is a statement the walk can read, never a call |
| TB080 | a port DTO field is never a union, optional included |
| TB080 | a port DTO field is never a bare bool |
| TB081 | a port method takes exactly one `ts.Request` |
| TB081 | a port method returns a `ts.Response` |

Three of these carry their weight indirectly:

- **The leaf rule enforces no-sharing for free.** A ports module cannot import
  a sibling, so a request class in `ports/a.py` is unreachable from
  `ports/b.py`. Combined with one-port-per-module, two ports sharing a DTO is
  not something a rule forbids — it is something the layout makes
  unrepresentable.
- **"Imports and classes only"** rules out the module-constant crutch, and
  **"never a body"** keeps executable logic out of the one application module
  adapters are allowed to import.
- **TB068** exists because an import rule that only reads `import` statements is
  a rule about spelling. `importlib.import_module("...application.service")` in
  a gateway is an import the matrix cannot see, so the call form is a finding.

`enum` classes are permitted in a ports module and as a port-DTO field — the one
deliberate widening, bought by Experiment 1. The enum base is resolved through
the module's import bindings, not its spelling, so `import typing as enum` does
not smuggle an unclassified logic class into the leaf.

## Retired

`ts.Parts` is gone. Port DTOs are `ts.Request` / `ts.Response` from
`tesser.application`, matching the client role's vocabulary; a nested view DTO
takes the `ts.Response` base, which is already the client convention
(`LinkView(ts.Response)`).

## The honest cost, measured on the five migrated trees

Review raised three costs as unmeasured. They are measurable, so here they are.

**Class count roughly triples.** 19 `ts.Parts` classes become 47 request and
response DTOs plus 10 enums, across 11 ports and 531 lines of ports modules.
That is the price of one-Request-in / one-Response-out, and it is real.

**Ten DTOs are empty** — the zero-arg `all()` / `available()` family and the
void `save()` family. `client.py` already ships this exact shape
(`ListLinksRequest.__init__(self) -> None: return None`), so it is an
established form rather than a new one, but a reader meeting it for the first
time on a repository will find it strange. Named, not defended.

**The no-shared-DTO rule costs nothing observable.** This was the loudest
worry, and it did not survive measurement. Of 26 distinct field shapes across
the migrated ports, 9 repeat — but every repeat is either the request/response
direction split *inside one module* (`CampaignRecord` and `SaveCampaignRequest`
carrying the same fields, which is the client role's existing convention), or a
shape repeating *across contexts* (`LinkRecord` in `campaign` and in `reports`),
where sharing was already forbidden by the cross-context rules and always had
been. **No two ports in the same context were forced to duplicate a DTO.** The
tax the rule was expected to levy is not present in any real tree here.

Two costs that are real and are not the rule's fault to fix:

- **A predicate now costs three classes.** `slug_taken(slug) -> bool` becomes a
  request, a response, and an enum. That is right when the answer is an outcome
  and heavy when it is genuinely a yes/no, and there is no decidable line
  between the two.
- **The low-ceremony path is gone.** A one-edge context used to be able to keep
  the walk inline. `port_request` and `port_response` are pinned to the ports
  package, so the smallest context pays the full package + DTO + mapping cost.
  There is no graduation path, by construction.

## Not a CI gate

These trees are a design record, not a governed example tree: `union/`, `flag/`,
`outcome/` and `split/` exist *because* they produce findings, so a zero-findings
gate is the wrong shape for them. `final/` alone is wired into `scripts/verify`.
The migration of the five real example trees is in `MIGRATION.md`.
