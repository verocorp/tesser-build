# Real-code corroboration — the public-interface anchor

The committed synthetic arms (`contrast_test.go`, `substitution_test.go`) are the
CI-reproducible proof. They could be dismissed as authored-to-win. This note
corroborates the **migration-surface direction** on *real conforming code* — not a
fan-out fixture — using `../../measure-ablation.sh` + `git grep -w`, the same
real-code approach `docs/case-study.md` used for value objects (F7 in the design).

**Target:** `examples/running/` — a full link-campaign HTTP app a fresh agent
produced *from the skill alone* (the v3 acceptance gate). It uses the real
interface boundary: `linkcampaign` (the `Client` contract) with `linkcampaignimpl`
behind it and `transport` + `main` as consumers.

## Result

Renaming a type and counting the compiler-forced worklist across the module (the
whole-module build undercounts past the first failing package, so the
cross-package spread is taken with `git grep -w`, per the script's own note):

| Change | forced references | packages | consumers (`transport`/`main`) |
|---|---|---|---|
| **impl-internal type** `campaignRecord` (a storage row behind the boundary) | 7 | **1** (`linkcampaignimpl`) | **0 forced** |
| **public-contract type** `ShortLinkView` (a DTO the `Client` returns) | 9 | **2** (`linkcampaign` + the mapping service `campaignapp`) | 0 named directly |

**Reading it.** A change to a component-**internal** type is *contained* — 0
edits forced on the consumers of the public `Client`, exactly the decoupled arm's
`O(1)`/0. A change to the **contract** spreads across the boundary to more
packages — the cost the boundary cannot hide. The *direction* (internal contained,
contract spreads) holds on real code.

**Why the magnitude is small.** `examples/running` has ~1 consumer, so the real
numbers are 1 vs 2 packages, not 0 vs N. That is precisely why the synthetic
anchor scales N to 8 and 16 (`contrast_test.go`): to exhibit the `O(dependents)`
*growth* a small real app is too thin to show. Synthetic gives reproducibility and
scaling; real ablation answers "is the direction only true in a fixture." It is
not.

**Note.** This corroborates the C1 (migration / decoupling) claim — internal
changes stay behind the boundary. It does **not** settle the facade finding (a
facade also contains internal changes); that is what C2 (`substitution_test.go`)
is for. The interface's *distinct* win over a facade is substitutability, not
containment.

## Reproduce

```
# tree must be clean; the script mutates one file, counts, and reverts.

# impl-internal type — contained to the impl:
./rationale/measure-ablation.sh examples/running/linkcampaignimpl/memory_repo.go \
  's/type campaignRecord struct/type campaignRow struct/ if $.==19' ./examples/running/...
git grep -wl campaignRecord -- 'examples/running/**/*.go'   # -> 1 file, linkcampaignimpl only

# public-contract type — spreads across the boundary:
L=$(grep -n 'type ShortLinkView struct' examples/running/linkcampaign/client.go | cut -d: -f1)
./rationale/measure-ablation.sh examples/running/linkcampaign/client.go \
  "s/type ShortLinkView struct/type ShortLinkOut struct/ if \$.==$L" ./examples/running/...
git grep -wl ShortLinkView -- 'examples/running/**/*.go'    # -> 2 packages
```
