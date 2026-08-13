# spike-ports — where a context's ports live, and what shape their answers take

A spike, not a shipped tree. Six sibling trees over one neutral domain
(`catalog`), identical except at **one seam**: how a repository port expresses a
two-outcome answer (item found / item missing). `final/` is the selected
combination.

The question this spike answers: **adapters were allowed to import the whole
`application` role, which means a gateway imports the service implementation it
is supposed to be decoupled from.** Ports move to `application/ports/`, adapters
reach only that, and the port's answer has to survive without a union.

## The seam, six ways

| Tree | Encoding of "found / missing" |
|---|---|
| `union/` | `FoundItem \| MissingItem` — the control; what the codebase does today |
| `cardinality/` | `FindItemResponse(items: tuple[ItemView, ...])`, 0 or 1 |
| `flag/` | `FindItemResponse(found: bool, id: str, name: str)`, blanked payload |
| `outcome/` | `FindItemResponse(outcome: str, items: ...)`, `"found"` / `"missing"` |
| `enum/` | `FindItemResponse(outcome: ItemLookup, items: ...)` + `match`/`assert_never` |
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

## Experiment 2 — what the existing rules say about each encoding

Running the ports checker (`tessercheck`) over each tree:

| Tree | Findings | What fired |
|---|---|---|
| `cardinality/` | 0 | — |
| `flag/` | 0 | — |
| `enum/` | 0 | — |
| `outcome/` | 2 | TB051 — module constants for the outcome strings |
| `union/` | 2 | TB081 — `find` does not return a `ts.Response` |
| `split/` | 20 | TB020 comments ×17, TB052 exception class, TB082 service branch |

Two of these are decisive and were not designed for:

- **`union/` needs no new rule to be banned.** "A port method returns a
  `ts.Response`" already rejects a union, at the port *and* at the fake.
- **`split/` is self-refuting under the comments norm.** The
  exists-then-get encoding cannot be written without comments explaining the
  precondition ("only legal to call when `exists()` said True") and the
  absent-item behaviour — and TB020 forbids comments. An encoding whose
  contract cannot be expressed in code is the wrong encoding. It also opens a
  time-of-check-to-time-of-use gap and smuggles the missing case out of the
  type system into an exception, which is a second return channel — precisely
  what "one Request in, one Response out" exists to prevent.

## Experiment 3 — the outcome string has no compiler behind it

`outcome/` was probed twice:

1. Removing the reader's fallthrough produced `Missing return statement` — which
   *looks* like exhaustiveness checking but is ordinary control-flow analysis.
   mypy has no idea `outcome` is drawn from a two-element set.
2. Changing the adapter to return `outcome="fnud"` (a typo) type-checked
   **clean**. The bug surfaced only at runtime.

A bare string closes over nothing. With the ports statement rule below
(imports and classes only, so no module constants), this encoding is
structurally unavailable anyway.

## The selected shape

`final/` demonstrates it, with two ports so the no-sharing rule is visible:

- **A collection answer carries a tuple** — `ListItemsResponse(items=...)`. No
  outcome enum; cardinality *is* the answer.
- **A multi-outcome answer carries an enum plus payload** —
  `FindItemResponse(outcome: ItemLookup, items=...)`, read with `match` +
  `typing.assert_never`. Growing the outcome set is a compile error at every
  reader.
- **Mapping stays in application.** `application/mapping.py` holds the
  domain ↔ port-DTO transforms; ports hold no logic.
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
| TB052 | a ports class declares its block |
| TB052 | only a port and the requests and responses it speaks live in a ports module |
| TB052 | a ports module declares exactly one port, so no two ports can share a request or a response |
| TB060 | adapters reach `application/ports`, never the rest of application |
| TB067 | a ports module is a leaf and imports nothing from its tree, its own siblings included |
| TB081 | a port method takes exactly one `ts.Request` |
| TB081 | a port method returns a `ts.Response` |

Two of these carry their weight indirectly:

- **The leaf rule enforces no-sharing for free.** A ports module cannot import
  a sibling, so a request class in `ports/a.py` is unreachable from
  `ports/b.py`. Combined with one-port-per-module, two ports sharing a DTO is
  not something a rule forbids — it is something the layout makes
  unrepresentable.
- **"Imports and classes only"** rules out the module-constant crutch that the
  bare-string encoding needs, so the weakest encoding cannot be written.

`enum` classes are permitted in a ports module and as a port-DTO field — the
one deliberate widening, bought by Experiment 1.

## Retired

`ts.Parts` is gone. Port DTOs are `ts.Request` / `ts.Response` from
`tesser.application`, matching the client role's vocabulary; a nested view DTO
takes the `ts.Response` base, which is already the client convention
(`LinkView(ts.Response)`).
