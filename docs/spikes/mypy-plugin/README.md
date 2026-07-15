# Spike — a mypy plugin for the ddd-vet-py checks (2026-07-15)

Throwaway spike, preserved for the record. **Nothing here is wired into the
build.** It answers one question: *what would a mypy plugin buy the Python DDD
analyzer that the shipped zero-dep AST tool (`ddd-vet-py`) and plain
`mypy --strict` don't already give us?* — measured by building a real plugin
and running three approaches over one shared case set.

Grounding for the mypy-internals claims below (API stability, hook semantics,
first-match-wins) is pinned in the tesser run against `github.com/python/mypy`
at `82e8498c1949`; the load-bearing `file:line` anchors are quoted inline in
`ddd_full_plugin.py`.

## What's here

- `ddd_full_plugin.py` — all four ddd-vet-py checks (DDD001–004) plus the
  type-aware primitive-obsession bonus, as **one** mypy plugin.
- `mypy.ini` / `mypy_plain.ini` — plugin-on and plugin-off (`--strict` only)
  configs.
- `fixtures/f_ddd00*.py` — the per-check good/bad fixtures, incl. the two
  non-literal DDD002 cases (`_alias_bad`, `_custom_bad`) the AST tool cannot see.
- `fixtures/testdata_copy/` — byte-for-byte copies of `ddd-vet-py/testdata/`.
- `fixtures/matrix/` — the type-aware cases: primitive disguised by alias /
  cross-module import / NewType, and the Mars-Orbiter unit-swap.

## Reproduce

```sh
python3 -m venv venv && ./venv/bin/pip install mypy
# plugin on a fixture (exit 1 = finding, 0 = clean):
./venv/bin/mypy --config-file mypy.ini fixtures/f_ddd002_alias_bad.py
# plain mypy, no plugin, for the same file:
./venv/bin/mypy --config-file mypy_plain.ini fixtures/f_ddd002_alias_bad.py
# the type-aware matrix cases:
cd fixtures/matrix && ../../venv/bin/mypy --config-file mypy.ini m_marsorbiter_bad.py
```

## Per-check difficulty (all four built into one plugin, all ran)

| Check | Hook | Grade | Note |
|---|---|---|---|
| DDD001 frozen | `get_class_decorator_hook_2("dataclasses.dataclass")` | **clean** | reads mypy's own `frozen` metadata off the dataclass transform |
| DDD002 hash-hazard | same decorator hook, walks resolved field types | **clean — the one check types genuinely upgrade** | catches non-literal cases (alias→dict, custom unhashable class) |
| DDD003 setattr-bypass | `get_method_hook("builtins.object.__setattr__")` | **awkward, worked** | leans on `ctx.api.scope`, an *undeclared* internal — the most fragile of the four |
| DDD004 str-equality | `get_method_hook("builtins.str.__eq__")` | **clean, zero benefit** | 100% syntactic even inside the hook — no reason to leave AST for it |

**The chain-preemption trap** (proven twice): user decorator hooks run *before*
mypy's own dataclass transform, first-match-wins. A hook that doesn't re-invoke
`dataclass_class_maker_callback` **silently disables `__init__` synthesis** on
every dataclass it touches — a false `[call-arg]` error on *valid* construction,
not a crash. Only surfaces if your fixtures include passing construction calls.

## The three-way coverage matrix (16 cases)

`✓` = correct verdict, `✗` = wrong verdict (missed a should-flag), `n/a` = not
a check that approach attempts.

| Case | Expect | AST tool | mypy-plugin | plain mypy |
|---|---|:---:|:---:|:---:|
| ddd001 good / bad | pass / flag | ✓ / ✓ | ✓ / ✓ | ✓ / ✗ |
| ddd002 good / bad (literal) | pass / flag | ✓ / ✓ | ✓ / ✓ | ✓ / ✗ |
| ddd003 good / bad | pass / flag | ✓ / ✓ | ✓ / ✓ | ✓ / ✗ |
| ddd004 good / bad | pass / flag | ✓ / ✓ | ✓ / ✓ | ✓ / ✗ |
| **ddd002 alias→dict** | flag | **✗** | **✓** | ✗ |
| **ddd002 custom unhashable class** | flag | **✗** | **✓** | ✗ |
| **primitive disguised by alias** | flag | n/a | **✓** | ✗ |
| **primitive disguised by cross-module import** | flag | n/a | **✓** | ✗ |
| primitive as NewType | pass | n/a | ✓ | ✓ |
| primitive as VO | pass | n/a | ✓ | ✓ |
| **Mars-Orbiter unit-swap (NewType)** | flag | n/a | ✓ | **✓ for free** |
| Mars-Orbiter good | pass | n/a | ✓ | ✓ |

- **AST tool**: correct on all four of its own checks; structurally blind to the
  two non-literal DDD002 cases (reads annotation *text*, sees `Tags` / `MutableBag`,
  not `dict` / unhashable); primitive-obsession and unit-swap aren't checks it
  attempts.
- **plain mypy `--strict`**: catches *nothing* in the DDD00x should-flag column —
  but catches the Mars-Orbiter unit-swap **for free**, no plugin, whenever VOs
  are `NewType`/`Annotated`.
- **mypy-plugin**: 16/16.

## Verdict

The plugin is 16/16, but its **unique** value — cases neither the AST tool nor
plain mypy gets right — is exactly **four rows / three checks**:

1. primitive-obsession field, seen through an alias / cross-module import;
2. non-literal mutable-collection field (alias → `dict`/`list`/`set`);
3. custom-class field that's unhashable at runtime (`__eq__` without `__hash__`).

DDD001/003/004 gain nothing from types, DDD004 is purely syntactic, and the
single highest-value type-aware win (unit-swap) is already free from plain mypy.
So the plugin is a **narrow complement, never a replacement**: if built, it does
only those three field-type checks, run *alongside* the zero-dep AST tool
(DDD001/003/004) and plain `mypy --strict` (unit-swap). Weigh that thin payoff
against the standing cost — an explicitly-unstable plugin API, the
chain-preemption trap, and DDD003's dependence on an undeclared internal — and
the call stays: **defer; build the narrow plugin only if those three disguises
actually show up in real pilot code.**
