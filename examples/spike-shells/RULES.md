# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## sigcheck rules (from the violation messages in sigcheck/domain.py)

| The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|
| a context holds only domain, application, client, adapters, and wiring modules | context package | is not a context module | domain.py:252 | test_non_context_module_and_nonempty_init_are_flagged |
| a context __init__ is empty | context `__init__` | __init__ declares code at line ⟨line⟩ | domain.py:260 | test_non_context_module_and_nonempty_init_are_flagged |
| an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain.py:323 | test_an_adapters_module_holds_one_kind |
| every context class declares its block | context role module | declares no ts.* base | domain.py:278 | test_placement_totality_is_flagged |
| a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩.py | domain.py:281 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| a module function declares itself with @ts.function | context role module | is an undeclared module function | domain.py:290 | test_placement_totality_is_flagged |
| a module constant is Final | context role module | declares a module constant without Final | domain.py:298,305 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain.py:312 | test_placement_totality_is_flagged |
| a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain.py:343 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain.py:369 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client |
| only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain.py:354 | test_only_a_handler_imports_its_own_client |
| the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain.py:361 | test_import_matrix_is_flagged |
| a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain.py:392 | test_srv_and_bootstrap_import_rows |
| the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain.py:406 | test_srv_and_bootstrap_import_rows |
| bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain.py:399 | test_srv_and_bootstrap_import_rows |
| a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain.py:429 | test_test_module_totality_is_flagged |
| a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain.py:446 | test_test_module_totality_is_flagged |
| a test double declares itself with @ts.fake | test module | is an undeclared class | domain.py:438 | test_test_module_totality_is_flagged |
| a fake implements the port it doubles | test module | implements no ts.Port | domain.py:442 | test_test_module_totality_is_flagged |
| a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain.py:465,477 | test_helper_rules_are_flagged |
| a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain.py:482 | test_helper_rules_are_flagged |
| a helper only constructs | @ts.helper function | has control flow at line ⟨line⟩ | domain.py:485 | test_helper_rules_are_flagged |
| a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain.py:524 | test_service_dependencies_must_be_ports |
| an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain.py:564 | test_records_never_carry_domain_objects |
| a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain.py:564 | test_records_never_carry_domain_objects |
| a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain.py:585 | test_domain_field_rules_are_flagged |
| a spec only carries construction data | spec class | defines a method on a spec | domain.py:605 | test_domain_field_rules_are_flagged |
| a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain.py:611 | test_domain_field_rules_are_flagged |
| a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain.py:630 | test_domain_field_rules_are_flagged |
| a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain.py:635 | test_domain_field_rules_are_flagged |
| an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain.py:652 | test_aggregate_constructor_violations_are_flagged |
| an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain.py:652 | test_domain_field_rules_are_flagged |
| a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain.py:692,694,697 | test_aggregate_constructor_violations_are_flagged |
| a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:692,694,697 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| a service method returns a ts.Response | public service method | does not return a ts.Response | domain.py:700 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:692,694,697 | test_client_method_rules_are_flagged |
| a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain.py:700 | test_client_method_rules_are_flagged |
| a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ at line ⟨line⟩ · delegates to ⟨function⟩ at line ⟨line⟩ | domain.py:725,727 | test_service_delegation_is_flagged |
| a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain.py:736 | test_service_body_rules_are_flagged |
| a service method satisfies a condition with one domain call | public service method | if condition at line ⟨line⟩ is not a single call · match subject at line ⟨line⟩ is not a single call | domain.py:740,745 | test_service_body_rules_are_flagged |
| a service method branches one level deep | public service method | nests a conditional at line ⟨line⟩ | domain.py:742,747 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |

## Import contracts (from .importlinter)

| Contract | Rule |
|---|---|
| domain-imports-only-tesser-domain | domain imports only tesser.domain |
| client-imports-only-tesser-context | the client DTOs import only tesser.context |
| application-never-reaches-adapters | application imports domain and client, never an adapter |
| adapters-never-import-domain | an adapter imports parts from application and foreign clients, never domain |

Import contracts are verified by violation-injection runs during development;
no committed test re-runs them (named gap — cf. python-app's committed
architecture violation-injection test).
