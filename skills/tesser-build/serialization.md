# Norm: serialization

<!-- tb-status: full -->
<!-- tb-allow-missing: examples/python-app/campaign/application/parts.py -->

**A domain object never serializes itself, and its primitives leave through
exactly one door per shape.** This norm is scoped to the domain data types —
value objects, entities, aggregates — and to the two places that consume their
serialized form: gateways (repositories, cross-context, vendor) and the
application service's Respond step. Handlers never touch it: they translate
wire ↔ `Client` DTOs and never see a domain object (`handlers.md` rule 4).
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
     string guarantees it.
   - `datetime` → timezone-aware UTC ISO-8601 at a fixed precision. Naive
     datetimes don't cross edges.
   **The round-trip law locks every canonical exit:** reconstructing from
   the canonical form reproduces an equal value (`Slug(str(s)) == s`), and a
   test asserts it per leaf. Changing a canonical form is a representation
   change — a breaking change — never a formatting tweak.
4. **Display is a presentation concern, never the value object's.** Locale,
   grouping, currency symbols, human phrasing — a formatter at the
   presentation edge owns them. The canonical form is not "how it looks";
   it is "what it is".
5. **Compounds, entities, and aggregates have no primitive exit at all.**
   They decompose structurally (rule 6); their components are value objects
   reached through VO-returning accessors; an entity/aggregate ID is itself
   a leaf VO, and serializing a *reference* to an aggregate means that ID's
   canonical form. A compound's `__str__` (`"1.5 USD"`) is debug/log
   convenience and never crosses an edge.
6. **One decompose walk per context: the parts module.** A single module in
   the **application layer** (role, not filename — layout stays free) owns
   the outbound walk for the context's domain types, producing a **total,
   typed, domain-named** parts record: every field required (optional-by-
   default is banned — totality is what makes a forgotten field a
   missing-argument type error at one site), each leaf carried as its typed
   canonical primitive (`int` stays `int` — a binary/typed wire maps parts
   to native field types with no parse-back). The walk reads only the
   sanctioned public surface: VO accessors and canonical exits. It lives in
   the application layer because both of its consumers can legally reach it
   there: the service's Respond step (a sibling) and the adapters (which
   import the application layer; the reverse import would violate dependency
   direction). It does NOT live in the domain: a parts record is spec-shaped
   (public primitive fields), and the spec must remain the only primitive
   bag near the domain — inbound-only.
7. **Edges own their shape; they consume parts and never re-walk the
   domain.** Wire keys, casing, column names, payload framing — each
   adapter maps the parts record to its own format. The parts record speaks
   domain names only; if it emitted wire keys, one edge's rename would fork
   the shared layer.
8. **Graduation, not dogma.** A context with a single outbound edge and
   leaf-only unwraps may keep the walk inline or in a private per-adapter
   record + mapping function — that is the parts pattern's degenerate case
   (one consumer), not a second mechanism. Introduce the shared parts module
   at the first compound crossing an edge or the first second edge. An
   adapter whose needs genuinely diverge forks to its own private mirror —
   never by growing optional fields on the shared parts record.
9. **Serialization frameworks never touch domain types.** A workflow
   engine's payload converter (Temporal, Restate), an ORM, a JSON encoder —
   they serialize parts-derived records only. Letting the framework reach
   the domain is how value objects get hollowed into public-field primitive
   bags (observed at field scale; the pressure is real and this rule is the
   pressure valve).

**Migration caveat:** the parts record is total, but already-persisted data
is not. Adding a field to a compound forces an explicit decision at each
edge — a default, a backfill, or a loud load failure — and the decision
belongs to the edge, recorded where its golden test lives.

## Why one walk (the changeability case)

- **Scattered walks are silent on compound growth.** With the walk copied
  into N adapters, adding a component to a compound is N edits and every
  missed one ships silently — the edge just omits the field. Measured
  empirically: the per-edge inline walk left compound growth SILENT across
  every edge; the shared total parts record turned the same change into
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
- The **public-decompiler check** (this wave) flags rule 1's method half: a
  public method on a domain type returning a spec-classified type, an
  emit-a-sink method streaming private fields out, and a leaf VO with a
  second or mismatched conversion dunder. Deeper laundering (locals,
  helpers, dict-building) is declared out of contract — review territory.
- The **compound-raw-primitive check** (this wave) flags rule 5's internal
  half: a multi-field VO holding bare primitives instead of child VOs.
- The **parts import boundary** (adapters consume parts, not domain types,
  outbound) is a named deferred check; until it ships, rule 7 is
  review-enforced. Honest gap, stated.

## Tests you must write

- **Round-trip law, per leaf VO:** reconstructing from the canonical form
  yields an equal value.
- **Golden-dict tests, per edge:** the exact wire/row/payload shape locked
  as data. Goldens live at edges ONLY — the parts record is locked by its
  total constructor and the type checker, and goldening it would tax
  harmless internal renames.
- **Reconstruction round-trip, per repository:** save → load produces a
  value-equal, non-identical object with invariants re-run.

## Common mistakes

- **The public decompiler:** `to_spec()`/`to_dict()`/`emit(sink)` on a
  domain type. The walk belongs to the parts module.
- **The scattered walk:** each adapter reading component VOs itself. One
  walk; adapters consume parts.
- **Optional parts fields:** an `x: str | None = None` on the parts record
  re-admits the silent-omission bug totality just killed. Fork the
  divergent adapter instead.
- **Parsing `str(x)` to extract data:** the canonical form is an exit, not
  a transport container for components.
- **Framework-shaped domain:** public fields or primitive accessors added
  "because the serializer needs them" — route the framework through parts.

## Now build it

- Python mechanics: `python.md#value-objects` (canonical exits, child VOs),
  `python.md#the-spec-pattern` (inbound door). Compound shape verified in
  `examples/python/catalog/money.py`; parts verified impl:
  `examples/python-app/campaign/application/parts.py`.
- Go: **not yet materialized — note the gap, don't invent a convention.**
  The Go rendering re-hinges canonical text from `fmt.Stringer` to
  `encoding.TextMarshaler`/`TextUnmarshaler` (Stringer is Go's implicit
  display hook) and must solve the typed-exit problem (Go has no `__int__`
  analog and package privacy blocks cross-package field reads); tracked in
  `TODOS.md` (Go serialization mirror).
