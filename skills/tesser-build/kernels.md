# Kernel

<!-- tb-status: full -->

A kernel is domain-convention content without a context around it: value
objects (and their specs) that more than one consumer must *agree on*,
consumed by direct import — no interface to inject, and that is the design.
Only bounded contexts have domains, and a context's domain is never shared;
when two contexts need the same value object, the kernel is the legal home
that isn't a copy.

## Is this what I'm building?

- **Two or more of this app's contexts need the same domain type** (the same
  Money, the same Quantity) → an **app-scoped kernel**: the package
  `kernel/` at the tree root. Invisible outside the app.
- **Other apps/packages must import this domain-level code** → the
  **exported kernel**: a package under its public import name, declared
  `export <dir>` in `.tesser-root`. A tree has at most one — the exported
  kernel is the package's import name, and a package has one name.
  (`tesser` itself is an exported kernel; tesser-py is an app whose export
  it is, governed by the shells rows — namespace totality, the shell
  stdlib, and inverted tests — because the shells cannot subclass
  themselves.)
- **Two aggregate roots in ONE context need the same value object** → a
  **context kernel**: the package `<context>/domain/kernel/`. It is the same
  answer one level down — a value object neither root owns, imported directly
  by both, with neither root's module importing the other.
- **Only one context uses it** → it is that context's domain content. Do not
  lift a type into the kernel speculatively; the second consumer earns the
  move.

## Rules

1. **Kernel content is domain content.** Classes declare their `ts.*` block
   and only domain kinds are legal — value objects, entities, aggregates,
   specs. Every domain convention (single validating constructor,
   representation hiding, serialization norms) applies unchanged.
2. **The purity bar is the domain's, transitively.** A kernel module imports
   only: its own kernel, `tesser.domain` (exactly once, as `ts`), kernels
   declared with `import <package>` lines, and the domain's pure stdlib —
   the shipped default plus any `stdlib <module>` lines the tree's
   `.tesser-root` declares. Never a context, never the app shell, never IO.
3. **Nothing imports leftward, and a kernel enters a context in one place.**
   A kernel never knows a context exists. A root kernel is imported only by a
   context's own `<context>/domain/kernel/` package, whose `__init__`
   re-exports what that context takes (`from kernel import Slug as Slug`); a
   domain module then names exactly one `kernel` (`import
   campaign.domain.kernel as kernel`, TB053). No other role, no adapter, no
   shell or protocol module imports a kernel at all — outside the domain a
   kernel type is named through the domain `__init__` (TB062, TB063).
4. **No client, no service, no adapters.** Consumption *is* the import. If
   the tree also wants runtime behavior (a CLI over the kernel), that is
   ordinary app anatomy grown beside it — contexts, `srv/` — not part of
   the kernel.
5. **A kernel `__init__` only re-exports from its own kernel.**
6. **A context kernel declares as well as re-exports** (maintainer ruling
   2026-09-11). `<context>/domain/kernel/` is the home of the value objects
   two of that context's aggregate roots share, not only a re-export shim over
   a root kernel. It holds value objects, specs and enums — an entity or an
   aggregate root there is a finding, because a root is owned by one module and
   named elsewhere by its id (TB052, TB012) — and it is a package, never a
   `domain/kernel.py` module (TB041). Unlike a root kernel it **is** an
   exporting package: its modules do not import each other (TB060), so one
   module holds one shared concept and two concepts that need each other are
   one module. Each module carries its sibling test (TB074), and the reverse
   of rule 3 holds for it too — only that context's own domain modules import
   it, as `import <context>.domain.kernel as kernel`.

## Shape

```
<app>/
  .tesser-root        app            (+ `export <dir>` for an exported kernel)
  kernel/             ← app-scoped: fixed name, discovered, one per app
    __init__.py       ← the export list
    money.py
    test_money.py     ← companion test: reaches only the kernel + tesser.testing
  <context>/
    domain/
      order.py        ← one aggregate root per domain module
      purchase.py     ← the second root; it does not import order.py
      kernel/         ← the one package that imports the root kernel,
                        and the home of what two roots here share
        __init__.py   ← re-exports what this context takes and declares
        order_id.py   ← a shared value object; no module beside it
        test_order_id.py
  srv/  app/  protocol/  tests/
```

## Decisions you must make

- **App-scoped or exported?** Exported is a superset promise (other packages
  couple to your namespace forever). Default app-scoped; export only when a
  real external consumer exists.
- **Lift or duplicate?** A type lifts from a context's domain into `kernel/`
  when a second context needs the *same agreed* type. If the two contexts
  need *different* rules for a similar-looking value, they are different
  types — keep them in their domains.
- **Which kernel?** Two *contexts* → the root `kernel/`. Two aggregate roots
  in one *context* → that context's `domain/kernel/`. The test is who has to
  agree on the type, and the answer decides the home; a type only one root
  uses stays in that root's module.

## How the machine sees it

`kernel/` is discovered by its fixed name (a reserved top-level name — a
context may not be called `kernel`); an exported kernel is routed by its
`.tesser-root` declaration (a second `export` line, an export naming no
package or a context-shaped one, or a shell/kernel name collision is a
`TB044` finding). An `import <package>` declaration is a validated purity
waiver: it never names this tree or the stdlib, and one that legalizes
nothing is itself a finding. Kernel modules carry the domain content rules
(`TB052` block declarations, the `TB01x` taxonomy), the kernel import row
(`TB050`/`TB062` — trusted per walked module, and the exported kernel never
imports the app-scoped one), statement totality (`TB051`), and the kernel
test tier (`TB070`). The worked example is `examples/python-app/kernel/`
(`Slug`, shared by the campaign and reports contexts). A **context** kernel is
routed by its own placement — `<context>/domain/kernel/` is not a role package
— and carries the context-kernel rows (`TB041` package-never-module, `TB042`
export list, `TB052` shared leaf kinds only, `TB060`/`TB062` the import row) on
top of the domain content rules. The worked example is
`examples/durable-execution/ordering/domain/kernel/` (`OrderId`, `Quantity`,
`PriceSpec` and `Price`, shared by the `Order` and `Purchase` roots).
