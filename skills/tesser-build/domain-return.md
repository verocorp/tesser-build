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
   object, an entity, an outcome (rule 6), or a collection of them. Containers
   are transparent — `tuple[Money, ...]` is fine, `tuple[tuple[str, int], ...]`
   is not.
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
     `__format__`, and `__contains__` (which coerces). `__bool__` stays licensed
     because the language fixes it, but it is *not* how a caller branches on
     what the domain did — that is an outcome (rule 6); `__bool__` is truthiness
     (an empty collection), one language-pinned site. A leaf's canonical
     conversion exit is among these, and `serialization.md` rule 3 requires it;
     TB015/TB018 govern it, not this norm.
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
   wraps it the way a `Slug` wraps a `str`, and never hands it back out. That
   is what the object *is*. What a call *did* is rule 6.
6. **Control flow comes back as an outcome.** When a caller needs to act on
   what a transition did — continue or stop, taken or held, matched or
   deferred — the transition returns a `ts.Outcome`: a closed set of names,
   declared in the domain, that subclasses `ts.Outcome` alone, carries nothing
   but `enum.auto()` members, and is a value object (Vernon's standard type;
   maintainer ruling 2026-08-26). It is the **return value** of a call, never
   a **field**: nothing holds one, no spec or DTO carries one, no port speaks
   one, and it has no canonical exit because it never leaves the process — it
   lives between the `return` and the `match`. The only reader is a `match`
   that closes with `case _ as never: assert_never(never)`, so a member added
   later fails `mypy --strict` at every reader instead of falling through. A
   member is named in exactly two places: the `return` that produces it and
   the `case` that consumes it; `== Outcome.X` anywhere is a branch the type
   checker cannot exhaust. Two members is the loop shape (`while True:
   match outcome:`); a third member is a type error at every site, not a
   redesign. If you find yourself wanting to persist or transmit one, it was a
   status — a field, on the spec, with an exit (rule 5). (TB084.)

## Decisions you must make

1. **Is this predicate public?** If only your own module asks, make it private
   and stop. If a caller outside asks, the answer is a concept, not a boolean —
   name it (rule 5).
2. **Where does the primitive re-enter?** At the edge, and only there. The
   application layer's port DTOs (`application/ports/`) and the `Client` DTOs
   carry primitives;
   they unwrap through the canonical exit (`str(vo)`, `int(vo)`). The domain
   exports no shape (`serialization.md` rule 1).
3. **Is the caller asking what the object is, or what a call did?** A field
   is state: the repository must write it down and read it back, so it lives
   on the spec with an exit, and behavior that depends on it lives on the
   type. A return value is an answer: nobody stores it, the caller acts on it
   once — that is an outcome (rule 6). The test: *could the repository need
   this to rebuild the object?* Yes → field. No → outcome. One `status()`
   serving both is the thing rule 5 calls the coat.

## Tests you must write

- **Answer type is a value:** two calls with the same inputs produce equal
  answers, and the answer exposes no selector to switch on.
- **Closed set rejects:** a state outside the set fails construction, so an
  undecided case cannot exist.
- **Edge unwraps once:** the DTO built at the boundary carries the primitive;
  the domain object never handed one out.
- **Every outcome member is reachable:** one test per member drives the
  transition into that answer and asserts the state it left behind. The
  exhaustiveness of the readers is mypy's test, not yours.

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
- **The status accessor.** `status() -> RunOutcome` computed from a field, so
  the caller can `match` on what the object *is*. That is a field reported
  through an outcome's type — the coat with a new hat. An outcome comes back
  from a transition (`advance() -> Advance`), never from an accessor
  (decision 3).
- **An enum with `is_*` methods.** `Progress.is_done()` is `== DONE` spelled
  as a word: a third member makes it silently `False`. A domain enum is
  members-only (TB051), and an outcome is members-only (TB084); the branch is
  the `match`, closed by `assert_never`.
- **The loop on `__bool__`.** `while run:` reads as one call, but it is a
  second spelling of the same thing and cannot grow a third state. Return a
  two-member outcome and `match` it (rule 6).

## How the machine sees it

`TB019` (`tessercheck-py`) keys on the classified stereotype, which the declared
`ts.*` base establishes. It skips private methods, dunders, and unannotated
ones (the gated trees run `mypy --strict`, which already requires the
annotation), reads containers through to their payload, and resolves a
`tesser.domain`-qualified return without the library being in the analyzed tree.

It also stands down where another check already owns the shape, so one leak is
never reported twice: a bare `return self._x` belongs to TB010 (value object)
and TB011 (aggregate collection); a spec-typed return belongs to TB015. A
`ts.Outcome` return is a domain object to TB019.

`TB084` owns the outcome itself, keyed on the declared `ts.Outcome` base: the
class subclasses `ts.Outcome` directly and alone (no mixin, no hierarchy),
undecorated, and carries nothing but `enum.auto()` members; nothing keeps one
— not an annotated field, not `self._last = self.advance()` (a spec, DTO, or
port carrying one is already TB080/TB081); and across every non-test module a
member is named only as a `return` value or inside a `case` pattern, the class
itself is named only in an annotation, a return, or a case pattern (no
`Advance["DONE"]`, `getattr`, or iteration), and every `match` that names one
has only member arms (or `|` of members) before an unguarded `case _ as
never: assert_never(never)` (or `return assert_never(never)`) with
`assert_never` still bound to `typing`'s; no function takes an outcome as a
parameter; and nothing reads `_value_` or `_name_`. Out of scope, by ruling
rather than oversight: reflection through a *local* (`vars(outcome)`,
`getattr(outcome, ...)`, `type(outcome)(2)`) and a keep through another
object's transition (`self._last = other.advance()`) — both need type
inference the walk does not have; the runtime's raising `.value`/`.name`
covers the path anyone would actually type. The runtime
base (`tesser.domain.Outcome`) raises at class definition for anything in the
body but `enum.auto()` members — a method or a descriptor of any name (a
`functools.cached_property`, dunders included), class data, an annotation, a
valued member, a member repeating another member's value (an alias makes a
`case` arm unreachable), a mixed-in or intermediate base, or a custom
metaclass — and `.value`/`.name` raise on every member — so the shape holds,
and there is nothing to read, even where the analyzer does not run.

There is no Go analyzer yet — a named gap, tracked in `TODOS.md`.

## Now build it

- Python: `python.md#value-objects`, `python.md#outcomes` for control flow,
  then `serialization.md` for the edge
- The base contracts: `value-objects.md` rule 4, `entities.md` rule 6,
  `aggregates.md` rule 4
