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
  it is.)
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
   declared with `import <package>` lines, and the domain's pure stdlib.
   Never a context, never the app shell, never IO.
3. **Nothing imports leftward.** A kernel never knows a context exists.
   Contexts' pure roles (domain, client, application) may import the app's
   kernels directly — member form is fine, like the stdlib — and adapters,
   wiring, and tests may too.
4. **No client, no service, no adapters.** Consumption *is* the import. If
   the tree also wants runtime behavior (a CLI over the kernel), that is
   ordinary app anatomy grown beside it — contexts, `srv/` — not part of
   the kernel.
5. **A kernel `__init__` only re-exports from its own kernel.**

## Shape

```
<app>/
  .tesser-root        app            (+ `export <dir>` for an exported kernel)
  kernel/             ← app-scoped: fixed name, discovered, one per app
    money.py
    test_money.py     ← companion test: reaches only the kernel + tesser.testing
  <context>/ ...      ← may import kernel.money directly from its pure roles
  srv/  bootstrap/  protocol/  tests/
```

## Decisions you must make

- **App-scoped or exported?** Exported is a superset promise (other packages
  couple to your namespace forever). Default app-scoped; export only when a
  real external consumer exists.
- **Lift or duplicate?** A type lifts from a context's domain into `kernel/`
  when a second context needs the *same agreed* type. If the two contexts
  need *different* rules for a similar-looking value, they are different
  types — keep them in their domains.

## How the machine sees it

`kernel/` is discovered by its fixed name; an exported kernel is routed by
its `.tesser-root` declaration (a second `export` line, an export naming no
package, or a shell/kernel name collision is a `TB044` finding). Kernel
modules carry the domain content rules (`TB052` block declarations, the
`TB01x` taxonomy), the kernel import row (`TB050`/`TB062`), statement
totality (`TB051`), and the kernel test tier (`TB070`). The worked example
is `examples/python-app/kernel/`.
