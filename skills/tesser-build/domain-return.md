# Norm: domain return

<!-- tb-status: full -->

**A domain object's behavior hands back domain objects.** A method on a value
object, entity, or aggregate root does not return a primitive, an enum, a
foreign value (`Decimal`, `datetime`), or a DTO. Those are representation, and
a method that hands one out is the public field with extra steps — the same
leak `value-objects.md` rule 3 bans on fields, one call further away.

This norm is scoped to the domain data types and keyed on the **declared**
base: a class that subclasses `ts.ValueObject` / `ts.Entity` /
`ts.AggregateRoot` has stated what it is, and this is the rule on what its
behavior may return. (Maintainer ruling 2026-08-08.)

## The norm

1. **A public method returns a domain object.** Its own type, another value
   object, an entity, or a collection of them. Containers are transparent —
   `tuple[Money, ...]` is fine, `tuple[tuple[str, int], ...]` is not.
2. **The comparison dunders are not implemented.** `__eq__`, `__ne__`, `__lt__`,
   `__le__`, `__gt__`, `__ge__` are *not* fixed by the language — CPython hands
   back whatever they return — so a `-> bool` there is a choice, and it is the
   same leak as a `before()` returning `bool`. Licensing one spelling and
   banning the other was an artifact. The base owns them: `ValueObject`
   compares by value, `Entity` compares by `identity`, an aggregate root blocks
   equality with `__eq__ = None`. Domain code spells none of them.

   **Enforced by the base, not by TB019.** `ValueObject.__init_subclass__` and
   `Entity.__init_subclass__` raise `TypeError` when a subclass overrides
   `__eq__`/`__hash__` — at import time, which beats lint time — so equality
   shape needs no checker at all. TB019 governs the ORDINARY methods,
   where nothing else is watching.
3. **Two exits, because the rule cannot reach them.**
   - **Language-fixed dunders.** CPython raises `TypeError` if these return
     anything else, verified per dunder: `__hash__`, `__str__`, `__repr__`,
     `__bool__`, `__len__`, `__int__`, `__float__`, `__bytes__`, `__index__`,
     `__format__`, and `__contains__` (which coerces). `__bool__` is where the
     boolean terminator actually lives — ONE language-pinned site, not a bool
     at every predicate. A leaf's canonical conversion exit is among these, and
     `serialization.md` rule 3 requires it; TB015/TB018 govern it, not this norm.
   - **A `-> None` transition.** A command has no value to promote; whether it
     should return the new state instead is the fact-vs-lifecycle decision
     `entities.md` leaves to the domain.
4. **An internal comparison stays internal.** A predicate used only inside its
   own module is private, and out of this norm's scope. Do not invent a type to
   carry a yes/no across a boundary nobody crosses.
5. **Do not wrap a bool to satisfy rule 1.** A generic truth-wrapper has no
   validation, no behavior and no domain meaning — `value-objects.md`'s
   primitive-obsession check calls that theater, and TB016 bans a bool inside a
   value object. When state really is richer than binary, model the *concept*:
   a closed-set value object constructed from the domain's enum (`LinkStatus`
   over `LinkState.ACTIVE`/`INACTIVE`, `Decision` over allowed/denied),
   string-backed so it has a canonical exit. The enum is a primitive with a
   name, declared plain in the domain (no `ts.*` base); the value object
   wraps it the way a `Slug` wraps a `str`, and never hands it back out.

## Decisions you must make

1. **Is this predicate public?** If only your own module asks, make it private
   and stop. If a caller outside asks, the answer is a concept, not a boolean —
   name it (rule 5).
2. **Where does the primitive re-enter?** At the edge, and only there. The
   application layer's port DTOs (`application/ports/`) and the `Client` DTOs
   carry primitives;
   they unwrap through the canonical exit (`str(vo)`, `int(vo)`). The domain
   exports no shape (`serialization.md` rule 1).

## Tests you must write

- **Answer type is a value:** two calls with the same inputs produce equal
  answers, and the answer exposes no selector to switch on.
- **Closed set rejects:** a state outside the set fails construction, so an
  undecided case cannot exist.
- **Edge unwraps once:** the DTO built at the boundary carries the primitive;
  the domain object never handed one out.

## Common mistakes

- **The truth-wrapper.** A `Truth`/`Bool` value object with `__bool__` and
  nothing else. It is a bool in a box; it satisfies the letter of rule 1 and
  none of its point. Rule 5.
- **Renaming, not removing, the predicate.** `active -> bool` becoming
  `active -> StatusVO` that callers still compare against constants is the enum
  in a value object's coat. The branch belongs to the type.
- **Spelling a comparison as a word to dodge the base.** `same_as`, `equals`,
  `is_before` returning `bool` are rule 2 in disguise.
- **Unwrapping in the domain.** `str(...)`/`bool(...)` inside a domain method,
  to compare or branch, drags the representation back into the model. Compare
  the value objects.

## How the machine sees it

`TB019` (`tessercheck-py`) keys on the classified stereotype, which the declared
`ts.*` base establishes. It skips private methods, dunders, and unannotated
ones (the gated trees run `mypy --strict`, which already requires the
annotation), reads containers through to their payload, and resolves a
`tesser.domain`-qualified return without the library being in the analyzed tree.

It also stands down where another check already owns the shape, so one leak is
never reported twice: a bare `return self._x` belongs to TB010 (value object)
and TB011 (aggregate collection); a spec-typed return belongs to TB015.

There is no Go analyzer yet — a named gap, tracked in `TODOS.md`.

## Now build it

- Python: `python.md#value-objects`, then `serialization.md` for the edge
- The base contracts: `value-objects.md` rule 4, `entities.md` rule 6,
  `aggregates.md` rule 4
