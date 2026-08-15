# Norm: serialization

<!-- tb-status: full -->

**A domain object never serializes itself, and its primitives leave through
exactly one door per shape.** This norm is scoped to the domain data types —
value objects, entities, aggregates — and to the two places that consume their
serialized form: gateways (repositories, cross-context, vendor) and the
application service's Respond step. Handlers never touch it: they translate
wire ↔ `Client` DTOs and never see a domain object (`handlers.md` rule 5).
Errors/testing/comments apply to everything; this norm applies to how domain
data crosses an edge (maintainer rulings 2026-07-20).

## The norm

1. **Domain objects never serialize themselves.** No `MarshalJSON`, no
   `to_wire()`, no `to_dict()`, no emit-a-sink method, and no public
   `decompose()`/`to_spec()` — a public decompose-to-primitives surface is a
   representation leak that also enables decomposed-form equality, and was
   red-teamed out in the reference discipline. Wire and storage shapes are
   edge property; the domain exports none of them.
2. **Inbound has one door: spec → constructor.** Reconstruction (from a row,
   a payload, a wire request) builds the spec and goes through the validating
   constructor, so every invariant re-runs on the way in. Stale persisted
   data surfacing as a constructor error on read is a feature. The spec is
   inbound-only — it is never the outbound snapshot.
3. **A leaf value object has one canonical exit: the conversion protocol.**
   The leaf exposes its canonical form through the ONE conversion dunder
   matching its backing primitive — str-backed → `__str__`, int-backed →
   `__int__`, float-backed → `__float__`, bytes-backed → `__bytes__`. Never a
   named accessor (`value()`, `to_int()` — TB010 territory), never a second
   dunder, never one that mismatches the backing type (a str-backed VO with
   `__int__` is a disguise). Representations without a conversion protocol
   exit as canonical text via `__str__` under an explicit policy:
   - `Decimal` → its string form (`str(Decimal)`) — cross-language precision
     is why: the same value must survive Python/Go/SQL hops, and only the
     string guarantees it. Known and accepted (2026-07-20): equal Decimals
     may render distinct canonical text (`1.5` and `1.50` are equal values
     with different forms) — the round-trip law holds; byte-identity of
     equal values does not. Revisit only on field evidence (e.g. byte-level
     dedup or idempotency keying on canonical strings).
   - `datetime` → timezone-aware, UTC-normalized, ISO-8601 with
     **microsecond precision** — exactly
     `value.astimezone(timezone.utc).isoformat(timespec="microseconds")`
     (`2026-07-20T15:16:15.123456+00:00`). Pinned 2026-07-20. Naive
     datetimes don't cross edges. The broader time-type taxonomy (instant
     vs date vs local time; per-precision types) is a named open decision —
     `TODOS.md`.
   **The round-trip law locks every canonical exit:** reconstructing from
   the canonical form reproduces an equal value (`Slug(str(s)) == s`), and a
   test asserts it per leaf. Changing a canonical form is a representation
   change — a breaking change — never a formatting tweak.
   **The exit routes through a per-type policy helper — the dunder body is
   one line.** The app-level serialization module owns one function per
   backing type — `canonical_str` / `canonical_int` / `canonical_float` /
   `canonical_bytes` (identity for the native primitives) and
   `canonical_decimal` / `canonical_datetime` (the text policies above,
   executable) — and every leaf's conversion dunder delegates to the
   matching one:

   ```python
   def __str__(self) -> str:
       return canonical_decimal(self._value)
   ```

   This gives each canonical-form policy exactly ONE implementation site (a
   consumer's tenth datetime VO cannot drift from the pinned format), makes
   every canonical exit self-announcing at its definition (grep
   `canonical_` to find them all — a hand-rolled `__str__` is visibly not a
   canonical exit), and is statically typed with no runtime dispatch.
   Consumers of the exit — the mapping walk, edges — call the conversion
   protocol directly (`str(vo)`, `int(vo)`). (Maintainer ruling 2026-07-20,
   superseding two same-day edge-side shapes — a one-arg introspective
   `canonical(vo)` dispatcher, then a two-arg `canonical(vo, expected)`
   verifier: the helper belongs at the exit's definition, not at the unwrap
   site; runtime introspection re-derived facts the call site already knew.
   What the runtime verifier guarded — `str()` on a structured type
   silently yielding `repr` garbage, since `str()` never fails — is covered
   by the mandatory per-edge goldens below and the zero-dunder checker.)
   Verified impls: `examples/python-app/serialization.py` (the module),
   `examples/serdepy/` (every backing type exercised).
4. **Display is a presentation concern, never the value object's.** Locale,
   grouping, currency symbols, human phrasing — a formatter at the
   presentation edge owns them. The canonical form is not "how it looks";
   it is "what it is".
5. **Compounds, entities, and aggregates have no primitive exit at all —
   including no conversion dunders.** They decompose structurally (rule 6);
   their components are value objects reached through VO-returning
   accessors; an entity/aggregate ID is itself a leaf VO, and serializing a
   *reference* to an aggregate means that ID's canonical form. A compound
   defines **zero** conversion dunders — no `__str__`, no `__int__`, none
   (maintainer ruling 2026-07-20: a "debug `__str__`" carve-out reads
   exactly like the single-representation carve-out this norm closed, so it
   doesn't exist; the default `repr` serves debugging, and how constructed
   apps log is its own future norm — `logging.md`, placeholder). The
   contract is mechanically crisp: a leaf has exactly one matching
   conversion dunder; a structured type has none.
6. **One decompose walk per context, into port DTOs.** The outbound shape a
   context's domain types decompose into is a **port DTO** — a `ts.Request`
   or `ts.Response` declared in the `application/ports/` package beside the
   port that speaks it (`python.md#ports`) — and a single **mapping module
   in the application role** (`mapping.py` / `views.py`; role, not filename)
   owns the walk that builds it. The DTO is **total, typed, and
   domain-named**: every field required (optional-by-default is banned, and
   TB080 bans a union field outright — totality is what makes a forgotten
   field a missing-argument type error at one site), each leaf carried as
   its typed canonical primitive (`int` stays `int` — a binary/typed wire
   maps fields to native types with no parse-back), a multi-outcome answer
   an enum plus payload, a collection a tuple. The walk reads only the
   sanctioned public surface: VO accessors and canonical exits.
   **Why the split.** The DTO lives in `application/ports/` because that is
   the one part of `application` an adapter may import (TB060) — and because
   a ports module is a leaf that imports nothing from its tree (TB067), the
   DTO structurally *cannot* reference a domain type. The walk lives in the
   application role beside the service, because it must touch both sides and
   an adapter may never see a domain object at all. Neither half lives in the
   domain: a port DTO is spec-shaped (public primitive fields), and the spec
   must remain the only primitive bag near the domain — inbound-only.
7. **Edges own their shape; they consume port DTOs and never re-walk the
   domain.** Wire keys, casing, column names, payload framing — each
   adapter maps the DTO to its own format. The DTO speaks domain names only;
   if it emitted wire keys, one edge's rename would fork the shared layer.
8. **A diverging edge forks to its own port, never to optional fields.**
   Each port module declares exactly one port with the DTOs that port
   speaks, and no two ports may share a DTO (TB052 — and the leaf rule makes
   sharing unrepresentable: a ports module cannot import its own sibling). So
   the second edge whose needs genuinely differ gets its own ports module
   with its own request and response, and the mapping module grows a second
   walk. Widening one shared DTO with optional fields — the shape this used
   to tempt — is banned twice over: by TB080 (no union field) and by the
   silent-omission bug totality exists to kill.
9. **Serialization frameworks never touch domain types.** A workflow
   engine's payload converter (Temporal, Restate), an ORM, a JSON encoder —
   they serialize port DTOs and edge-owned records only. Letting the
   framework reach the domain is how value objects get hollowed into
   public-field primitive bags (observed at field scale; the pressure is
   real and this rule is the pressure valve).

**Migration caveat:** the port DTO is total, but already-persisted data
is not. Adding a field to a compound forces an explicit decision at each
edge — a default, a backfill, or a loud load failure — and the decision
belongs to the edge, recorded where its golden test lives.

## Why one walk (the changeability case)

- **Scattered walks are silent on compound growth.** With the walk copied
  into N adapters, adding a component to a compound is N edits and every
  missed one ships silently — the edge just omits the field. Measured
  empirically: the per-edge inline walk left compound growth SILENT across
  every edge; the shared total DTO turned the same change into
  type errors at one site.
- **Two mechanisms fork.** A codebase that decomposes some types with
  methods and others with inline walks makes "which site do I change?"
  unanswerable — observed in a real tree that ran both, inconsistently,
  inside a single statement.
- **`String()`-roundtripping is the worst walk.** Parsing a display string
  to get at components silently couples the wire to display formatting.
  The canonical-exit rules exist so no edge is ever tempted.

## How the machine sees it

- **TB010** flags the leak's accessor half: public primitive fields and
  passthrough accessors on a VO.
- **TB015** (the public-decompiler check) flags rule 1's method half: a
  public method on a domain type returning a spec-classified type, an
  emit-a-sink method streaming private fields out, a leaf VO with a second
  or mismatched conversion dunder, and **any conversion dunder on a
  compound/entity/aggregate** (rule 5's zero-dunder contract), collection
  value objects included. Deeper laundering (locals, helpers, dict-building)
  is declared out of contract — review territory. Leaf-vs-structured is
  decided mechanically: exactly one field annotated with a bare scalar is a
  leaf; anything else — two or more fields, a collection field, a field typed
  as another domain object — is structured. A single `bool`/`complex` field
  reads as a leaf shape (not misreported as structured), but the leaf itself
  is a TB016 violation — those scalars are not value-object material.
- **TB016** (the value-object-primitives check) flags rule 5's internal
  half: what a VO may be built from. A compound holds child VOs, not bare
  primitives. The wrappable set is "primitive" in the DDD sense — the
  language scalars plus the stdlib temporals (`date`/`datetime`/`time`),
  which a compound wraps in child VOs just like a `Decimal`, and a
  `date`-backed leaf exits as canonical text via `__str__` (maintainer ruling
  2026-07-20). `bool` and `complex` are the exception: they are **not
  value-object material at all** — a `bool` is atomic (model it raw, or an
  enum when it is richer than binary; it has no canonical conversion exit),
  `complex` has no domain wire form — so wrapping either in a VO, or holding
  one as a VO field, is itself the violation (ruling 2026-07-20). The
  wrappable set is now exactly the set with a ruled canonical exit; there is
  no must-wrap-without-an-exit gap. Types with no stereotype meaning at all
  (`UUID`, `Enum`) stay out of contract rather than guessed at.
- **TB017** (the single-construction-door check) flags the inbound half of the
  same discipline: a value object constructs through its own `__init__` and
  nothing else, so **any** classmethod or staticmethod returning its own type
  is a second door — name-agnostic, because the name was never what made it
  one (`from_spec`, `parse`, `new`, `require`, `of` alike). Two doors mean two
  invariant sets on one type: if `new` is permissive and `require` demands
  non-empty, what the type guarantees depends on which door the caller picked.
  A factory returning some *other* type is not a door and is left alone; specs
  are inert carriers and out of scope; entities and aggregates fall under
  TB080, whose door rule is the spec itself — a domain constructor takes
  exactly one `ts.Spec`.
- **TB018** (the canonical-exit-routing check) flags rule 3's delegation half:
  a leaf's conversion dunder must be a one-line delegation to the
  `canonical_*` helper matching its backing type. Two shapes — not a
  delegation at all (`return self._value`, `return str(self._value)`, or a
  post-processed helper result), and delegation to the *wrong* policy (a
  `Decimal` leaf routed through `canonical_str` gets str's identity instead of
  the pinned decimal text). A hand-rolled exit is a second implementation of a
  pinned form: correct the day it is written, silently drifted the day the
  policy changes. The mismatched-*dunder* shape stays TB015's, so a violation
  gets exactly one code. `date`- and `time`-backed leaves are **out of
  contract**: they have a ruled exit (`__str__`) but no ruled canonical form
  yet — the time-type taxonomy is a named open decision (`TODOS.md`) — and out
  of contract beats guessed at, as with `UUID` and `Enum`.
- The **port-DTO import boundary** (adapters consume DTOs, not domain types,
  outbound) was a named deferred check and is now enforced from both ends:
  **TB060** lets an adapter import `application/ports` and nothing else of
  `application`, **TB067** makes a ports module a leaf that imports nothing
  from its tree, and **TB081** flags a domain object in a port or adapter
  signature. Rule 7's remaining half — that the *edge*, not the DTO, owns wire
  keys and framing — stays review-enforced. Honest gap, narrowed.
- **TB080** flags the DTO-field half of rules 6 and 8: a port DTO field is
  never a union (optional included) and never a bare `bool` — model the
  outcome as an enum. **TB052** flags the rest of the ports module's contents:
  a subclassed DTO (a response hierarchy is a union mypy cannot check for
  exhaustiveness), a `StrEnum`/`IntEnum` outcome (a member that compares equal
  to a raw literal reopens the typo the enum closes), a second port in the
  module, and any class that is neither the port nor a DTO it speaks.

## Tests you must write

- **Round-trip law, per leaf VO:** reconstructing from the canonical form
  yields an equal value.
- **Golden-dict tests, per edge:** the exact wire/row/payload shape locked
  as data. Goldens live at edges ONLY — the port DTO is locked by its
  total constructor and the type checker, and goldening it would tax
  harmless internal renames.
- **Reconstruction round-trip, per repository:** save → load produces a
  value-equal, non-identical object with invariants re-run.

## Common mistakes

- **The public decompiler:** `to_spec()`/`to_dict()`/`emit(sink)` on a
  domain type. The walk belongs to the application's mapping module.
- **The scattered walk:** each adapter reading component VOs itself. One
  walk; adapters consume port DTOs — and cannot do otherwise, since an
  adapter may not import the domain.
- **Optional DTO fields:** an `x: str | None = None` on a port DTO
  re-admits the silent-omission bug totality just killed (and TB080 rejects
  the union outright). Give the diverging edge its own port instead.
- **Logic in the ports module:** a helper function, a shared outcome
  constant, a mapping function parked beside the DTO it builds. A ports
  module holds imports and classes, nothing else (TB051) — the walk goes in
  the application's mapping module, where it can legally see both sides.
- **Parsing `str(x)` to extract data:** the canonical form is an exit, not
  a transport container for components.
- **Hand-rolling a canonical form inside a dunder:** a leaf's `__str__`
  formatting its value inline (`self._value.isoformat()`,
  `f"{self._value:.2f}"`) instead of delegating to the matching
  `canonical_*` policy helper — the tenth such VO silently drifts from the
  pinned format, and the exit stops being greppable as canonical.
- **Merging the port DTO and the spec because they look alike:** a minimal
  context's record is often a field-for-field twin of its spec — that is a
  coincidence of the simple case, not an identity. The spec is inbound-only
  (accepts any valid representation, feeds the validating constructor); the
  port DTO is outbound-only (carries exactly the canonical forms, and
  grows derived fields the constructor must never accept). Deduplicating
  them welds the two directions together — and is now structurally
  impossible: a ports module imports nothing from its tree (TB067), so it
  cannot reach a spec even to alias it.
- **A "just for logging" dunder on a compound:** the zero-dunder contract
  has no debug carve-out; `repr` is the debug surface, and logging norms
  are `logging.md`'s to settle.
- **Framework-shaped domain:** public fields or primitive accessors added
  "because the serializer needs them" — route the framework through the port
  DTO.

## Now build it

- Python mechanics: `python.md#value-objects` (canonical exits, child VOs),
  `python.md#the-spec-pattern` (inbound door), `python.md#ports` (the ports
  package and its DTO rules). Compound shape verified in
  `examples/python-app/campaign/domain/money.py`; the walk-plus-DTO pair
  verified in `examples/serdepy/parcel/application/mapping.py` and
  `examples/serdepy/parcel/application/ports/parcel_wire.py`.
- The all-cases worked example: `examples/serdepy/` — every backing type's
  exit (all four conversion dunders, the Decimal and datetime text
  policies), the zero-dunder compound, a port DTO whose derived field
  (`weight_class`, an enum) proves DTO ≠ spec by construction, an edge golden
  with edge-owned keys and framing (bytes → hex), and the full required test
  set in miniature.
- Go: **not yet materialized — note the gap, don't invent a convention.**
  The Go rendering re-hinges canonical text from `fmt.Stringer` to
  `encoding.TextMarshaler`/`TextUnmarshaler` (Stringer is Go's implicit
  display hook) and must solve the typed-exit problem (Go has no `__int__`
  analog and package privacy blocks cross-package field reads); tracked in
  `TODOS.md` (Go serialization mirror).
