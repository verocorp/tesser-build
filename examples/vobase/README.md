# vobase — the ValueObject-base rendering of a value object

This example ports `examples/python/catalog/money.py` from the
`@dataclass(frozen=True)` idiom to a shared undecorated base class:

```python
import tesser.domain as ts

class Money(ts.ValueObject):
    ...
```

`ts.ValueObject` (from `tesser-py/`) supplies value equality
(`type(self) is type(other)` + `self.__dict__ == other.__dict__`), a derived
`__hash__`, a generic `__repr__`, and the frozen `__setattr__`/`__delattr__`
guard. Each subclass carries only its validating constructor, domain methods,
and `__str__`; fields are written with `object.__setattr__` in `__init__` and
every stored field participates in equality and hash automatically — adding a
field is a one-site edit, as in the dataclass idiom.

One deliberate API difference from the catalog original: `Money.amount()` /
`Money.currency()` are plain methods, not `@property` accessors. mutmut skips
any decorated function (only a lone `@staticmethod`/`@classmethod` is exempt),
so a `@property` accessor would be invisible to mutation testing — the same
blindness this shape exists to escape.

The port also hardens validation gaps review found here that the catalog
original still has — a missing guard is missing code, which no mutation
operator can surface: amounts must be plain decimal strings (`-?\d+(\.\d+)?`,
so `"NaN"`, `"Infinity"`, `"1_000"`, `" 1.5 "`, `"+5"`, and `"1e2"` are all
rejected), zero has one canonical form, `add` raises instead of silently
rounding past 28 significant digits, and currency codes are stored stripped.

## Why this shape exists

mutmut (3.x) silently skips any class that carries any decorator — the whole
body, methods included — so the dataclass idiom yields zero mutants on value
objects. Measured on this example with mutmut 3.6+ (`mutmut run` in this
directory and in `tesser-py/`): the dataclass rendering of this same
`money.py` generates zero mutants in the module; this shape generates dozens
across the example and the shared base — exact counts shift as code evolves,
so run it rather than trust a number here — and the suites kill all of them.
The base keeps identity semantics out of per-class code entirely, so the
dropped-field equality defect is not expressible per class.

This is a candidate successor shape under evaluation, not yet the taught
convention — `skills/tesser-build/python.md` and `examples/python` still
render the dataclass idiom. Known cost of that status: `tessercheck-py` does
not classify `ts.ValueObject` subclasses as value objects, so none of the
identity-taxonomy checks (TB003, TB010–TB014) see this tree — the trade today
is mutation-testability for static enforcement. This example is therefore
deliberately not tessercheck-gated in CI; the classifier work is queued in
TODOS.md and lands with the adoption decision.

## Run it

```
MYPYPATH=.:../../tesser-py mypy --strict vobase tests
pytest -q
mutmut run   # local only; CI does not gate on mutation score
```
