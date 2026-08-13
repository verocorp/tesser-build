# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## tessercheck rules (from the violation messages in tessercheck/domain/checks.py)

| Code | The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|---|
| TB043 | a module has one definition | checked source file | is also defined by ⟨paths⟩ | domain/checks.py:720 | test_a_colliding_module_definition_is_a_finding_not_a_crash, test_a_colliding_unparseable_file_reports_the_collision |
| TB043 | every checked module is readable UTF-8 Python | checked source file | could not be read as UTF-8 text | domain/checks.py:730 | test_a_non_utf8_file_is_a_finding_not_a_crash |
| TB043 | every checked module parses | checked source file | does not parse (⟨error⟩) | domain/checks.py:745 | test_an_unparseable_module_is_a_finding_not_a_crash, test_reader_findings_are_never_inline_suppressible, test_a_colliding_unparseable_file_reports_the_collision |
| TB090 | an ignore comment suppresses an actual finding | ignore comment | carries an ignore that suppresses nothing | domain/checks.py:776 | test_a_scoped_ignore_leaves_other_codes_alone, test_a_stale_ignore_is_itself_a_finding, test_tb090_itself_cannot_be_ignored |
| TB041 | a context holds only domain, application, client, adapters, wiring, and tests modules | context package | is not a context module | domain/checks.py:924 | test_non_context_module_and_nonempty_init_are_flagged |
| TB041 | a role is a package, never a module | context package | is a role module | domain/checks.py:912 | test_a_role_must_be_a_package |
| TB041 | a context tests package holds only test modules and conftest | context package | is neither a test module nor conftest | domain/checks.py:900 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB042 | a context __init__ is empty | context `__init__` | __init__ declares code | domain/checks.py:935 | test_non_context_module_and_nonempty_init_are_flagged |
| TB042 | a protocol __init__ is empty | protocol package `__init__` | __init__ declares code | domain/checks.py:946 | test_a_protocol_init_is_empty |
| TB040 | every module belongs to a context, srv, bootstrap, tests, or the protocol package | top-level module | belongs to no governed package | domain/checks.py:957 | test_homeless_modules_are_flagged |
| TB065 | a conftest is a leaf that imports nothing from its tree | conftest module | imports ⟨import⟩ | domain/checks.py:979 | test_a_root_conftest_is_a_leaf, test_a_conftest_off_the_tier_map_is_a_leaf, test_a_vendored_tesser_package_is_not_the_tree |
| TB065 | a root module is a leaf that imports nothing from its tree | root module | imports ⟨import⟩ | domain/checks.py:991 | test_a_root_module_is_a_leaf |
| TB063 | a context __main__ composes from its own application, adapters, client, and wiring | context `__main__` | imports ⟨import⟩ | domain/checks.py:1024 | test_a_context_main_composes_only_its_own_context |
| TB041 | a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code | domain/checks.py:1041,1051 | test_tests_package_totality_is_flagged |
| TB042 | a context tests __init__ is empty | context tests `__init__` | __init__ declares code | domain/checks.py:1062 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB042 | a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code · imports ⟨import⟩ | domain/checks.py:1076,1089 | test_role_init_only_reexports_its_own_role, test_relative_imports_resolve_against_the_package |
| TB042 | a srv or bootstrap __init__ is empty | srv / bootstrap `__init__` | __init__ declares code | domain/checks.py:1102 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a bootstrap module imports tesser.context exactly once, as ts | bootstrap module | never imports tesser.context · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1138,1149,1158,1167 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a bootstrap module imports only tesser.context | bootstrap module | imports ⟨import⟩ | domain/checks.py:1129 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a srv module imports tesser.srv exactly once, as ts | srv module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1138,1149,1158,1167 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a srv module imports only tesser.srv | srv module | imports ⟨import⟩ | domain/checks.py:1129 | test_srv_and_bootstrap_statement_totality |
| TB050 | a protocol module imports tesser.srv exactly once, as ts | protocol module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1138,1149,1158,1167 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a protocol module imports only tesser.srv | protocol module | imports ⟨import⟩ | domain/checks.py:1129 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1138,1149,1158,1167 | test_role_module_tesser_import_is_exactly_once_as_ts, test_nested_imports_neither_classify_nor_satisfy_presence, test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain/checks.py:1129 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| TB050 | a test module imports only tesser.testing | test module | imports ⟨import⟩ | domain/checks.py:1129 | test_test_module_tesser_import_rules |
| TB050 | a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1138,1149,1158 | test_test_module_tesser_import_rules |
| TB051 | a bootstrap function declares itself with @ts.function | bootstrap module | is an undeclared module function | domain/checks.py:1189 | test_srv_and_bootstrap_statement_totality |
| TB051 | a bootstrap constant is Final | bootstrap module | declares a module constant without Final | domain/checks.py:1200,1210 | test_srv_and_bootstrap_statement_totality |
| TB051 | a bootstrap module holds only imports, declared functions, and Final constants | bootstrap module | has a loose module-level statement · is a class | domain/checks.py:1220,1998 | test_srv_and_bootstrap_statement_totality |
| TB051 | a srv function declares itself with @ts.function | srv module | is an undeclared module function | domain/checks.py:1189 | test_srv_and_bootstrap_statement_totality |
| TB051 | a srv constant is Final | srv module | declares a module constant without Final | domain/checks.py:1200,1210 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| TB051 | a srv module holds only imports, declared classes and functions, and Final constants | srv module | has a loose module-level statement | domain/checks.py:1220 | test_srv_and_bootstrap_statement_totality |
| TB051 | a protocol function declares itself with @ts.function | protocol module | is an undeclared module function | domain/checks.py:1189 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol constant is Final | protocol module | declares a module constant without Final | domain/checks.py:1200,1210 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol module holds only imports, declared classes and functions, and Final constants | protocol module | has a loose module-level statement | domain/checks.py:1220 | test_protocol_module_totality_is_flagged |
| TB051 | a module function declares itself with @ts.function | context role module | is an undeclared module function | domain/checks.py:1189 | test_placement_totality_is_flagged |
| TB051 | a module constant is Final | context role module | declares a module constant without Final | domain/checks.py:1200,1210 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| TB051 | a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain/checks.py:1220 | test_placement_totality_is_flagged |
| TB020 | code speaks for itself — comments, docstrings, and loose strings belong in the doc layer | every module | carries a code comment · carries ⟨kind⟩ | domain/checks.py:1245,1268 | test_comments_docstrings_and_bare_strings_are_flagged |
| TB030 | a test double is a hand-written fake, never a mocking library or a runtime patcher | every module | imports a mocking library · reaches for pytest MonkeyPatch · takes the ⟨name⟩ fixture | domain/checks.py:1288,1300,1311,1326,1340,1355 | test_mocking_library_and_patcher_fixtures_are_flagged |
| TB033 | a shadowed builtin is never called — rename the binding | every module | binds ⟨builtin⟩ and calls it in the same scope | domain/checks.py:1389 | test_a_called_shadowed_builtin_is_flagged |
| TB004 | compare value objects by value, never by their string form | every module | equates two str() calls | domain/checks.py:1411 | test_string_form_equality_is_flagged |
| TB002 | a value object's field is hashable — a tuple or frozenset, never a mutable collection | value object class | field ⟨field⟩ is a mutable collection | domain/checks.py:1429 | test_a_value_object_mutable_collection_field_is_flagged |
| TB010 | a value object hides its representation — a public field belongs on a spec | value object class | exposes field ⟨field⟩ | domain/checks.py:1475 | test_a_value_object_hides_its_representation |
| TB010 | a value object's accessor returns a value object — the canonical exit is the only primitive door | value object class | passes the raw primitive through | domain/checks.py:1496 | test_a_value_object_hides_its_representation |
| TB016 | bool and complex are not value-object material — model the raw value or reach for an enum | value object class | field ⟨field⟩ is a ⟨scalar⟩ | domain/checks.py:1519 | test_composition_norms |
| TB016 | a compound backs itself with child value objects | value object class | field ⟨field⟩ is a bare primitive | domain/checks.py:1532 | test_composition_norms |
| TB017 | a value object has one door — its own __init__ | value object class | is a second construction door | domain/checks.py:1564 | test_a_value_object_has_one_construction_door |
| TB015 | a structured domain object has no primitive exit — decompose through leaf components | value object conversion dunder | is a primitive exit | domain/checks.py:1658,1673 | test_exit_norms_leaf_and_structured |
| TB015 | a leaf defines exactly its backing type's conversion dunder | value object conversion dunder | is a mismatched exit | domain/checks.py:1637 | test_exit_norms_leaf_and_structured |
| TB018 | a canonical exit is a one-line delegation to its canonical_* policy | value object conversion dunder | hand-rolls its exit | domain/checks.py:1647 | test_exit_norms_leaf_and_structured |
| TB011 | an accessor returns a defensive copy, never the backing store | entity or aggregate accessor | hands back its backing collection | domain/checks.py:1706 | test_an_accessor_never_hands_back_the_backing_collection |
| TB012 | an aggregate is referenced by its ID value object, never held | entity or aggregate field | field ⟨field⟩ holds another aggregate root | domain/checks.py:1733 | test_an_aggregate_is_referenced_by_id_never_held |
| TB015 | a domain object never serializes itself — a spec is construction data, not an exit | domain object public method | returns a spec | domain/checks.py:1777 | test_domain_returns_and_spec_returns |
| TB019 | a domain object's public behavior hands back domain objects — the licensed exits are the protocol dunders, the canonical exit, and a -> None transition | domain object public method | returns ⟨types⟩ | domain/checks.py:1789 | test_domain_returns_and_spec_returns |
| TB052 | a srv class declares its block | srv module | declares no ts.* base | domain/checks.py:2038 | test_srv_and_bootstrap_statement_totality |
| TB052 | only a host class lives in a srv module | srv module | is ⟨kind⟩ | domain/checks.py:2047 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB064 | a protocol module is context-generic and imports no context | protocol module | imports ⟨import⟩ | domain/checks.py:2087 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module never imports srv or bootstrap | protocol module | imports ⟨import⟩ | domain/checks.py:2097 | test_protocol_module_totality_is_flagged |
| TB052 | a protocol class declares its block | protocol module | declares no ts.* base | domain/checks.py:2121 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module imports nothing else from its tree | protocol module | imports ⟨import⟩ | domain/checks.py:2107 | test_a_protocol_module_imports_nothing_else_from_its_tree |
| TB052 | only protocol ports, protocol records, protocol rejections, protocol requests, and protocol responses live in a protocol module | protocol module | is ⟨kind⟩ | domain/checks.py:2130 | test_protocol_module_totality_is_flagged |
| TB052 | an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain/checks.py:2200 | test_an_adapters_module_holds_one_kind |
| TB052 | every context class declares its block | context role module | declares no ts.* base | domain/checks.py:2160 | test_placement_totality_is_flagged |
| TB052 | a host lives in srv and a protocol kind in a protocol module, never a context | context role module | is ⟨kind⟩ | domain/checks.py:2169 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB052 | a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩.py | domain/checks.py:2179 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| TB062 | domain, client, and application import only their context, their tesser package, and the pure stdlib | context role module | imports ⟨import⟩ | domain/checks.py:2282 | test_pure_core_stdlib_allowlist, test_nested_imports_neither_classify_nor_satisfy_presence, test_pure_core_allowlist_covers_application_and_domain_future |
| TB061 | a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain/checks.py:2265 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |
| TB066 | of the app shell a context imports only protocol, and only from its adapters | context role module | imports ⟨import⟩ | domain/checks.py:2296 | test_a_context_role_reaches_the_app_shell_only_as_adapters_to_protocol |
| TB060 | only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain/checks.py:2244 | test_only_a_handler_imports_its_own_client |
| TB060 | the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain/checks.py:2254 | test_import_matrix_is_flagged |
| TB063 | a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:2325 | test_srv_and_bootstrap_import_rows, test_a_denied_app_edge_is_not_form_checked |
| TB063 | the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:2348 | test_srv_and_bootstrap_import_rows |
| TB063 | bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:2335 | test_srv_and_bootstrap_import_rows |
| TB066 | production code never imports the tests package | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:2357 | test_production_never_imports_the_tests_package |
| TB066 | bootstrap composes the application and never imports protocol | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:2367 | test_production_never_imports_the_tests_package |
| TB070 | a test reaches only what its placement allows | test module, by where it is placed | imports ⟨import⟩, but a test placed in ⟨tier⟩ does not reach that package · imports ⟨import⟩, but a test placed in the root tests package reaches a context only through its wiring and client · imports ⟨import⟩, but a test placed in srv reaches a context only through its handlers · imports ⟨import⟩, but a test placed in bootstrap reaches a context only through its wiring, client, and adapters · imports ⟨import⟩, but a test placed in protocol reaches no context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of its own context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches no neighbouring context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of a neighbouring context | domain/checks.py:2411,2452,2473,2493,2512,2545,2556,2567 | test_a_handler_sibling_fakes_only_the_client, test_a_srv_test_reaches_a_context_only_through_its_handlers, test_a_test_reaches_only_what_its_placement_allows, test_a_repository_sibling_test_reaches_its_kind_and_application_only, test_a_wiring_sibling_test_mirrors_production_wiring_reach, test_a_client_sibling_test_reaches_only_its_own_client, test_a_bootstrap_test_reaches_a_context_like_production_bootstrap, test_a_protocol_test_reaches_no_context, test_a_placed_conftest_carries_its_tier, test_a_root_test_reaches_a_context_only_through_wiring_and_client, test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does, test_a_context_tests_module_reaches_its_own_tests_package, test_adapter_kind_and_protocol_tests_shell_reach |
| TB070 | a sibling test lives in a role package or an adapter kind package (handlers, gateways, repositories) | test module, by where it is placed | resolves to no test tier | domain/checks.py:2432 | test_a_test_that_resolves_to_no_tier_is_itself_a_finding, test_an_unplaced_test_module_is_still_governed |
| TB070 | an eval lives only in a gateway, the one place a sampled real-model call is honest | eval module (`eval_*.py`) | is an eval outside a gateway | domain/checks.py:2593 | test_an_eval_lives_only_in_a_gateway |
| TB071 | a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain/checks.py:2640 | test_test_module_totality_is_flagged |
| TB071 | a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain/checks.py:2674 | test_test_module_totality_is_flagged |
| TB072 | a test double declares itself with @ts.fake | test module | is an undeclared class | domain/checks.py:2652 | test_test_module_totality_is_flagged |
| TB072 | a fake implements the port or client it doubles | test module | implements no application port, protocol port, or client | domain/checks.py:2664 | test_test_module_totality_is_flagged, test_a_dotted_module_base_resolves |
| TB073 | a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain/checks.py:2697,2712 | test_helper_rules_are_flagged |
| TB073 | a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain/checks.py:2722 | test_helper_rules_are_flagged |
| TB073 | a helper only constructs | @ts.helper function | has control flow | domain/checks.py:2732 | test_helper_rules_are_flagged |
| TB081 | a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain/checks.py:2780 | test_service_dependencies_must_be_ports |
| TB081 | an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain/checks.py:2828 | test_records_never_carry_domain_objects, test_relative_imports_resolve_against_the_package |
| TB081 | a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain/checks.py:2828 | test_records_never_carry_domain_objects |
| TB080 | a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain/checks.py:2852 | test_domain_field_rules_are_flagged |
| TB080 | a spec only carries construction data | spec class | defines a method on a spec | domain/checks.py:2875 | test_domain_field_rules_are_flagged |
| TB080 | a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain/checks.py:2886 | test_domain_field_rules_are_flagged, test_optional_construction_data_is_the_only_union |
| TB080 | a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain/checks.py:2909 | test_domain_field_rules_are_flagged |
| TB080 | a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain/checks.py:2920 | test_domain_field_rules_are_flagged |
| TB080 | an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain/checks.py:2940 | test_aggregate_constructor_violations_are_flagged |
| TB080 | an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain/checks.py:2940 | test_domain_field_rules_are_flagged |
| TB080 | a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain/checks.py:2996,3005,3015 | test_aggregate_constructor_violations_are_flagged |
| TB081 | a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:2996,3005,3015 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| TB081 | a service method returns a ts.Response | public service method | does not return a ts.Response | domain/checks.py:3025 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| TB081 | a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:2996,3005,3015 | test_client_method_rules_are_flagged |
| TB081 | a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain/checks.py:3025 | test_client_method_rules_are_flagged |
| TB082 | a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ · delegates to ⟨function⟩ | domain/checks.py:3055,3064 | test_service_delegation_is_flagged |
| TB082 | a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain/checks.py:3080 | test_service_body_rules_are_flagged |
| TB082 | a service method satisfies a condition with one domain call | public service method | if condition is not a single call · match subject is not a single call | domain/checks.py:3092,3112 | test_service_body_rules_are_flagged |
| TB082 | a service method branches one level deep | public service method | nests a conditional | domain/checks.py:3102,3122 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| TB050 | a tesser import is module-level | role, srv/bootstrap, or test module | imports ⟨import⟩ inside a function | domain/checks.py:3175 | test_nested_imports_neither_classify_nor_satisfy_presence, test_protocol_module_totality_is_flagged |
| TB043 | a relative import resolves inside the tree | role, srv/bootstrap, or test module | imports ⟨import⟩ beyond the package root | domain/checks.py:3185 | test_relative_imports_resolve_against_the_package |
| TB053 | a context module is imported as an aliased module, never its members | direction-legal context import (role modules and their __init__, srv/bootstrap, test modules) | imports names from ⟨import⟩ · imports ⟨import⟩ without an alias | domain/checks.py:3201,3211 | test_role_init_only_reexports_its_own_role, test_a_role_init_may_import_a_module_but_never_a_class, test_context_module_import_form, test_relative_imports_resolve_against_the_package, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |

## Named exemptions (carve-outs the code makes on purpose, not rules)

- modules under the top-level `protocol/` package are the protocol
  modules (PROTOCOL_PACKAGE in tessercheck/domain/checks.py) — package membership
  is the declaration; no suffix opts a module in, so a stray `*wire.py`
  is homeless.
- srv and protocol kinds carry placement and import rules only — no
  signature or body rules yet (deliberate: the srv signature matrix
  ruled the kinds and their invariants, not tessercheck rules over
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
