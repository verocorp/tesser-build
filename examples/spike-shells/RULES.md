# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## sigcheck rules (from the violation messages in sigcheck/domain.py)

| The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|
| an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain.py:136 | test_aggregate_constructor_violations_are_flagged |
| an aggregate constructor takes exactly one ts.Spec | aggregate `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain.py:180,182,185 | test_aggregate_constructor_violations_are_flagged |
| a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:180,182,185 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| a service method returns a ts.Response | public service method | does not return a ts.Response | domain.py:188 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ at line ⟨line⟩ · delegates to ⟨function⟩ at line ⟨line⟩ | domain.py:213,215 | test_service_delegation_is_flagged |
| a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain.py:224 | test_service_body_rules_are_flagged |
| a service method satisfies a condition with one domain call | public service method | if condition at line ⟨line⟩ is not a single call · match subject at line ⟨line⟩ is not a single call | domain.py:228,233 | test_service_body_rules_are_flagged |
| a service method branches one level deep | public service method | nests a conditional at line ⟨line⟩ | domain.py:230,235 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |

## Import contracts (from .importlinter)

| Contract | Rule |
|---|---|
| domain-imports-only-tesser-domain | domain imports only tesser.domain |
| client-imports-only-tesser-context | the client DTOs import only tesser.context |
| application-never-reaches-adapters | application imports domain and client, never an adapter |
| adapters-never-import-domain | an adapter imports parts from application, never domain or client |

Import contracts are verified by violation-injection runs during development;
no committed test re-runs them (named gap — cf. python-app's committed
architecture violation-injection test).
