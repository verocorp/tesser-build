# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## sigcheck rules (from the violation messages in sigcheck/domain.py)

| The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|
| a context holds only domain, application, client, adapters, and wiring modules | context package | is not a context module | domain.py:268 | test_non_context_module_and_nonempty_init_are_flagged |
| a context __init__ is empty | context `__init__` | __init__ declares code at line ⟨line⟩ | domain.py:276 | test_non_context_module_and_nonempty_init_are_flagged |
| every module belongs to a context, srv, bootstrap, or tests | top-level module | belongs to no governed package | domain.py:284 | test_homeless_modules_are_flagged |
| a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code at line ⟨line⟩ | domain.py:293,300 | test_tests_package_totality_is_flagged |
| a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code at line ⟨line⟩ · imports ⟨import⟩ | domain.py:311,319 | test_role_init_only_reexports_its_own_role |
| a srv or bootstrap module imports tesser.context exactly once, as ts | srv / bootstrap module | never imports tesser.context · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:339,348,355,362 | test_srv_and_bootstrap_statement_totality |
| a srv or bootstrap module imports only tesser.context | srv / bootstrap module | imports ⟨import⟩ | domain.py:332 | test_srv_and_bootstrap_statement_totality |
| a srv or bootstrap function declares itself with @ts.function | srv / bootstrap module | is an undeclared module function | domain.py:373 | test_srv_and_bootstrap_statement_totality |
| a srv or bootstrap module holds only imports, declared functions, and Final constants | srv / bootstrap module | is a class · has a loose module-level statement | domain.py:380,402 | test_srv_and_bootstrap_statement_totality |
| a srv or bootstrap constant is Final | srv / bootstrap module | declares a module constant without Final | domain.py:388,395 | test_srv_and_bootstrap_statement_totality |
| an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain.py:468 | test_an_adapters_module_holds_one_kind |
| every context class declares its block | context role module | declares no ts.* base | domain.py:423 | test_placement_totality_is_flagged |
| a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩.py | domain.py:426 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| a module function declares itself with @ts.function | context role module | is an undeclared module function | domain.py:435 | test_placement_totality_is_flagged |
| a module constant is Final | context role module | declares a module constant without Final | domain.py:443,450 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain.py:457 | test_placement_totality_is_flagged |
| a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:495,504,511,518 | test_role_module_tesser_import_is_exactly_once_as_ts |
| a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain.py:488 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain.py:548 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client |
| only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain.py:533 | test_only_a_handler_imports_its_own_client |
| the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain.py:540 | test_import_matrix_is_flagged |
| a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain.py:571 | test_srv_and_bootstrap_import_rows |
| the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain.py:585 | test_srv_and_bootstrap_import_rows |
| bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain.py:578 | test_srv_and_bootstrap_import_rows |
| a test module imports only tesser.testing | test module | imports ⟨import⟩ | domain.py:602 | test_test_module_tesser_import_rules |
| a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain.py:640 | test_test_module_totality_is_flagged |
| a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:608,617,624 | test_test_module_tesser_import_rules |
| a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain.py:657 | test_test_module_totality_is_flagged |
| a test double declares itself with @ts.fake | test module | is an undeclared class | domain.py:649 | test_test_module_totality_is_flagged |
| a fake implements the port it doubles | test module | implements no ts.Port | domain.py:653 | test_test_module_totality_is_flagged |
| a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain.py:676,688 | test_helper_rules_are_flagged |
| a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain.py:693 | test_helper_rules_are_flagged |
| a helper only constructs | @ts.helper function | has control flow at line ⟨line⟩ | domain.py:696 | test_helper_rules_are_flagged |
| a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain.py:735 | test_service_dependencies_must_be_ports |
| an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain.py:775 | test_records_never_carry_domain_objects |
| a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain.py:775 | test_records_never_carry_domain_objects |
| a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain.py:796 | test_domain_field_rules_are_flagged |
| a spec only carries construction data | spec class | defines a method on a spec | domain.py:816 | test_domain_field_rules_are_flagged |
| a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain.py:822 | test_domain_field_rules_are_flagged |
| a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain.py:841 | test_domain_field_rules_are_flagged |
| a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain.py:846 | test_domain_field_rules_are_flagged |
| an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain.py:863 | test_aggregate_constructor_violations_are_flagged |
| an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain.py:863 | test_domain_field_rules_are_flagged |
| a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain.py:903,905,908 | test_aggregate_constructor_violations_are_flagged |
| a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:903,905,908 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| a service method returns a ts.Response | public service method | does not return a ts.Response | domain.py:911 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:903,905,908 | test_client_method_rules_are_flagged |
| a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain.py:911 | test_client_method_rules_are_flagged |
| a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ at line ⟨line⟩ · delegates to ⟨function⟩ at line ⟨line⟩ | domain.py:936,938 | test_service_delegation_is_flagged |
| a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain.py:947 | test_service_body_rules_are_flagged |
| a service method satisfies a condition with one domain call | public service method | if condition at line ⟨line⟩ is not a single call · match subject at line ⟨line⟩ is not a single call | domain.py:951,956 | test_service_body_rules_are_flagged |
| a service method branches one level deep | public service method | nests a conditional at line ⟨line⟩ | domain.py:953,958 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |

## Named exemptions (carve-outs the code makes on purpose, not rules)

- a `conftest` module is ungoverned (kept for now — followup pending with
  the test-organization work).
- a context `__main__` is ungoverned (named ruling, PR #48).
- tooling modules outside the taxonomy: `rules` (TOOLING_MODULES in
  sigcheck/domain.py — the whole-tree totality rule skips them).

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
