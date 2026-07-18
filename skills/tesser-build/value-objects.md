# Value Object

A value object is a domain concept defined entirely by its attributes: two
instances with the same attributes are the same value and are interchangeable.
It has no identity and no lifecycle — you don't change a value object, you
replace it (Evans, *Domain-Driven Design*, ch. 5; Vernon, *Implementing
Domain-Driven Design*, ch. 6). Money is the canonical example: one "USD 100"
is as good as any other "USD 100".

## Is this what I'm building?

**Test:** *Could I swap this instance for another with the same attributes and
nothing would change?* Yes → value object.

**The primitive-obsession check** (when adding a `string`/`int`/`time`/... field):
wrap the primitive in a value object when the value is **domain-meaningful** —
it has validation rules, domain behavior, or a meaning the type name should
carry (`EmailAddress`, not `string`; `Money`, not `int64`). Do NOT wrap when
the primitive is incidental: a log line, a purely technical counter, a
persistence-only column, a local implementation detail. Blanket wrapping is
**value-object theater** — it adds ceremony without adding meaning.

**Near-misses that are NOT value objects:**
- A **Spec / DTO** — a data carrier crossing a layer boundary. No behavior, no
  validation, primitive leaves. It *feeds* a value object's constructor.
- A **persistence/row model** — shaped by storage, not by the domain.
- An **enum / type code** — a closed set of named constants that *selects*
  behavior; it's a primitive with a name, not a value object.

## Rules

1. **Immutable, always.** No setters, no mutation methods — a changed value is
   a different value. (Identity-free things can't "change"; there is no *it*.)
2. **One validating constructor** is the only construction path. Invalid
   values are unrepresentable after construction.
3. **Private fields, public accessors.** The representation never leaks; the
   constructor's guarantees can't be bypassed.
4. **Equality is by value, and it's explicit.** Same attributes ⇒ equal,
   across all representations of the same logical value.
5. **Validation belongs to the value, not its parents.** A parent constructor
   never re-checks a child value object's rules — it just builds the child and
   propagates the error.
6. **Display is not equality.** The string form exists for humans; comparing
   two objects by their string forms silently mis-equates multi-representation
   values.
7. **Domain behavior lives on the type** (`Add`, `Contains`, `Overlaps`...)
   and enforces its own consistency (e.g., same-currency arithmetic).

## Shape

```
EmailAddress            Money
  - value (hidden)        - amount   (hidden)
                          - currency (hidden)
  NewEmailAddress(...) → (EmailAddress, error)
```

Construction mechanics, spec structure, and language idioms: see
`go.md#value-objects` / `python.md#value-objects`.

## Decisions you must make

1. **Simple or compound?** One argument → flat constructor (the type *is* its
   value: an ID, a code — it won't grow; growth would mean a different
   concept). Two or more arguments → construct via a spec (compound concepts
   accrete attributes; a spec prevents a definition cascade through every
   parent that embeds the type). See `go.md#the-spec-pattern` /
   `python.md#the-spec-pattern`.
2. **Equality path.** If every logical value has exactly one representation,
   native equality works. If the same logical value has multiple
   representations (decimals: `1.5` vs `1.50`), native equality LIES — block
   it and provide an explicit `Equal` that compares logical values. Your
   language file shows both paths.
3. **Collection value object?** A raw map/slice/dict field should become a
   value object when 2+ of: parents validate it in their constructors; it has
   dedicated behavior functions; the same raw shape appears in 2+ domain
   types; defensive copies are being written around it.

## How the machine sees it

The analyzers treat a type with a `NewX(...) (X, error)` constructor as a
value-object candidate, then **subtract** types matching entity/aggregate
signals (identity field/method, setters, owned domain collections) via a
human-ratified exclude list. These signals are *heuristics that flag
candidates for human judgment* — never the definition. A DTO can carry an
`ID string` field without being an entity; the human ratifies the list.

## Tests you must write

- **Constructor rejection:** each validation rule has a test proving invalid
  input returns an error (not a panic).
- **Equality semantics** (`Test*_Equality` / `test_*_equality`): same value ⇒
  equal; different value ⇒ not equal; multi-representation values ⇒ equal
  across representations, native comparison blocked where it would lie.
- **Panic-constructor contract** where the language provides one (`MustNew*`):
  panics on invalid input; used only with known-valid literals in tests.
- **Display** (`Test*_String`): stringification tested in its own test — and
  **never** used as an equality proxy anywhere else.

## Common mistakes

- **Value-object theater:** wrapping every primitive on sight. Run the
  primitive-obsession check; wrap meaning, not plumbing.
- **String-form equality:** `a.String() == b.String()` in a test. Compare by
  value.
- **Parent re-validation:** an aggregate's constructor re-checking an email
  format. The `EmailAddress` constructor already did; trust it.
- **Leaked representation:** a public field or an accessor returning the
  mutable innards. Copies out, never references.
- **Validation drift:** a second construction path (a mapper, a test helper)
  that skips the constructor. One door.

## Now build it

- Go: `go.md#value-objects`, then `go.md#the-spec-pattern`
- Python: `python.md#value-objects`, then `python.md#the-spec-pattern`
