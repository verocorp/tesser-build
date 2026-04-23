# go-ddd

Go DDD enforcement toolkit: analyzers, workflows, and CI actions for Go repos following domain-driven design conventions.

## What's here

### `cmd/` — DDD convention checkers

Standalone Go programs that walk a directory and report violations. Each exits 0 on PASS, 1 on FAIL.

| Checker | What it enforces |
|---|---|
| `checkmustnew` | Every value-object constructor `NewX(...) (X, error)` has a paired `MustNewX(...) X` that panics on error. Tests use `MustNewX` for inline construction. |
| `checkequality` | Every value-object type `X` has a `Test*_Equality` test function covering equality semantics. |
| `checkstring` | `.String()` is only called inside `Test*_String` accessor tests — not as a shortcut for value comparison elsewhere. |

`checkmustnew` and `checkequality` accept `--exclude=Type1,Type2` for types that aren't value objects (aggregates, entities, types with non-comparable fields). The list is per-consumer config — every repo has its own aggregates.

### `actions/run-ddd-checks` — composite GitHub Action

Runs all three checkers against the caller's repo. Used from consumer workflows:

```yaml
- uses: chrisconley/go-ddd/actions/run-ddd-checks@v1
  with:
    mustnew-exclude: "Ledger,Transaction,Transfer"
    equality-exclude: "Ledger,Transaction,Transfer,BudgetRule"
```

## The conventions, briefly

This toolkit encodes three rules from a broader DDD approach for Go:

1. **Value objects get `MustNew*` helpers.** VOs are cheap to construct; tests should be able to write `MustNewCustomerID("cust-1")` inline without error-handling noise. Aggregates and entities are not VOs — they carry real construction risk and don't get `Must*` constructors.

2. **Every VO has explicit equality test coverage.** Equality is a load-bearing property of value objects; behavior changes (adding a field, changing comparability) should be caught by a `Test*_Equality` test that exists specifically to lock that behavior.

3. **`.String()` is for display, not for equality.** If you find yourself comparing `a.String() == b.String()`, you're doing value-object equality the wrong way. `.String()` belongs inside a `Test*_String` test that exercises stringification.

## Consumers

- [verocorp/certus](https://github.com/verocorp/certus) — reference implementation
- [chrisconley/metron](https://github.com/chrisconley/metron)
- [chrisconley/quanta](https://github.com/chrisconley/quanta)

## Status

This repo is new. The checkers were extracted from certus's `ci/` directory; porting them to the `go/analysis` framework (enabling `go vet -vettool`, `multichecker`, editor integration) is a follow-up.
