# Kernels — the direct-import tier

Only bounded contexts have domains, and a context's domain is never exported.
But a domain always couples directly to *something*: there is code so core
that no interface exists to inject — you import the implementation and that
is the design, not a violation of it. This doc names that tier, gives it two
homes in the tree, and extends the import rules so the analyzer can tell a
legal direct import from a leak.

Maintainer rulings this materializes (2026-08-15, this session's design
thread): an app has no domain of its own — only its bounded contexts do;
a context's domain can never be exported as a shared kernel; kernels come in
exactly two scopes (shared across one app's contexts, or exported by a
package for other apps); a tree has at most one exported kernel.

## The problem this solves

Three holes of one shape — the direct-import tier existed but had no name,
so each member was a special case:

1. **Two contexts needing the same value object must duplicate it.** The
   import matrix (TB060–TB066) says a context reaches another only through
   its client, from gateways and wiring. Correct for behavior; wrong for a
   `Money` that `campaign` and `reports` must *agree on*. Today the only
   legal answer is a copy in each domain — the exact drift the conventions
   exist to prevent.
2. **tesser-py is unclassifiable.** Its manifest row says `app`, but the app
   grammar defines every obligation as an import *of tesser* ("a role module
   imports its tesser package exactly once, as ts") — applied to the tree
   that ships `tesser`, every row says "import yourself." So the tree that
   defines the conventions is the one tree the conventions cannot check,
   and its verify arm carries no tessercheck step.
3. **The tier's membership is hardcoded.** `CORE_STDLIB` (the pure stdlib a
   domain may import) and `tesser.*` (the one package legal everywhere) are
   the only direct-import channels, both baked into the analyzer. There is
   no way for a repo to add a member — which is policy, and policy never
   lives in the analyzer's code.

## The model

```
context pure roles  →  kernels  →  pure stdlib
(domain, client,       (a DAG among
 application)           themselves)
```

Arrows point right and are transitive: a domain may import any kernel it is
entitled to and the pure stdlib, directly, no port. Nothing imports leftward
— a kernel never knows a context exists.

**A kernel is domain-convention content without a context around it.** Its
classes are value objects and specs built on the `ts.*` shells; the identity
taxonomy, `MustNew`, representation hiding, and the serialization norm apply
to it unchanged. What a kernel does not have: a client (consumption is the
import itself), an application service (nothing to coordinate), adapters or
IO of any kind (whatever a domain imports directly inherits the domain's
purity bar, transitively — this single rule generates the whole tier).

Two scopes, two different promises:

- **App-scoped kernel** — shared across *this app's* bounded contexts,
  invisible outside the package. The DDD shared-kernel sense: the thing the
  contexts agree on.
- **Exported kernel** — shipped as part of the package's public API,
  importable by other apps' pure roles and by other kernels. `tesser` itself
  is one: tesser-py is not special outside the analyzer — it is just an app
  whose exported kernel other packages import. **At most one per tree**: the
  exported kernel is the package's import name; a package has one name.

## Where they live

Both at tree top level, siblings of the contexts and the app shell — placed
by different mechanisms because their names answer to different audiences:

- **`kernel/` — a fixed name, discovered structurally.** The app-scoped
  kernel's name is a repo-internal choice with no outside consumer, so the
  strongest form of "every directory says what it is" applies: fix the word,
  like `srv/` and `protocol/`. One per app; subpackages organize growth.
- **The exported kernel sits under its public import name, declared.** Its
  directory name IS the importable namespace (`tesser/` for tesser-py) — the
  product's name, not a structural word — so it cannot be fixed and cannot
  be discovered (a kernel containing a `domain/` subdir would misclassify as
  a context). The `.tesser-root` declares it, and the declaration is
  cross-checked against disk in both directions.

```
python-app/                          tesser-py/
  .tesser-root   app                   .tesser-root   app
  kernel/                                             export tesser
    money.py                           tesser/
  campaign/  reports/  linkpolicy/       domain/ application/ adapters/
  srv/  bootstrap/  protocol/            context/ srv/ testing/
  tests/  conftest.py                    do_not_use_declared.py  py.typed
                                       tests/
```

Degenerate shapes are legal in both directions: `kernel/` with no contexts
(an app that is only a shared kernel), contexts with no `kernel/` (today's
status quo), and an exported kernel with no contexts (tesser-py today). An
app may later grow `srv/` hosts around any of them — kernel-ness adds one
legal edge and subtracts no app capability.

## The declarations

`.tesser-root` grammar grows from two line forms to five. First line `app`,
then any of:

```
skip <dir>          # unchanged
export <dir>        # this tree's exported kernel (at most one line)
import <package>    # an external kernel this tree's pure roles may import
stdlib <module>     # a stdlib module added to the domain's pure stdlib
```

TB044 findings, all reported before any module finding (the analyzer says
what the tree is before saying anything about its contents):

- a second `export` line — **a tree has one exported kernel**
- `export` naming a directory that does not exist, is not a package, or is
  also a context / `kernel` / a shell package name
- a top-level package that is neither a context, a shell package, `kernel/`,
  nor the declared export — homeless, as any stray is today (TB040)
- an unrecognized directive — unchanged: unrecognized is a finding, never
  silently permitted

`import` is the consumer side and deliberately separate: producing and
consuming are different promises. An external kernel arrives as an installed
dependency (there is no directory to discover), so the consuming tree names
the packages its pure roles may import. `tesser` stays hardcoded-legal
everywhere and needs no line.

An `import` declaration is a purity waiver, so it is validated like one
(all three are TB044 findings, reported before any module finding):

- it never names this tree — not `kernel`, not the app shell, not any
  walked top-level package. A declaration legalizes an *installed external
  kernel*; anything the walk governs is governed by the walk.
- it never names the stdlib — the pure stdlib is already legal, and the
  rest of it is never a kernel (`import subprocess` cannot be declared
  away).
- it must be *used* — a declaration that legalizes no edge is itself a
  finding, mirroring TB090's rule that a debt marker suppressing nothing
  rots the ledger.

`stdlib` is the stdlib-side counterpart (maintainer ruling 2026-08-24: the
pure allowlist is a recommended default, not a fixed constant — a consumer
whose domain needs `collections` or `itertools` widens it in its own
declaration, never in the analyzer). A `stdlib <module>` line widens
`CORE_STDLIB["domain"]` — the set the domain role and every kernel module
share — with that module and its submodules (`stdlib urllib` admits
`urllib.parse` and `urllib.request` alike; `stdlib urllib.parse` admits
only the parser). It does not widen client, application, or ports: those
are DTO shapes with nothing to compute. It is validated like `import` (all
three are TB044 findings, reported before any module finding):

- it names the stdlib — `stdlib requests` is a finding; an external package
  is declared with `import`.
- it never repeats the default — `stdlib typing` legalizes nothing.
- it must be *used*, for the same reason an `import` line must.

Like `import`, a `stdlib` line is a purity waiver, and the analyzer checks
its shape, not its purity: `stdlib os` is accepted. Enumerating the IO
modules is the trap the allowlist inverted away from, and the line sits in
a one-line diff of a file every reviewer reads — the tree decides what its
domain may reach for, in review, not the analyzer.

The shipped default is evidence-driven and stays so: `collections.abc`,
`urllib.parse`, and `copy` were admitted 2026-08-24 (the latter two burned
the last `# tesser:debt TB062` markers in `examples/python-app`).

Kernel-target imports are trusted per **walked module**, not per top-level
name: an import of `kernel.vendored.x` where `vendored/` is skipped from
the walk is a finding, because trust in code the analyzer never saw is not
trust. And `kernel` is a **reserved top-level name**: a consumer repo with
a pre-existing bounded context named `kernel` will see its modules
reinterpreted under the kernel rules — loudly, by design — and must rename.

## Import matrix changes

- **TB062 (pure roles)** — domain, client, and application may additionally
  import: this tree's `kernel/`, and any `import`-declared external kernel.
  Everything else about the row is unchanged.
- **New kernel row** — a kernel module imports only: its own kernel package,
  `tesser.domain` (exactly once, as `ts` — kernel content is domain
  content), the domain pure stdlib (`CORE_STDLIB["domain"]`), and
  `import`-declared external kernels. Never a context, never the app shell,
  never IO.
- **Adapters/component/srv** — unchanged. They may already reach more than the
  pure roles can; kernels add nothing they need.
- **Tests** — kernel companion tests sit beside kernel modules and follow
  the domain-companion tier: they may import the kernel and `tesser.testing`.

## The one special case, and where it lives

Kernel *content* rules are keyed on the `ts.*` shells — and the shells
cannot subclass themselves. So the analyzer routes exactly one exported
kernel differently: when the declared export is the package `tesser`, its
modules are governed by **shells rows** instead of domain-content rows:

- **The tree is the distribution, and nothing else**: a tree declaring
  `export tesser` holds exactly `tesser/` and `tests/` at its top level.
  Without this, any app could park a `tesser/` package beside its
  contexts, declare the export, and gain a content-rule-free region its
  governed domain code calls as `ts.*` — the shape gate makes the
  declaration an identity claim only the distribution can make.
- **Totality**: the distribution's members — modules and subpackages alike
  — are exactly the consumer namespaces (`domain`, `application`,
  `adapters`, `context`, `srv`, `testing`, `lifecycle`, `errors`,
  `serialization`) plus `do_not_use_declared.py`; anything else is a finding.
- **Purity**: a shell module imports only its own distribution and the
  shell stdlib (`__future__`, `typing`, `collections`, `enum`, `datetime`,
  `decimal`, `dataclasses`) — the measured external surface of the
  shipped distribution, and a meta-test
  (`tessercheck/tests/test_tesser_allowlists.py`) fails when either
  allowlist grants a name the distribution does not earn.
- **Tests invert exactly two consumer rules, and keep the rest**: this
  tree's tests may import any `tesser.*` (the shells are their subject —
  the mirror image of consumer tests, which may touch only
  `tesser.testing`), and their module-level classes are free (probe
  subclasses of the shells are the tests' method, not test doubles).
  Function totality still applies — every module-level function is a test
  or a declared helper — as do the comments norm, the mock-library ban,
  and placement. The mutmut ecosystem harness is subprocess
  infrastructure that cannot meet the helper shape, so it is skipped by
  declaration (`skip ecosystem`), visibly, with its rationale in that
  directory's README.

This is the entire remaining specialness of tesser-py, and it lives in the
analyzer — the same file that already names `tesser` in every import row —
never in the manifest, the layout, or the docs' ontology.

## Enforcement summary

| Claim | Where enforced |
|---|---|
| one exported kernel per tree | TB044 (second `export` line) |
| export exists on disk, is a package, collides with nothing | TB044 |
| kernel purity (no IO, pure stdlib only) | kernel import row |
| kernel content is conventional domain content | existing TB01x/TB03x, applied to kernel modules |
| pure roles import only entitled kernels | TB062 extension |
| nothing imports leftward into a kernel's consumers | existing rows (unchanged) |
| shells meet the shells bar | shells rows (the `export tesser` routing) |
| declarations match disk, arms, and CI | layout app cross-checks |

## Rollout

1. **This grammar** — `.tesser-root` line forms, classifier `kernel/` role,
   TB062 extension, single-export rule, homeless-rule update; RULES.md
   regen, roadmap row, coverage matrix rows for each new rule.
2. **Shells rows** — the `tesser` routing; tesser-py gains `.tesser-root`
   (`app` + `export tesser` + skips for the mutmut fixtures) and
   `tessercheck_tree` in its verify arm. The gate this design exists to
   make real.
3. **The worked example** — landed with step 1, because the
   category-earning meta-test demands a real tree exercise every legal
   classification. The honest lift turned out to be `Slug`, not `Money`:
   `Slug` was duplicated byte-for-byte in `campaign` and `reports` (two
   real consumers — the second consumer earns the move), while `Money` has
   one consumer and stays in `campaign/domain`, and the three `TargetURL`s
   validate differently — different rules are different types, so none of
   them lift. The Decimal/precision behavioral ground stays tracked
   against the ValueObject-shape TODO.

Each step lands green on its own; no step depends on a later one.
