# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## sigcheck rules (from the violation messages in sigcheck/domain/checks.py)

| Code | The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|---|
| TB043 | a module has one definition | checked source file | is also defined by ⟨paths⟩ | domain/checks.py:552 | test_a_colliding_module_definition_is_a_finding_not_a_crash, test_a_colliding_unparseable_file_reports_the_collision |
| TB043 | every checked module is readable UTF-8 Python | checked source file | could not be read as UTF-8 text | domain/checks.py:562 | test_a_non_utf8_file_is_a_finding_not_a_crash |
| TB043 | every checked module parses | checked source file | does not parse (⟨error⟩) | domain/checks.py:577 | test_an_unparseable_module_is_a_finding_not_a_crash, test_reader_findings_are_never_inline_suppressible, test_a_colliding_unparseable_file_reports_the_collision |
| TB090 | an ignore comment suppresses an actual finding | ignore comment | carries an ignore that suppresses nothing | domain/checks.py:608 | test_a_scoped_ignore_leaves_other_codes_alone, test_a_stale_ignore_is_itself_a_finding, test_tb090_itself_cannot_be_ignored |
| TB041 | a context holds only domain, application, client, adapters, wiring, and tests modules | context package | is not a context module | domain/checks.py:719 | test_non_context_module_and_nonempty_init_are_flagged |
| TB041 | a context tests package holds only test modules and conftest | context package | is neither a test module nor conftest | domain/checks.py:695 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB041 | a role is a package, never a module | context package | is a role module | domain/checks.py:708 | test_a_role_must_be_a_package |
| TB042 | a context __init__ is empty | context `__init__` | __init__ declares code | domain/checks.py:730 | test_non_context_module_and_nonempty_init_are_flagged |
| TB042 | a protocol __init__ is empty | protocol package `__init__` | __init__ declares code | domain/checks.py:741 | test_a_protocol_init_is_empty |
| TB040 | every module belongs to a context, srv, bootstrap, tests, or the protocol package | top-level module | belongs to no governed package | domain/checks.py:754 | test_homeless_modules_are_flagged |
| TB041 | a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code | domain/checks.py:766,776 | test_tests_package_totality_is_flagged |
| TB042 | a context tests __init__ is empty | context tests `__init__` | __init__ declares code | domain/checks.py:787 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB042 | a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code · imports ⟨import⟩ | domain/checks.py:801,814 | test_role_init_only_reexports_its_own_role, test_relative_imports_resolve_against_the_package |
| TB042 | a srv or bootstrap __init__ is empty | srv / bootstrap `__init__` | __init__ declares code | domain/checks.py:827 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a bootstrap module imports tesser.context exactly once, as ts | bootstrap module | never imports tesser.context · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:863,874,883,892 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a bootstrap module imports only tesser.context | bootstrap module | imports ⟨import⟩ | domain/checks.py:854 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a srv module imports tesser.srv exactly once, as ts | srv module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:863,874,883,892 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a srv module imports only tesser.srv | srv module | imports ⟨import⟩ | domain/checks.py:854 | test_srv_and_bootstrap_statement_totality |
| TB050 | a protocol module imports tesser.srv exactly once, as ts | protocol module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:863,874,883,892 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a protocol module imports only tesser.srv | protocol module | imports ⟨import⟩ | domain/checks.py:854 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:863,874,883,892 | test_role_module_tesser_import_is_exactly_once_as_ts, test_nested_imports_neither_classify_nor_satisfy_presence, test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain/checks.py:854 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| TB050 | a test module imports only tesser.testing | test module | imports ⟨import⟩ | domain/checks.py:854 | test_test_module_tesser_import_rules |
| TB050 | a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:863,874,883 | test_test_module_tesser_import_rules |
| TB051 | a bootstrap function declares itself with @ts.function | bootstrap module | is an undeclared module function | domain/checks.py:914 | test_srv_and_bootstrap_statement_totality |
| TB051 | a bootstrap constant is Final | bootstrap module | declares a module constant without Final | domain/checks.py:925,935 | test_srv_and_bootstrap_statement_totality |
| TB051 | a bootstrap module holds only imports, declared functions, and Final constants | bootstrap module | has a loose module-level statement · is a class | domain/checks.py:945,1293 | test_srv_and_bootstrap_statement_totality |
| TB051 | a srv function declares itself with @ts.function | srv module | is an undeclared module function | domain/checks.py:914 | test_srv_and_bootstrap_statement_totality |
| TB051 | a srv constant is Final | srv module | declares a module constant without Final | domain/checks.py:925,935 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| TB051 | a srv module holds only imports, declared classes and functions, and Final constants | srv module | has a loose module-level statement | domain/checks.py:945 | test_srv_and_bootstrap_statement_totality |
| TB051 | a protocol function declares itself with @ts.function | protocol module | is an undeclared module function | domain/checks.py:914 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol constant is Final | protocol module | declares a module constant without Final | domain/checks.py:925,935 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol module holds only imports, declared classes and functions, and Final constants | protocol module | has a loose module-level statement | domain/checks.py:945 | test_protocol_module_totality_is_flagged |
| TB051 | a module function declares itself with @ts.function | context role module | is an undeclared module function | domain/checks.py:914 | test_placement_totality_is_flagged |
| TB051 | a module constant is Final | context role module | declares a module constant without Final | domain/checks.py:925,935 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| TB051 | a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain/checks.py:945 | test_placement_totality_is_flagged |
| TB020 | code speaks for itself — comments, docstrings, and loose strings belong in the doc layer | every module (tooling exempt) | carries a code comment · carries ⟨kind⟩ | domain/checks.py:972,995 | test_comments_docstrings_and_bare_strings_are_flagged |
| TB030 | a test double is a hand-written fake, never a mocking library or a runtime patcher | every module (tooling exempt) | imports a mocking library · reaches for pytest MonkeyPatch · takes the ⟨name⟩ fixture | domain/checks.py:1015,1027,1038,1053,1067,1082 | test_mocking_library_and_patcher_fixtures_are_flagged |
| TB033 | a shadowed builtin is never called — rename the binding | every module (tooling exempt) | binds ⟨builtin⟩ and calls it in the same scope | domain/checks.py:1116 | test_a_called_shadowed_builtin_is_flagged |
| TB004 | compare value objects by value, never by their string form | every module (tooling exempt) | equates two str() calls | domain/checks.py:1138 | test_string_form_equality_is_flagged |
| TB002 | a value object's field is hashable — a tuple or frozenset, never a mutable collection | value object class | field ⟨field⟩ is a mutable collection | domain/checks.py:1156 | test_a_value_object_mutable_collection_field_is_flagged |
| TB052 | a srv class declares its block | srv module | declares no ts.* base | domain/checks.py:1333 | test_srv_and_bootstrap_statement_totality |
| TB052 | only a host class lives in a srv module | srv module | is ⟨kind⟩ | domain/checks.py:1342 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB064 | a protocol module is context-generic and imports no context | protocol module | imports ⟨import⟩ | domain/checks.py:1382 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module never imports srv or bootstrap | protocol module | imports ⟨import⟩ | domain/checks.py:1392 | test_protocol_module_totality_is_flagged |
| TB052 | a protocol class declares its block | protocol module | declares no ts.* base | domain/checks.py:1406 | test_protocol_module_totality_is_flagged |
| TB052 | only protocol ports, protocol records, protocol rejections, protocol requests, and protocol responses live in a protocol module | protocol module | is ⟨kind⟩ | domain/checks.py:1415 | test_protocol_module_totality_is_flagged |
| TB052 | an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain/checks.py:1485 | test_an_adapters_module_holds_one_kind |
| TB052 | every context class declares its block | context role module | declares no ts.* base | domain/checks.py:1445 | test_placement_totality_is_flagged |
| TB052 | a host lives in srv and a protocol kind in a protocol module, never a context | context role module | is ⟨kind⟩ | domain/checks.py:1454 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB052 | a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩.py | domain/checks.py:1464 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| TB062 | domain, client, and application import only their context, their tesser package, and the pure stdlib | context role module | imports ⟨import⟩ | domain/checks.py:1567 | test_pure_core_stdlib_allowlist, test_nested_imports_neither_classify_nor_satisfy_presence, test_pure_core_allowlist_covers_application_and_domain_future |
| TB061 | a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain/checks.py:1550 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |
| TB060 | only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain/checks.py:1529 | test_only_a_handler_imports_its_own_client |
| TB060 | the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain/checks.py:1539 | test_import_matrix_is_flagged |
| TB063 | a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:1596 | test_srv_and_bootstrap_import_rows, test_a_denied_app_edge_is_not_form_checked |
| TB063 | the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:1619 | test_srv_and_bootstrap_import_rows |
| TB063 | bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:1606 | test_srv_and_bootstrap_import_rows |
| TB070 | a test reaches only what its placement allows | test module, by where it is placed | imports ⟨import⟩, but a test placed in srv reaches a context only through its handlers · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of its own context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches no neighbouring context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of a neighbouring context | domain/checks.py:1663,1696,1707,1718 | test_a_handler_sibling_fakes_only_the_client, test_a_srv_test_reaches_a_context_only_through_its_handlers, test_a_test_reaches_only_what_its_placement_allows |
| TB070 | an eval lives only in a gateway, the one place a sampled real-model call is honest | eval module (`eval_*.py`) | is an eval outside a gateway | domain/checks.py:1744 | test_an_eval_lives_only_in_a_gateway |
| TB071 | a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain/checks.py:1790 | test_test_module_totality_is_flagged |
| TB071 | a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain/checks.py:1824 | test_test_module_totality_is_flagged |
| TB072 | a test double declares itself with @ts.fake | test module | is an undeclared class | domain/checks.py:1802 | test_test_module_totality_is_flagged |
| TB072 | a fake implements the port or client it doubles | test module | implements no application port, protocol port, or client | domain/checks.py:1814 | test_test_module_totality_is_flagged, test_a_dotted_module_base_resolves |
| TB073 | a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain/checks.py:1847,1862 | test_helper_rules_are_flagged |
| TB073 | a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain/checks.py:1872 | test_helper_rules_are_flagged |
| TB073 | a helper only constructs | @ts.helper function | has control flow | domain/checks.py:1882 | test_helper_rules_are_flagged |
| TB081 | a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain/checks.py:1930 | test_service_dependencies_must_be_ports |
| TB081 | an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain/checks.py:1978 | test_records_never_carry_domain_objects, test_relative_imports_resolve_against_the_package |
| TB081 | a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain/checks.py:1978 | test_records_never_carry_domain_objects |
| TB080 | a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain/checks.py:2002 | test_domain_field_rules_are_flagged |
| TB080 | a spec only carries construction data | spec class | defines a method on a spec | domain/checks.py:2025 | test_domain_field_rules_are_flagged |
| TB080 | a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain/checks.py:2036 | test_domain_field_rules_are_flagged, test_optional_construction_data_is_the_only_union |
| TB080 | a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain/checks.py:2059 | test_domain_field_rules_are_flagged |
| TB080 | a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain/checks.py:2070 | test_domain_field_rules_are_flagged |
| TB080 | an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain/checks.py:2090 | test_aggregate_constructor_violations_are_flagged |
| TB080 | an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain/checks.py:2090 | test_domain_field_rules_are_flagged |
| TB080 | a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain/checks.py:2146,2155,2165 | test_aggregate_constructor_violations_are_flagged |
| TB081 | a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:2146,2155,2165 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| TB081 | a service method returns a ts.Response | public service method | does not return a ts.Response | domain/checks.py:2175 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| TB081 | a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:2146,2155,2165 | test_client_method_rules_are_flagged |
| TB081 | a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain/checks.py:2175 | test_client_method_rules_are_flagged |
| TB082 | a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ · delegates to ⟨function⟩ | domain/checks.py:2205,2214 | test_service_delegation_is_flagged |
| TB082 | a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain/checks.py:2230 | test_service_body_rules_are_flagged |
| TB082 | a service method satisfies a condition with one domain call | public service method | if condition is not a single call · match subject is not a single call | domain/checks.py:2242,2262 | test_service_body_rules_are_flagged |
| TB082 | a service method branches one level deep | public service method | nests a conditional | domain/checks.py:2252,2272 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| TB050 | a tesser import is module-level | role, srv/bootstrap, or test module | imports ⟨import⟩ inside a function | domain/checks.py:2325 | test_nested_imports_neither_classify_nor_satisfy_presence, test_protocol_module_totality_is_flagged |
| TB043 | a relative import resolves inside the tree | role, srv/bootstrap, or test module | imports ⟨import⟩ beyond the package root | domain/checks.py:2335 | test_relative_imports_resolve_against_the_package |
| TB053 | a context module is imported as an aliased module, never its members | direction-legal context import (role modules and their __init__, srv/bootstrap, test modules) | imports names from ⟨import⟩ · imports ⟨import⟩ without an alias | domain/checks.py:2351,2361 | test_role_init_only_reexports_its_own_role, test_a_role_init_may_import_a_module_but_never_a_class, test_context_module_import_form, test_relative_imports_resolve_against_the_package, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |

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
