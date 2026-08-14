# Rules implemented in the spike

Generated from the implementation by `rules.py` — never hand-edit.
`python3 rules.py --check` fails when this file drifts from the code.
One row per rule: the normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## tessercheck rules (from the violation messages in tessercheck/domain/checks.py)

| Code | The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|---|
| TB043 | a module carries its own shape, because a stub is what the type checker reads and the walk cannot | checked source file | is a stub | domain/checks.py:811 | test_a_stub_cannot_shadow_the_shape_the_rules_read |
| TB043 | a module has one definition | checked source file | is also defined by ⟨paths⟩ | domain/checks.py:823 | test_a_colliding_module_definition_is_a_finding_not_a_crash, test_a_colliding_unparseable_file_reports_the_collision |
| TB043 | every checked module is readable UTF-8 Python | checked source file | could not be read as UTF-8 text | domain/checks.py:833 | test_a_non_utf8_file_is_a_finding_not_a_crash |
| TB043 | every checked module parses | checked source file | does not parse (⟨error⟩) | domain/checks.py:848 | test_an_unparseable_module_is_a_finding_not_a_crash, test_reader_findings_are_never_inline_suppressible, test_a_colliding_unparseable_file_reports_the_collision |
| TB090 | an ignore comment suppresses an actual finding | ignore comment | carries an ignore that suppresses nothing | domain/checks.py:885 | test_a_scoped_ignore_leaves_other_codes_alone, test_a_stale_ignore_is_itself_a_finding, test_tb090_itself_cannot_be_ignored |
| TB041 | a context holds only domain, application, client, adapters, wiring, and tests modules | context package | is not a context module | domain/checks.py:1111 | test_non_context_module_and_nonempty_init_are_flagged |
| TB041 | a ports package holds only ports modules, and test_/eval_/conftest are reserved names, because a fake here would be an implementation adapters may import | context package | is not a ports module | domain/checks.py:1072 | test_a_ports_package_holds_only_ports_modules |
| TB041 | a role is a package, never a module | context package | is a role module | domain/checks.py:1099 | test_a_role_must_be_a_package |
| TB041 | a context tests package holds only test modules and conftest | context package | is neither a test module nor conftest | domain/checks.py:1062 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB041 | ports is a package, never a module | context package | is a ports module | domain/checks.py:1085 | test_ports_is_a_package_never_a_module |
| TB042 | a context __init__ is empty | context `__init__` | __init__ declares code | domain/checks.py:1122 | test_non_context_module_and_nonempty_init_are_flagged |
| TB042 | a protocol __init__ is empty | protocol package `__init__` | __init__ declares code | domain/checks.py:1133 | test_a_protocol_init_is_empty |
| TB068 | an import is a statement the walk can read, never a call | every module | imports dynamically through sys.modules · imports dynamically through ⟨types⟩ | domain/checks.py:1152,1165 | test_a_dynamic_import_is_not_a_way_around_the_matrix |
| TB044 | a checkable tree carries a .tesser-root file containing 'app' at its root | the checked tree itself | this tree is not declared | domain/checks.py:1236 | test_an_undeclared_tree_is_a_finding_and_nothing_else_is |
| TB044 | a tessercheck run covers one declared tree, so run that tree directly | the checked tree itself | declares a nested tree root | domain/checks.py:1256 | test_a_nested_declaration_is_a_finding |
| TB044 | the one recognized kind is 'app' | the checked tree itself | this tree declares an unrecognized kind | domain/checks.py:1246 | test_an_unrecognized_declaration_is_a_finding |
| TB040 | every module belongs to a context, srv, bootstrap, tests, or the protocol package | top-level module | belongs to no governed package | domain/checks.py:1268 | test_homeless_modules_are_flagged |
| TB065 | a conftest is a leaf that imports nothing from its tree | conftest module | imports ⟨import⟩ | domain/checks.py:1290 | test_a_root_conftest_is_a_leaf, test_a_conftest_off_the_tier_map_is_a_leaf, test_a_vendored_tesser_package_is_not_the_tree |
| TB065 | a root module is a leaf that imports nothing from its tree | root module | imports ⟨import⟩ | domain/checks.py:1302 | test_a_root_module_is_a_leaf |
| TB063 | a context __main__ composes from its own application, adapters, client, and wiring | context `__main__` | imports ⟨import⟩ | domain/checks.py:1335 | test_a_context_main_composes_only_its_own_context |
| TB041 | a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code | domain/checks.py:1352,1362 | test_tests_package_totality_is_flagged |
| TB042 | a context tests __init__ is empty | context tests `__init__` | __init__ declares code | domain/checks.py:1373 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB042 | a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code · imports ⟨import⟩ | domain/checks.py:1387,1400 | test_role_init_only_reexports_its_own_role, test_relative_imports_resolve_against_the_package |
| TB042 | a srv or bootstrap __init__ is empty | srv / bootstrap `__init__` | __init__ declares code | domain/checks.py:1413 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a bootstrap module imports tesser.context exactly once, as ts | bootstrap module | never imports tesser.context · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1449,1460,1469,1478 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a bootstrap module imports only tesser.context | bootstrap module | imports ⟨import⟩ | domain/checks.py:1440 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a srv module imports tesser.srv exactly once, as ts | srv module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1449,1460,1469,1478 | test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a srv module imports only tesser.srv | srv module | imports ⟨import⟩ | domain/checks.py:1440 | test_srv_and_bootstrap_statement_totality |
| TB050 | a protocol module imports tesser.srv exactly once, as ts | protocol module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1449,1460,1469,1478 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a protocol module imports only tesser.srv | protocol module | imports ⟨import⟩ | domain/checks.py:1440 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a ports module imports tesser.application exactly once, as ts | ports module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1449,1460,1469,1478 | test_a_ports_module_tesser_import_rules |
| TB050 | a ports module imports only tesser.application | ports module | imports ⟨import⟩ | domain/checks.py:1440 | test_a_ports_module_stdlib_allowlist, test_a_ports_module_tesser_import_rules |
| TB050 | a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1449,1460,1469,1478 | test_role_module_tesser_import_is_exactly_once_as_ts, test_nested_imports_neither_classify_nor_satisfy_presence, test_srv_and_bootstrap_tesser_form_modes |
| TB050 | a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain/checks.py:1440 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| TB050 | a test module imports only tesser.testing | test module | imports ⟨import⟩ | domain/checks.py:1440 | test_test_module_tesser_import_rules |
| TB050 | a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:1449,1460,1469 | test_test_module_tesser_import_rules |
| TB051 | a bootstrap function declares itself with @ts.function | bootstrap module | is an undeclared module function | domain/checks.py:1500 | test_srv_and_bootstrap_statement_totality |
| TB051 | a bootstrap constant is Final | bootstrap module | declares a module constant without Final | domain/checks.py:1511,1521 | test_srv_and_bootstrap_statement_totality |
| TB051 | a bootstrap module holds only imports, declared functions, and Final constants | bootstrap module | has a loose module-level statement · is a class | domain/checks.py:1531,2309 | test_srv_and_bootstrap_statement_totality |
| TB051 | a srv function declares itself with @ts.function | srv module | is an undeclared module function | domain/checks.py:1500 | test_srv_and_bootstrap_statement_totality |
| TB051 | a srv constant is Final | srv module | declares a module constant without Final | domain/checks.py:1511,1521 | test_srv_and_bootstrap_statement_totality, test_srv_and_bootstrap_tesser_form_modes |
| TB051 | a srv module holds only imports, declared classes and functions, and Final constants | srv module | has a loose module-level statement | domain/checks.py:1531 | test_srv_and_bootstrap_statement_totality |
| TB051 | a protocol function declares itself with @ts.function | protocol module | is an undeclared module function | domain/checks.py:1500 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol constant is Final | protocol module | declares a module constant without Final | domain/checks.py:1511,1521 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol module holds only imports, declared classes and functions, and Final constants | protocol module | has a loose module-level statement | domain/checks.py:1531 | test_protocol_module_totality_is_flagged |
| TB051 | a module function declares itself with @ts.function | context role module | is an undeclared module function | domain/checks.py:1500 | test_placement_totality_is_flagged |
| TB051 | a module constant is Final | context role module | declares a module constant without Final | domain/checks.py:1511,1521 | test_placement_totality_is_flagged, test_declared_function_and_final_constant_pass |
| TB051 | a context module holds only imports, classes, declared functions, and Final constants | context role module | has a loose module-level statement | domain/checks.py:1531 | test_placement_totality_is_flagged |
| TB020 | code speaks for itself — comments, docstrings, and loose strings belong in the doc layer | every module | carries a code comment · carries ⟨kind⟩ | domain/checks.py:1556,1579 | test_comments_docstrings_and_bare_strings_are_flagged |
| TB030 | a test double is a hand-written fake, never a mocking library or a runtime patcher | every module | imports a mocking library · reaches for pytest MonkeyPatch · takes the ⟨name⟩ fixture | domain/checks.py:1599,1611,1622,1637,1651,1666 | test_mocking_library_and_patcher_fixtures_are_flagged |
| TB033 | a shadowed builtin is never called — rename the binding | every module | binds ⟨builtin⟩ and calls it in the same scope | domain/checks.py:1700 | test_a_called_shadowed_builtin_is_flagged |
| TB004 | compare value objects by value, never by their string form | every module | equates two str() calls | domain/checks.py:1722 | test_string_form_equality_is_flagged |
| TB002 | a value object's field is hashable — a tuple or frozenset, never a mutable collection | value object class | field ⟨field⟩ is a mutable collection | domain/checks.py:1740 | test_a_value_object_mutable_collection_field_is_flagged |
| TB010 | a value object hides its representation — a public field belongs on a spec | value object class | exposes field ⟨field⟩ | domain/checks.py:1786 | test_a_value_object_hides_its_representation |
| TB010 | a value object's accessor returns a value object — the canonical exit is the only primitive door | value object class | passes the raw primitive through | domain/checks.py:1807 | test_a_value_object_hides_its_representation |
| TB016 | bool and complex are not value-object material — model the raw value or reach for an enum | value object class | field ⟨field⟩ is a ⟨scalar⟩ | domain/checks.py:1830 | test_composition_norms |
| TB016 | a compound backs itself with child value objects | value object class | field ⟨field⟩ is a bare primitive | domain/checks.py:1843 | test_composition_norms |
| TB017 | a value object has one door — its own __init__ | value object class | is a second construction door | domain/checks.py:1875 | test_a_value_object_has_one_construction_door |
| TB015 | a structured domain object has no primitive exit — decompose through leaf components | value object conversion dunder | is a primitive exit | domain/checks.py:1969,1984 | test_exit_norms_leaf_and_structured |
| TB015 | a leaf defines exactly its backing type's conversion dunder | value object conversion dunder | is a mismatched exit | domain/checks.py:1948 | test_exit_norms_leaf_and_structured |
| TB018 | a canonical exit is a one-line delegation to its canonical_* policy | value object conversion dunder | hand-rolls its exit | domain/checks.py:1958 | test_exit_norms_leaf_and_structured |
| TB011 | an accessor returns a defensive copy, never the backing store | entity or aggregate accessor | hands back its backing collection | domain/checks.py:2017 | test_an_accessor_never_hands_back_the_backing_collection |
| TB012 | an aggregate is referenced by its ID value object, never held | entity or aggregate field | field ⟨field⟩ holds another aggregate root | domain/checks.py:2044 | test_an_aggregate_is_referenced_by_id_never_held |
| TB015 | a domain object never serializes itself — a spec is construction data, not an exit | domain object public method | returns a spec | domain/checks.py:2088 | test_domain_returns_and_spec_returns |
| TB019 | a domain object's public behavior hands back domain objects — the licensed exits are the protocol dunders, the canonical exit, and a -> None transition | domain object public method | returns ⟨types⟩ | domain/checks.py:2100 | test_domain_returns_and_spec_returns |
| TB052 | a srv class declares its block | srv module | declares no ts.* base | domain/checks.py:2349 | test_srv_and_bootstrap_statement_totality |
| TB052 | only a host class lives in a srv module | srv module | is ⟨kind⟩ | domain/checks.py:2358 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB064 | a protocol module is context-generic and imports no context | protocol module | imports ⟨import⟩ | domain/checks.py:2398 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module never imports srv or bootstrap | protocol module | imports ⟨import⟩ | domain/checks.py:2408 | test_protocol_module_totality_is_flagged |
| TB052 | a protocol class declares its block | protocol module | declares no ts.* base | domain/checks.py:2432 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module imports nothing else from its tree | protocol module | imports ⟨import⟩ | domain/checks.py:2418 | test_a_protocol_module_imports_nothing_else_from_its_tree |
| TB052 | only protocol ports, protocol records, protocol rejections, protocol requests, and protocol responses live in a protocol module | protocol module | is ⟨kind⟩ | domain/checks.py:2441 | test_protocol_module_totality_is_flagged |
| TB042 | a ports __init__ is empty | ports `__init__` | __init__ declares code | domain/checks.py:2508 | test_a_ports_init_is_empty |
| TB052 | a ports module declares exactly one port, so no two ports can share a request or a response | ports module | declares ⟨count⟩ ports · declares no port | domain/checks.py:2747,2757 | test_a_ports_module_declares_exactly_one_port |
| TB051 | a ports module holds only imports and classes | ports module | has a loose module-level statement | domain/checks.py:2769 | test_a_ports_module_holds_only_imports_and_classes |
| TB067 | a ports module is a leaf and imports nothing from its tree, its own siblings included | ports module | imports ⟨import⟩ | domain/checks.py:2542 | test_a_ports_module_is_a_leaf |
| TB052 | a ports module declares its port and its DTOs at module level, where the one-port count can see them | ports module | is a nested class | domain/checks.py:2565 | test_a_nested_class_cannot_hide_a_second_port |
| TB051 | a ports module holds no expression that runs at import, and a metaclass is logic every adapter imports | ports module | carries a class keyword | domain/checks.py:2578 | test_a_ports_class_carries_no_keyword |
| TB051 | a ports module names concrete shapes, because a type parameter is a slot the shape rules cannot read and a bound is an expression | ports module | is generic | domain/checks.py:2592,2615 | test_a_ports_module_runs_nothing_at_import |
| TB051 | a ports module holds no expression that runs at import, and a base built by a call is logic every adapter imports | ports module | computes a base | domain/checks.py:2630 | test_a_ports_module_runs_nothing_at_import |
| TB051 | only an enum member is class-level data in a ports module, because anything else runs at import in the one application module adapters may import | ports module | carries a class-level statement | domain/checks.py:2682 | test_a_ports_class_carries_no_class_level_statement |
| TB052 | a ports class declares its block | ports module | declares no ts.* base | domain/checks.py:2712 | test_a_ports_module_holds_only_port_kinds |
| TB052 | a port DTO is never subclassed, because a response hierarchy is a union mypy cannot check for exhaustiveness | ports module | subclasses a port DTO | domain/checks.py:2737 | test_a_port_dto_is_never_subclassed |
| TB067 | a ports module imports only tesser.application and the pure stdlib | ports module | imports ⟨import⟩ | domain/checks.py:2552 | test_a_ports_module_stdlib_allowlist |
| TB051 | a ports module holds no expression that runs at import, and an annotation is evaluated like any other | ports module | computes an annotation | domain/checks.py:2604 | test_a_ports_module_computes_no_annotation |
| TB051 | a ports module holds no expression that runs at import, because every adapter imports it | ports module | carries a computed default | domain/checks.py:2651 | test_a_ports_module_runs_nothing_at_import, test_an_async_port_method_runs_nothing_at_import |
| TB051 | a ports enum is a closed set of names and nothing else, because a method or a decorator here is logic every adapter imports | ports module | carries more than its members | domain/checks.py:2665 | test_a_ports_enum_carries_nothing_but_its_members |
| TB052 | a ports enum is an enum.Enum, because a str- or int-backed member compares equal to a raw literal and reopens the typo the enum closes | ports module | is an enum.⟨enum⟩ | domain/checks.py:2700 | test_a_ports_enum_is_a_plain_enum |
| TB052 | only a port and the requests and responses it speaks live in a ports module | ports module | is ⟨kind⟩ | domain/checks.py:2721 | test_a_ports_module_holds_only_port_kinds |
| TB051 | a port method declares a shape and never a body, because a ports module holds no logic to import | port protocol method | carries a body | domain/checks.py:2793 | test_a_port_method_declares_a_shape_and_never_a_body |
| TB081 | a port declares only its public calls and __call__, because a private name is not private to anyone implementing or holding the port | port protocol method | is not a call an implementer provides | domain/checks.py:2803 | test_a_port_declares_only_the_calls_an_implementer_provides |
| TB081 | a port method speaks requests and responses declared in its own ports module, never a bare ts.Request or ts.Response, which two ports would share | port protocol method | names a shape it does not declare | domain/checks.py:2842 | test_a_port_speaks_shapes_it_declares_itself |
| TB051 | a ports module holds no decorator, because a decorator is a call that runs at import in the one application module adapters may import | ports module | is decorated | domain/checks.py:2858 | test_a_ports_module_runs_nothing_at_import |
| TB069 | a ports module holds only the shapes its rules can read, so anything else is a finding by default rather than a gap nobody enumerated | ports module | holds a ⟨node⟩ | domain/checks.py:2939 | test_a_ports_module_holds_only_shapes_the_rules_can_read |
| TB052 | an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain/checks.py:3079 | test_an_adapters_module_holds_one_kind |
| TB052 | every context class declares its block | context role module | declares no ts.* base | domain/checks.py:3039 | test_placement_totality_is_flagged |
| TB052 | a host lives in srv and a protocol kind in a protocol module, never a context | context role module | is ⟨kind⟩ | domain/checks.py:3048 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB052 | a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩ | domain/checks.py:3058 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role |
| TB062 | domain, client, and application import only their context, their tesser package, and the pure stdlib | context role module | imports ⟨import⟩ | domain/checks.py:3173 | test_pure_core_stdlib_allowlist, test_nested_imports_neither_classify_nor_satisfy_presence, test_pure_core_allowlist_covers_application_and_domain_future |
| TB061 | a context reaches another context only through its client, and only from gateways and wiring | context role module | imports ⟨import⟩ | domain/checks.py:3156 | test_import_matrix_is_flagged, test_wiring_is_a_role, test_only_a_gateway_reaches_a_foreign_client, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |
| TB066 | of the app shell a context imports only protocol, and only from its adapters | context role module | imports ⟨import⟩ | domain/checks.py:3187 | test_a_context_role_reaches_the_app_shell_only_as_adapters_to_protocol |
| TB060 | only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain/checks.py:3135 | test_only_a_handler_imports_its_own_client |
| TB060 | the same-context matrix is a role to itself, application to domain and client, adapters to application/ports, wiring to application, adapters, and client | context role module | imports ⟨import⟩ | domain/checks.py:3145 | test_import_matrix_is_flagged, test_an_adapter_reaches_application_only_through_ports |
| TB063 | a host reaches a context only through its handlers | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:3216 | test_srv_and_bootstrap_import_rows, test_a_denied_app_edge_is_not_form_checked |
| TB063 | the composition root never imports a host | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:3239 | test_srv_and_bootstrap_import_rows |
| TB063 | bootstrap builds from wiring, clients, and adapters, never domain or application | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:3226 | test_srv_and_bootstrap_import_rows |
| TB066 | production code never imports the tests package | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:3248 | test_production_never_imports_the_tests_package |
| TB066 | bootstrap composes the application and never imports protocol | srv / bootstrap module | imports ⟨import⟩ | domain/checks.py:3258 | test_production_never_imports_the_tests_package |
| TB070 | a test reaches only what its placement allows | test module, by where it is placed | imports ⟨import⟩, but a test placed in ⟨tier⟩ does not reach that package · imports ⟨import⟩, but a test placed in the root tests package reaches a context only through its wiring and client · imports ⟨import⟩, but a test placed in srv reaches a context only through its handlers · imports ⟨import⟩, but a test placed in bootstrap reaches a context only through its wiring, client, and adapters · imports ⟨import⟩, but a test placed in protocol reaches no context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of its own context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches no neighbouring context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of a neighbouring context | domain/checks.py:3302,3343,3364,3384,3403,3439,3450,3461 | test_a_handler_sibling_fakes_only_the_client, test_a_srv_test_reaches_a_context_only_through_its_handlers, test_a_test_reaches_only_what_its_placement_allows, test_a_repository_sibling_test_reaches_its_kind_and_application_only, test_a_wiring_sibling_test_mirrors_production_wiring_reach, test_a_client_sibling_test_reaches_only_its_own_client, test_a_bootstrap_test_reaches_a_context_like_production_bootstrap, test_a_protocol_test_reaches_no_context, test_a_placed_conftest_carries_its_tier, test_a_root_test_reaches_a_context_only_through_wiring_and_client, test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does, test_a_context_tests_module_reaches_its_own_tests_package, test_adapter_kind_and_protocol_tests_shell_reach |
| TB070 | a sibling test lives in a role package or an adapter kind package (handlers, gateways, repositories) | test module, by where it is placed | resolves to no test tier | domain/checks.py:3323 | test_a_test_that_resolves_to_no_tier_is_itself_a_finding, test_an_unplaced_test_module_is_still_governed |
| TB070 | an eval lives only in a gateway, the one place a sampled real-model call is honest | eval module (`eval_*.py`) | is an eval outside a gateway | domain/checks.py:3487 | test_an_eval_lives_only_in_a_gateway |
| TB071 | a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain/checks.py:3534 | test_test_module_totality_is_flagged |
| TB071 | a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain/checks.py:3568 | test_test_module_totality_is_flagged |
| TB072 | a test double declares itself with @ts.fake | test module | is an undeclared class | domain/checks.py:3546 | test_test_module_totality_is_flagged |
| TB072 | a fake implements the port or client it doubles | test module | implements no application port, protocol port, or client | domain/checks.py:3558 | test_test_module_totality_is_flagged, test_a_dotted_module_base_resolves |
| TB073 | a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain/checks.py:3591,3606 | test_helper_rules_are_flagged |
| TB073 | a helper builds a spec | @ts.helper function | does not return a ts.Spec | domain/checks.py:3616 | test_helper_rules_are_flagged |
| TB073 | a helper only constructs | @ts.helper function | has control flow | domain/checks.py:3626 | test_helper_rules_are_flagged |
| TB081 | a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain/checks.py:3674 | test_service_dependencies_must_be_ports |
| TB081 | an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain/checks.py:3722 | test_records_never_carry_domain_objects, test_relative_imports_resolve_against_the_package |
| TB081 | a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain/checks.py:3722 | test_records_never_carry_domain_objects |
| TB080 | a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain/checks.py:3746 | test_domain_field_rules_are_flagged |
| TB080 | a spec only carries construction data | spec class | defines a method on a spec | domain/checks.py:3769 | test_domain_field_rules_are_flagged |
| TB080 | a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain/checks.py:3780 | test_domain_field_rules_are_flagged, test_optional_construction_data_is_the_only_union |
| TB080 | a port DTO declares its fields as __init__ parameters, where the field rules can read them | request/response DTO | carries a class-level statement | domain/checks.py:3808 | test_a_dto_declares_its_fields_where_the_rules_can_read_them |
| TB080 | a DTO declares its fields as named __init__ parameters, where the field rules can read them | request/response DTO | uses *args/**kwargs | domain/checks.py:3825 | test_a_dto_declares_its_fields_where_the_rules_can_read_them |
| TB080 | a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain/checks.py:3835 | test_domain_field_rules_are_flagged, test_an_async_method_on_a_dto_is_still_a_method |
| TB080 | a port DTO constructor only assigns its parameters, because a ports module holds no logic to import | request/response DTO | carries logic | domain/checks.py:3847 | test_a_port_dto_constructor_only_assigns_its_parameters |
| TB080 | a port DTO field is never a bare bool — model the outcome as an enum | request/response DTO | field ⟨name⟩ is a bool | domain/checks.py:3858 | test_a_port_dto_field_is_never_a_bare_bool |
| TB080 | a port DTO field is never a union, optional included — model the outcome as an enum | request/response DTO | field ⟨name⟩ is a union | domain/checks.py:3869 | test_a_port_dto_field_is_never_a_union |
| TB080 | a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain/checks.py:3887 | test_domain_field_rules_are_flagged, test_a_client_dto_with_a_sibling_enum_stays_strict |
| TB080 | an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain/checks.py:3907 | test_aggregate_constructor_violations_are_flagged |
| TB080 | an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain/checks.py:3907 | test_domain_field_rules_are_flagged |
| TB080 | a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain/checks.py:3963,3972,3982 | test_aggregate_constructor_violations_are_flagged |
| TB081 | a port method takes exactly one ts.Request | port protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:3963,3972,3982 | test_a_port_method_speaks_one_request_and_one_response, test_a_port_method_shape_survives_async_and_dunder_call |
| TB081 | a port method returns a ts.Response | port protocol method | does not return a ts.Response | domain/checks.py:3992 | test_a_port_method_speaks_one_request_and_one_response |
| TB081 | a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:3963,3972,3982 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| TB081 | a service method returns a ts.Response | public service method | does not return a ts.Response | domain/checks.py:3992 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| TB081 | a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:3963,3972,3982 | test_client_method_rules_are_flagged |
| TB081 | a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain/checks.py:3992 | test_client_method_rules_are_flagged |
| TB082 | a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ · delegates to ⟨function⟩ | domain/checks.py:4022,4031 | test_service_delegation_is_flagged |
| TB082 | a service method body is at most 10 source lines | public service method | body spans ⟨count⟩ source lines | domain/checks.py:4049 | test_service_body_rules_are_flagged |
| TB082 | a service method satisfies a condition with one domain call | public service method | if condition is not a single call · match subject is not a single call | domain/checks.py:4061,4081 | test_service_body_rules_are_flagged |
| TB082 | a service method branches one level deep | public service method | nests a conditional | domain/checks.py:4071,4091 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| TB050 | a tesser import is module-level | role, srv/bootstrap, or test module | imports ⟨import⟩ inside a function | domain/checks.py:4144 | test_nested_imports_neither_classify_nor_satisfy_presence, test_protocol_module_totality_is_flagged |
| TB043 | a relative import resolves inside the tree | role, srv/bootstrap, or test module | imports ⟨import⟩ beyond the package root | domain/checks.py:4154 | test_relative_imports_resolve_against_the_package |
| TB053 | a context module is imported as an aliased module, never its members | direction-legal context import (role modules and their __init__, srv/bootstrap, test modules) | imports names from ⟨import⟩ · imports ⟨import⟩ without an alias | domain/checks.py:4170,4180 | test_role_init_only_reexports_its_own_role, test_a_role_init_may_import_a_module_but_never_a_class, test_context_module_import_form, test_relative_imports_resolve_against_the_package, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |

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
| adapters-never-import-domain | an adapter imports its context's application ports and foreign clients, never domain |

Import contracts are verified by violation-injection runs during development;
no committed test re-runs them (named gap — cf. python-app's committed
architecture violation-injection test).
