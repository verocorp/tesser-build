# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## sigcheck rules (from the violation messages in sigcheck/domain.py)

| The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|
| a context holds only domain, application, client, adapters, and wiring modules | context package | is not a context module | domain.py:349 | test_non_context_module_and_nonempty_init_are_flagged |
| a context __init__ is empty | context `__init__` | __init__ declares code at line ⟨line⟩ | domain.py:357 | test_non_context_module_and_nonempty_init_are_flagged |
| every module belongs to a context, srv, bootstrap, tests, or a wire module | top-level module | belongs to no governed package | domain.py:365 | test_homeless_modules_are_flagged |
| a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code at line ⟨line⟩ | domain.py:374,381 | test_tests_package_totality_is_flagged |
| a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code at line ⟨line⟩ · imports ⟨import⟩ | domain.py:392,400 | test_role_init_only_reexports_its_own_role, test_relative_imports_resolve_against_the_package |
| a srv or bootstrap __init__ is empty | srv / bootstrap `__init__` | __init__ declares code at line ⟨line⟩ | domain.py:409 | test_srv_and_bootstrap_tesser_form_modes |
| a bootstrap module imports tesser.context exactly once, as ts | bootstrap module | never imports tesser.context · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:436,445,452,459 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| a bootstrap module imports only tesser.context | bootstrap module | imports ⟨import⟩ | domain.py:429 | test_srv_and_bootstrap_tesser_form_modes |
| a srv module imports tesser.srv exactly once, as ts | srv module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:436,445,452,459 | test_srv_and_bootstrap_tesser_form_modes |
| a srv module imports only tesser.srv | srv module | imports ⟨import⟩ | domain.py:429 | test_srv_and_bootstrap_statement_totality |
| a wire module imports tesser.srv exactly once, as ts | wire module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:436,445,452,459 | test_wire_module_tesser_import_is_exactly_once_as_ts |
| a wire module imports only tesser.srv | wire module | imports ⟨import⟩ | domain.py:429 | test_wire_module_tesser_import_is_exactly_once_as_ts |
| a bootstrap function declares itself with @ts.function | bootstrap module | is an undeclared module function | domain.py:476 | test_srv_and_bootstrap_statement_totality |
| a bootstrap module holds only imports, declared functions, and Final constants | bootstrap module | is a class · has a loose module-level statement | domain.py:483,505 | test_srv_and_bootstrap_statement_totality |
| a bootstrap constant is Final | bootstrap module | declares a module constant without Final | domain.py:491,498 | test_srv_and_bootstrap_statement_totality |
| a srv class declares its block | srv module | declares no ts.* base | domain.py:527 | test_srv_and_bootstrap_statement_totality |
| only a host class lives in a srv module | srv module | is ⟨kind⟩ | domain.py:530 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| a srv function declares itself with @ts.function | srv module | is an undeclared module function | domain.py:535 | test_srv_and_bootstrap_statement_totality |
| a srv constant is Final | srv module | declares a module constant without Final | domain.py:543,550 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| a srv module holds only imports, declared classes and functions, and Final constants | srv module | has a loose module-level statement | domain.py:557 | test_srv_and_bootstrap_statement_totality |
| a wire module is context-generic and imports no context | wire module | imports ⟨import⟩ | domain.py:577 | test_wire_module_totality_is_flagged |
| a wire module never imports srv or bootstrap | wire module | imports ⟨import⟩ | domain.py:584 | test_wire_module_totality_is_flagged |
| a wire class declares its block | wire module | declares no ts.* base | domain.py:596 | test_wire_module_totality_is_flagged |
| only wire ports, wire records, wire requests, and wire responses live in a wire module | wire module | is ⟨kind⟩ | domain.py:599 | test_wire_module_totality_is_flagged |
| a wire function declares itself with @ts.function | wire module | is an undeclared module function | domain.py:607 | test_wire_module_totality_is_flagged |
| a wire constant is Final | wire module | declares a module constant without Final | domain.py:615,622 | test_wire_module_totality_is_flagged |
| a wire module holds only imports, declared classes and functions, and Final constants | wire module | has a loose module-level statement | domain.py:629 | test_wire_module_totality_is_flagged |
| an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain.py:702 | test_an_adapters_module_holds_one_kind |
| every context class declares its block | context role module | declares no ts.* base | domain.py:650 | test_placement_totality_is_flagged |
| a host lives in srv and a wire kind in a wire module, never a context | context role module | is ⟨kind⟩ | domain.py:653 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| a module function declares itself with @ts.function | context role module | is an undeclared module function | domain.py:669 | test_placement_totality_is_flagged |
| a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩.py | domain.py:660 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| a module constant is Final | context role module | declares a module constant without Final | domain.py:677,684 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain.py:691 | test_placement_totality_is_flagged |
| a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:732,741,748,755 | test_role_module_tesser_import_is_exactly_once_as_ts, test_nested_imports_neither_classify_nor_satisfy_presence, test_srv_and_bootstrap_tesser_form_modes |
| a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain.py:725 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| domain, client, and application import only their context, their tesser package, and the pure stdlib | context role module | imports ⟨import⟩ | domain.py:799 | test_pure_core_stdlib_allowlist, test_nested_imports_neither_classify_nor_satisfy_presence, test_pure_core_allowlist_covers_application_and_domain_future |
| a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain.py:786 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |
| only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain.py:771 | test_only_a_handler_imports_its_own_client |
| the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain.py:778 | test_import_matrix_is_flagged |
| a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain.py:823 | test_srv_and_bootstrap_import_rows |
| the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain.py:839 | test_srv_and_bootstrap_import_rows |
| bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain.py:830 | test_srv_and_bootstrap_import_rows |
| a test module imports only tesser.testing | test module | imports ⟨import⟩ | domain.py:860 | test_test_module_tesser_import_rules |
| a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain.py:898 | test_test_module_totality_is_flagged |
| a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain.py:866,875,882 | test_test_module_tesser_import_rules |
| a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain.py:921 | test_test_module_totality_is_flagged |
| a test double declares itself with @ts.fake | test module | is an undeclared class | domain.py:907 | test_test_module_totality_is_flagged |
| a fake implements the port or client it doubles | test module | implements no application port, wire port, or client | domain.py:914 | test_test_module_totality_is_flagged, test_a_dotted_module_base_resolves |
| a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain.py:940,952 | test_helper_rules_are_flagged |
| a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain.py:957 | test_helper_rules_are_flagged |
| a helper only constructs | @ts.helper function | has control flow at line ⟨line⟩ | domain.py:960 | test_helper_rules_are_flagged |
| a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain.py:999 | test_service_dependencies_must_be_ports |
| an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain.py:1039 | test_records_never_carry_domain_objects, test_relative_imports_resolve_against_the_package |
| a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain.py:1039 | test_records_never_carry_domain_objects |
| a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain.py:1060 | test_domain_field_rules_are_flagged |
| a spec only carries construction data | spec class | defines a method on a spec | domain.py:1080 | test_domain_field_rules_are_flagged |
| a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain.py:1086 | test_domain_field_rules_are_flagged |
| a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain.py:1105 | test_domain_field_rules_are_flagged |
| a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain.py:1110 | test_domain_field_rules_are_flagged |
| an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain.py:1127 | test_aggregate_constructor_violations_are_flagged |
| an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain.py:1127 | test_domain_field_rules_are_flagged |
| a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain.py:1167,1169,1172 | test_aggregate_constructor_violations_are_flagged |
| a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:1167,1169,1172 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| a service method returns a ts.Response | public service method | does not return a ts.Response | domain.py:1175 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain.py:1167,1169,1172 | test_client_method_rules_are_flagged |
| a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain.py:1175 | test_client_method_rules_are_flagged |
| a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ at line ⟨line⟩ · delegates to ⟨function⟩ at line ⟨line⟩ | domain.py:1200,1202 | test_service_delegation_is_flagged |
| a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain.py:1211 | test_service_body_rules_are_flagged |
| a service method satisfies a condition with one domain call | public service method | if condition at line ⟨line⟩ is not a single call · match subject at line ⟨line⟩ is not a single call | domain.py:1215,1220 | test_service_body_rules_are_flagged |
| a service method branches one level deep | public service method | nests a conditional at line ⟨line⟩ | domain.py:1217,1222 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| a tesser import is module-level | role, srv/bootstrap, or test module | imports ⟨import⟩ inside a function | domain.py:1269 | test_nested_imports_neither_classify_nor_satisfy_presence, test_wire_module_totality_is_flagged |
| a relative import resolves inside the tree | role, srv/bootstrap, or test module | imports ⟨import⟩ beyond the package root | domain.py:1276 | test_relative_imports_resolve_against_the_package |
| a context module is imported as an aliased module, never its members | direction-legal context import (role, srv/bootstrap, test modules) | imports names from ⟨import⟩ · imports ⟨import⟩ without an alias | domain.py:1293,1300 | test_context_module_import_form, test_relative_imports_resolve_against_the_package, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |

## Named exemptions (carve-outs the code makes on purpose, not rules)

- a `conftest` module is ungoverned (kept for now — followup pending with
  the test-organization work).
- a context `__main__` is ungoverned (named ruling, PR #48).
- tooling modules outside the taxonomy: `rules` (TOOLING_MODULES in
  sigcheck/domain.py — the whole-tree totality rule skips them).
- a top-level module whose name ends in `wire` is a wire module
  (WIRE_SUFFIX in sigcheck/domain.py) — the name is the declaration,
  the `test_*` precedent; a package or nested module never qualifies.
- srv and wire kinds carry placement and import rules only — no
  signature or body rules yet (deliberate: the srv signature matrix
  ruled the kinds and their invariants, not sigcheck rules over
  their members — see TODOS.md).

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
