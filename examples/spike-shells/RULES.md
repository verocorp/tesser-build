# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## sigcheck rules (from the violation messages in sigcheck/domain/checks.py)

| The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|
| a context holds only domain, application, client, adapters, wiring, and tests modules | context package | is not a context module | domain/checks.py:518 | test_non_context_module_and_nonempty_init_are_flagged |
| a context tests package holds only test modules and conftest | context package | is neither a test module nor conftest | domain/checks.py:500 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| a role is a package, never a module | context package | is a role module | domain/checks.py:510 | test_a_role_must_be_a_package |
| a context __init__ is empty | context `__init__` | __init__ declares code at line ⟨line⟩ | domain/checks.py:526 | test_non_context_module_and_nonempty_init_are_flagged |
| a protocol __init__ is empty | protocol package `__init__` | __init__ declares code at line ⟨line⟩ | domain/checks.py:532 | test_a_protocol_init_is_empty |
| every module belongs to a context, srv, bootstrap, tests, or the protocol package | top-level module | belongs to no governed package | domain/checks.py:542 | test_homeless_modules_are_flagged |
| a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code at line ⟨line⟩ | domain/checks.py:551,558 | test_tests_package_totality_is_flagged |
| a context tests __init__ is empty | context tests `__init__` | __init__ declares code at line ⟨line⟩ | domain/checks.py:566 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code at line ⟨line⟩ · imports ⟨import⟩ | domain/checks.py:578,588 | test_role_init_only_reexports_its_own_role, test_relative_imports_resolve_against_the_package |
| a srv or bootstrap __init__ is empty | srv / bootstrap `__init__` | __init__ declares code at line ⟨line⟩ | domain/checks.py:598 | test_srv_and_bootstrap_tesser_form_modes |
| a bootstrap module imports tesser.context exactly once, as ts | bootstrap module | never imports tesser.context · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:625,631,637,643 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| a bootstrap module imports only tesser.context | bootstrap module | imports ⟨import⟩ | domain/checks.py:622 | test_srv_and_bootstrap_tesser_form_modes |
| a srv module imports tesser.srv exactly once, as ts | srv module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:625,631,637,643 | test_srv_and_bootstrap_tesser_form_modes |
| a srv module imports only tesser.srv | srv module | imports ⟨import⟩ | domain/checks.py:622 | test_srv_and_bootstrap_statement_totality |
| a protocol module imports tesser.srv exactly once, as ts | protocol module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:625,631,637,643 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| a protocol module imports only tesser.srv | protocol module | imports ⟨import⟩ | domain/checks.py:622 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:625,631,637,643 | test_role_module_tesser_import_is_exactly_once_as_ts, test_nested_imports_neither_classify_nor_satisfy_presence, test_srv_and_bootstrap_tesser_form_modes |
| a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain/checks.py:622 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| a test module imports only tesser.testing | test module | imports ⟨import⟩ | domain/checks.py:622 | test_test_module_tesser_import_rules |
| a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:625,631,637 | test_test_module_tesser_import_rules |
| a bootstrap function declares itself with @ts.function | bootstrap module | is an undeclared module function | domain/checks.py:659 | test_srv_and_bootstrap_statement_totality |
| a bootstrap constant is Final | bootstrap module | declares a module constant without Final | domain/checks.py:667,674 | test_srv_and_bootstrap_statement_totality |
| a bootstrap module holds only imports, declared functions, and Final constants | bootstrap module | has a loose module-level statement · is a class | domain/checks.py:681,703 | test_srv_and_bootstrap_statement_totality |
| a srv function declares itself with @ts.function | srv module | is an undeclared module function | domain/checks.py:659 | test_srv_and_bootstrap_statement_totality |
| a srv constant is Final | srv module | declares a module constant without Final | domain/checks.py:667,674 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| a srv module holds only imports, declared classes and functions, and Final constants | srv module | has a loose module-level statement | domain/checks.py:681 | test_srv_and_bootstrap_statement_totality |
| a protocol function declares itself with @ts.function | protocol module | is an undeclared module function | domain/checks.py:659 | test_protocol_module_totality_is_flagged |
| a protocol constant is Final | protocol module | declares a module constant without Final | domain/checks.py:667,674 | test_protocol_module_totality_is_flagged |
| a protocol module holds only imports, declared classes and functions, and Final constants | protocol module | has a loose module-level statement | domain/checks.py:681 | test_protocol_module_totality_is_flagged |
| a module function declares itself with @ts.function | context role module | is an undeclared module function | domain/checks.py:659 | test_placement_totality_is_flagged |
| a module constant is Final | context role module | declares a module constant without Final | domain/checks.py:667,674 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain/checks.py:681 | test_placement_totality_is_flagged |
| a srv class declares its block | srv module | declares no ts.* base | domain/checks.py:739 | test_srv_and_bootstrap_statement_totality |
| only a host class lives in a srv module | srv module | is ⟨kind⟩ | domain/checks.py:742 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| a protocol module is context-generic and imports no context | protocol module | imports ⟨import⟩ | domain/checks.py:777 | test_protocol_module_totality_is_flagged |
| a protocol module never imports srv or bootstrap | protocol module | imports ⟨import⟩ | domain/checks.py:784 | test_protocol_module_totality_is_flagged |
| a protocol class declares its block | protocol module | declares no ts.* base | domain/checks.py:794 | test_protocol_module_totality_is_flagged |
| only protocol ports, protocol records, protocol rejections, protocol requests, and protocol responses live in a protocol module | protocol module | is ⟨kind⟩ | domain/checks.py:797 | test_protocol_module_totality_is_flagged |
| an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain/checks.py:851 | test_an_adapters_module_holds_one_kind |
| every context class declares its block | context role module | declares no ts.* base | domain/checks.py:823 | test_placement_totality_is_flagged |
| a host lives in srv and a protocol kind in a protocol module, never a context | context role module | is ⟨kind⟩ | domain/checks.py:826 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩.py | domain/checks.py:833 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| domain, client, and application import only their context, their tesser package, and the pure stdlib | context role module | imports ⟨import⟩ | domain/checks.py:919 | test_pure_core_stdlib_allowlist, test_nested_imports_neither_classify_nor_satisfy_presence, test_pure_core_allowlist_covers_application_and_domain_future |
| a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain/checks.py:905 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |
| only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain/checks.py:890 | test_only_a_handler_imports_its_own_client |
| the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain/checks.py:897 | test_import_matrix_is_flagged |
| a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:945 | test_srv_and_bootstrap_import_rows |
| the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:962 | test_srv_and_bootstrap_import_rows |
| bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:952 | test_srv_and_bootstrap_import_rows |
| a test reaches only what its placement allows | test module, by where it is placed | imports ⟨import⟩, but a test placed in srv reaches a context only through its handlers · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of its own context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches no neighbouring context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of a neighbouring context | domain/checks.py:1013,1043,1051,1059 | test_a_handler_sibling_fakes_only_the_client, test_a_srv_test_reaches_a_context_only_through_its_handlers, test_a_test_reaches_only_what_its_placement_allows |
| an eval lives only in a gateway, the one place a sampled real-model call is honest | eval module (`eval_*.py`) | is an eval outside a gateway | domain/checks.py:1094 | test_an_eval_lives_only_in_a_gateway |
| a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain/checks.py:1140 | test_test_module_totality_is_flagged |
| a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain/checks.py:1163 | test_test_module_totality_is_flagged |
| a test double declares itself with @ts.fake | test module | is an undeclared class | domain/checks.py:1149 | test_test_module_totality_is_flagged |
| a fake implements the port or client it doubles | test module | implements no application port, protocol port, or client | domain/checks.py:1156 | test_test_module_totality_is_flagged, test_a_dotted_module_base_resolves |
| a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain/checks.py:1182,1194 | test_helper_rules_are_flagged |
| a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain/checks.py:1199 | test_helper_rules_are_flagged |
| a helper only constructs | @ts.helper function | has control flow at line ⟨line⟩ | domain/checks.py:1202 | test_helper_rules_are_flagged |
| a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain/checks.py:1241 | test_service_dependencies_must_be_ports |
| an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain/checks.py:1281 | test_records_never_carry_domain_objects, test_relative_imports_resolve_against_the_package |
| a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain/checks.py:1281 | test_records_never_carry_domain_objects |
| a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain/checks.py:1302 | test_domain_field_rules_are_flagged |
| a spec only carries construction data | spec class | defines a method on a spec | domain/checks.py:1322 | test_domain_field_rules_are_flagged |
| a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain/checks.py:1328 | test_domain_field_rules_are_flagged |
| a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain/checks.py:1347 | test_domain_field_rules_are_flagged |
| a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain/checks.py:1352 | test_domain_field_rules_are_flagged |
| an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain/checks.py:1369 | test_aggregate_constructor_violations_are_flagged |
| an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain/checks.py:1369 | test_domain_field_rules_are_flagged |
| a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain/checks.py:1417,1419,1422 | test_aggregate_constructor_violations_are_flagged |
| a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:1417,1419,1422 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| a service method returns a ts.Response | public service method | does not return a ts.Response | domain/checks.py:1425 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:1417,1419,1422 | test_client_method_rules_are_flagged |
| a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain/checks.py:1425 | test_client_method_rules_are_flagged |
| a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ at line ⟨line⟩ · delegates to ⟨function⟩ at line ⟨line⟩ | domain/checks.py:1451,1453 | test_service_delegation_is_flagged |
| a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain/checks.py:1462 | test_service_body_rules_are_flagged |
| a service method satisfies a condition with one domain call | public service method | if condition at line ⟨line⟩ is not a single call · match subject at line ⟨line⟩ is not a single call | domain/checks.py:1466,1471 | test_service_body_rules_are_flagged |
| a service method branches one level deep | public service method | nests a conditional at line ⟨line⟩ | domain/checks.py:1468,1473 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| a tesser import is module-level | role, srv/bootstrap, or test module | imports ⟨import⟩ inside a function | domain/checks.py:1520 | test_nested_imports_neither_classify_nor_satisfy_presence, test_protocol_module_totality_is_flagged |
| a relative import resolves inside the tree | role, srv/bootstrap, or test module | imports ⟨import⟩ beyond the package root | domain/checks.py:1527 | test_relative_imports_resolve_against_the_package |
| a context module is imported as an aliased module, never its members | direction-legal context import (role modules and their __init__, srv/bootstrap, test modules) | imports names from ⟨import⟩ · imports ⟨import⟩ without an alias | domain/checks.py:1540,1547 | test_role_init_only_reexports_its_own_role, test_a_role_init_may_import_a_module_but_never_a_class, test_context_module_import_form, test_relative_imports_resolve_against_the_package, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |

## Named exemptions (carve-outs the code makes on purpose, not rules)

- a `conftest` module is ungoverned (kept for now — followup pending with
  the test-organization work).
- a context `__main__` is ungoverned (named ruling, PR #48).
- tooling modules outside the taxonomy: `rules` (TOOLING_MODULES in
  sigcheck/domain/checks.py — the whole-tree totality rule skips them).
- modules under the top-level `protocol/` package are the protocol
  modules (PROTOCOL_PACKAGE in sigcheck/domain/checks.py) — package membership
  is the declaration; no suffix opts a module in, so a stray `*wire.py`
  is homeless.
- srv and protocol kinds carry placement and import rules only — no
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
