# `run-ddd-checks` — composite GitHub Action

Runs the go-ddd value-object convention analyzers (`ddd-vet`) against the calling
repo. It builds `ddd-vet` from this repo, then runs it as a `go vet` tool over the
caller's packages (`go vet -vettool=ddd-vet ./...`). Each analyzer reports a
diagnostic per violation; `go vet` exits non-zero if any analyzer fires.

The analyzers it runs (see the repo root [`README.md`](../../README.md) and
[`docs/design-ddd-vet-migration.md`](../../docs/design-ddd-vet-migration.md) for
the full set): `mustnew`, `stringequality`, `vofields`, `voconstructor`,
`stringer`, `primitiveaccessor`, `comparability`.

## Usage

```yaml
- uses: verocorp/go-ddd/actions/run-ddd-checks@v1
```

No inputs. Configuration is file-only.

## Configuration — `.go-ddd.yaml`

Put a `.go-ddd.yaml` at your repo root listing the types every analyzer should
**skip** — the aggregates and entities that match the value-object heuristic
(`NewX(...) (X, error)`) but are not value objects:

```yaml
exclude:
  - Ledger       # has ID() method            (entity)
  - Transaction  # field: id TransactionID    (entity)
  - Transfer     # mutated by (*Transfer).Apply()  (aggregate)
```

Generate a starter list (then review and edit — each exclusion is a domain call,
not a guess to rubber-stamp):

```sh
go run github.com/chrisconley/go-ddd/cmd/ddd-vet -gen-excludes ./...
```

There are no `mustnew-exclude` / `equality-exclude` Action inputs. There is one
way to configure the checks — the file — not two. (Consumers that used the old
inputs move their lists into `.go-ddd.yaml`.)

## Two consequences worth knowing

**Your packages must compile.** The analyzers are type-aware (they run under
`go vet`, which type-checks first), unlike the old text-only directory walkers. If
your repo has an *unrelated* build error — a typo, a missing import — this check
goes red too, and the message may point at the build failure rather than a DDD
violation. This is an accepted trade for the type-aware checks; it is not a bug in
the Action. For real modules that already build in CI it is a non-event.

**The check runs with a cold cache.** The Action points `GOCACHE` at a scratch
directory for the vet step so that editing `.go-ddd.yaml` (with no code change)
always takes effect. `go/analysis` does not track the config file as a cache
input, so a warm cache could otherwise return stale results. The cost is a
cold analysis cache on every run; the principled fix (pass excludes as analyzer
flags, which *are* part of `go vet`'s cache key) is parked in the design doc.
