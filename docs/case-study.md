# Case study: the discipline, measured on a real codebase

The `rationale/` fixture proves the *mechanism* (typed value objects turn silent
bugs into compile errors). This is the *magnitude*, measured on a real ~1,100-commit
Go codebase by running the compiler against real mutations (see
`rationale/measure-ablation.sh`). Numbers are anonymized; the raw, commit-cited
evidence lives in the originating private repo.

- **Rename a typed value object:** touched **269 references across 28 files** —
  every one enumerated by the compiler, zero missed. The same concept in its
  earlier **bare-string** form had **360 silent literal sites** the compiler
  could not see; a rename there is a find-and-replace with no safety net.

- **Retype the representation:** behind a value object, changing the underlying
  type touched **1 production file** (the private field) — callers never saw it.
  The same value as a bare primitive is exposed at every site that holds it.

- **A real shipped bug from the silence:** a domain discriminator stored as a
  bare string had one of its values renamed. The compiler flagged **0** of the
  ~223 literal sites. A corrective commit landed **39 minutes later** to patch
  sites the rename missed — and one stale literal survived for **months** as an
  invalid value that errors at runtime. That is the silent surface shipping a bug.

- **Inconsistent adoption costs like no adoption (the third contender):** a
  concept whose value object *already existed* was still read as a **bare string
  in one slot across 43 call sites**. The value object bought nothing for those
  43 sites — a change to the concept stayed silent there, exactly as if no value
  object existed. This is the real-world magnitude behind `rationale/inconsistent/`:
  half-adopted value objects sit on the bare-primitive end of this table, not the
  typed end. The dividend is bought by adopting the concept *everywhere and the
  same way*, not by the type existing somewhere.

**The metric:** changeability cost is dominated by **silent sites** — edits the
compiler can't flag, that a human must find by hand and can miss. A value object
drives silent sites to **zero** by making every change either a compile error or
a rejected construction. A bare primitive leaves them as an unbounded,
compiler-invisible surface.

**Honest boundary** (see `rationale/` benchmarks): value objects are *free* for
simple value types and cost a real allocation only for collection VOs with
defensive copies on a hot path. The discipline buys safety; it is not free on a
tight loop over a collection.
