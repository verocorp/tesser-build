# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
Fixture coverage is a token-overlap heuristic over test assertion strings.

## sigcheck rules (from the violation messages in sigcheck/domain.py)

| Family | Message template | Source line | Fixture coverage |
|---|---|---|---|
| Codebase._constructor_violations | {…}.{…}:{…} defines no __init__; an aggregate constructs from exactly one ts.Spec | domain.py:136 | test_aggregate_constructor_violations_are_flagged |
| Codebase._signature_violations | {…} uses *args/**kwargs; {…} takes exactly one {…} | domain.py:180 | test_arity_and_missing_annotations_are_flagged |
| Codebase._signature_violations | {…} takes {…} parameters; {…} takes exactly one {…} | domain.py:182 | test_arity_and_missing_annotations_are_flagged, test_aggregate_constructor_violations_are_flagged |
| Codebase._signature_violations | {…} does not return a {…} | domain.py:187 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| Codebase._signature_violations | {…} parameter {…} is not a {…} | domain.py:185 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged, test_aggregate_constructor_violations_are_flagged |
| Codebase._delegation_violations | {…} delegates to self.{…} at line {…}; a service inlines its logic | domain.py:208 | test_service_delegation_is_flagged |
| Codebase._delegation_violations | {…} delegates to {…} at line {…}; a service inlines its logic | domain.py:210 | test_service_delegation_is_flagged |
| Codebase._body_violations | {…} body spans {…} source lines; a service method body is at most 10 | domain.py:219 | test_service_body_rules_are_flagged |
| Codebase._body_violations | {…} if condition at line {…} is not a single call; satisfy it with one domain call | domain.py:223 | test_service_body_rules_are_flagged |
| Codebase._body_violations | {…} nests a conditional at line {…}; a service method branches one level deep | domain.py:225 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| Codebase._body_violations | {…} match subject at line {…} is not a single call; satisfy it with one domain call | domain.py:228 | test_service_body_rules_are_flagged |
| Codebase._body_violations | {…} nests a conditional at line {…}; a service method branches one level deep | domain.py:230 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |

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
