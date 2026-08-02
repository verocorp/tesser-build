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

The port also hardens two validation gaps review found here (non-finite
amounts like `"NaN"`/`"Infinity"`, whitespace-only currency) that the catalog
original still has — a missing guard is missing code, which no mutation
operator can surface.

## Why this shape exists

mutmut (3.x) silently skips any class that carries any decorator — the whole
body, methods included — so the dataclass idiom yields zero mutants on value
objects. Measured on this Money example (2026-07): dataclass idiom, 7 mutants
none in any class; this shape, 97 mutants with 79 landing in the subclasses'
real logic. The base keeps identity semantics out of per-class code entirely,
so the dropped-field equality defect is not expressible per class.

This is a candidate successor shape under evaluation, not yet the taught
convention — `skills/tesser-build/python.md` and `examples/python` still
render the dataclass idiom.

## Run it

```
MYPYPATH=.:../../tesser-py mypy --strict vobase tests
pytest -q
mutmut run   # local only; CI does not gate on mutation score
```
