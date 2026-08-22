# Rules implemented in the spike

Generated from the implementation by the rulebook — never hand-edit.
`python3 -m srv.cli.rules --check` fails when this file drifts from the
code; regenerate with `python3 -m srv.cli.rules`. One row per rule: the
normative clause every violation message ends
with. ⟨…⟩ marks a value filled in per violation. Fixture coverage is
exact: a test covers a rule when an assert literal contains the clause.

## tessercheck rules (from the violation messages in tessercheck/domain/checks.py)

| Code | The rule | Applies to | Fires when | Source | Fixtures |
|---|---|---|---|---|---|
| TB043 | a module carries its own shape, because a stub is what the type checker reads and the walk cannot | checked source file | is a stub | domain/checks.py:932 | test_a_stub_cannot_shadow_the_shape_the_rules_read |
| TB043 | a module has one definition | checked source file | is also defined by ⟨paths⟩ | domain/checks.py:944 | test_a_colliding_module_definition_is_a_finding_not_a_crash, test_a_colliding_unparseable_file_reports_the_collision |
| TB043 | every checked module is readable UTF-8 Python | checked source file | could not be read as UTF-8 text | domain/checks.py:954 | test_a_non_utf8_file_is_a_finding_not_a_crash |
| TB043 | every checked module parses | checked source file | does not parse (⟨error⟩) | domain/checks.py:969 | test_an_unparseable_module_is_a_finding_not_a_crash, test_a_colliding_unparseable_file_reports_the_collision, test_reader_findings_are_never_inline_suppressible |
| TB090 | a debt marker suppresses an actual finding | debt marker | carries a debt marker that suppresses nothing | domain/checks.py:1184 | test_a_scoped_debt_marker_leaves_other_codes_alone, test_a_stale_debt_marker_is_itself_a_finding, test_tb090_itself_cannot_be_suppressed |
| TB074 | an implementation module carries exactly one test_<module>.py beside it | implementation module and its sibling test file | has no sibling test file | domain/checks.py:1236 | test_an_implementation_module_carries_exactly_one_sibling_test |
| TB074 | a sibling test file is named test_<module>.py for the module beside it | implementation module and its sibling test file | pairs with no implementation module | domain/checks.py:1248 | test_a_sibling_test_names_the_module_beside_it |
| TB041 | a context holds only domain, application, client, adapters, component, and tests modules | context package | is not a context module | domain/checks.py:1483 | test_non_context_module_and_nonempty_init_are_flagged, test_a_context_main_is_a_stray_module |
| TB041 | kernel is a package, never a module | context package | is a kernel module at the tree root | domain/checks.py:1414 | test_kernel_is_a_package_never_a_module |
| TB041 | a ports package holds only ports modules, and test_/eval_/conftest are reserved names, because a fake here would be an implementation adapters may import | context package | is not a ports module | domain/checks.py:1444 | test_a_ports_package_holds_only_ports_modules |
| TB041 | a role is a package, never a module | context package | is a role module | domain/checks.py:1471 | test_a_role_must_be_a_package |
| TB041 | a context tests package holds only test modules and conftest | context package | is neither a test module nor conftest | domain/checks.py:1434 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB041 | ports is a package, never a module | context package | is a ports module | domain/checks.py:1457 | test_ports_is_a_package_never_a_module |
| TB042 | a context __init__ is empty | context `__init__` | __init__ declares code | domain/checks.py:1494 | test_non_context_module_and_nonempty_init_are_flagged |
| TB042 | a protocol __init__ is empty | protocol package `__init__` | __init__ declares code | domain/checks.py:1505 | test_a_protocol_init_is_empty |
| TB068 | an import is a statement the walk can read, never a call | every module | imports dynamically through sys.modules · imports dynamically through ⟨types⟩ | domain/checks.py:1564,1608 | test_a_dynamic_import_is_not_a_way_around_the_matrix |
| TB044 | a checkable tree carries a .tesser-root file containing 'app' at its root | the checked tree itself | this tree is not declared | domain/checks.py:1622 | test_an_undeclared_tree_is_a_finding_and_nothing_else_is |
| TB044 | a tessercheck run covers one declared tree, so run that tree directly | the checked tree itself | declares a nested tree root | domain/checks.py:1667 | test_a_nested_declaration_is_a_finding_and_masks_the_walk |
| TB045 | a declared tree is walked in full, and a symlink escapes the walk | the checked tree itself | is a symlinked directory | domain/checks.py:1677 | test_a_symlinked_directory_is_a_finding |
| TB044 | a .tesser-root is a plain UTF-8 text file | the checked tree itself | this tree's declaration is not readable | domain/checks.py:1632 | test_an_unreadable_declaration_is_a_finding |
| TB044 | a tree has one exported kernel, so a declaration carries at most one 'export <dir>' line | the checked tree itself | this tree declares a second exported kernel | domain/checks.py:1642 | test_a_second_export_line_is_a_finding_end_to_end, test_a_second_export_declaration_is_a_finding |
| TB044 | a declaration is 'app', then only 'skip <dir>', 'export <dir>', and 'import <package>' lines | the checked tree itself | this tree declares an unrecognized kind | domain/checks.py:1653 | test_an_unrecognized_declaration_is_a_finding |
| TB044 | an exported kernel never takes the name of the kernel package or the app shell | the checked tree itself | this tree exports '⟨export⟩' | domain/checks.py:1692 | test_an_export_never_takes_a_shell_or_kernel_name |
| TB044 | an export names a package at the tree root | the checked tree itself | this tree exports '⟨export⟩' but no such package exists | domain/checks.py:1705 | test_an_export_that_is_no_package_is_a_finding, test_an_export_naming_a_bare_module_is_a_finding |
| TB044 | a bounded context's domain is never exported — a kernel is not a context | the checked tree itself | this tree exports '⟨export⟩', a context-shaped package | domain/checks.py:1736 | test_a_context_shaped_export_is_a_finding |
| TB044 | a tree exporting tesser is the distribution itself — its top level is tesser and tests, nothing else | the checked tree itself | this tree exports 'tesser' but also holds ⟨packages⟩ | domain/checks.py:1722 | test_a_tree_exporting_tesser_holds_nothing_else |
| TB044 | an import declaration names an installed external kernel, never something the walk governs | the checked tree itself | this tree declares 'import ⟨import⟩' but that names this tree | domain/checks.py:1753 | test_an_import_declaration_never_names_this_tree |
| TB044 | the pure stdlib is already legal and the rest of it is never a kernel | the checked tree itself | this tree declares 'import ⟨import⟩' but that names the stdlib | domain/checks.py:1764 | test_an_import_declaration_never_names_the_stdlib |
| TB044 | an import declaration that legalizes nothing is itself a finding | the checked tree itself | this tree declares 'import ⟨import⟩' and nothing uses it | domain/checks.py:1777 | test_an_unused_import_declaration_is_a_finding |
| TB040 | every module belongs to a context, a kernel, srv, app, tests, or the protocol package | top-level module | belongs to no governed package | domain/checks.py:1790 | test_homeless_modules_are_flagged, test_a_root_module_is_homeless |
| TB065 | a conftest is a leaf that imports nothing from its tree | conftest module | imports ⟨import⟩ | domain/checks.py:1805 | test_a_vendored_tesser_package_is_not_the_tree, test_a_root_conftest_is_a_leaf, test_a_conftest_off_the_tier_map_is_a_leaf, test_a_conftest_leaf_counts_tesser_edges_in_the_exporting_tree |
| TB041 | a tests package holds only test modules and conftest | tests package module | is neither a test module nor conftest · __init__ declares code | domain/checks.py:1826,1836 | test_tests_package_totality_is_flagged |
| TB042 | a context tests __init__ is empty | context tests `__init__` | __init__ declares code | domain/checks.py:1847 | test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application |
| TB042 | a role __init__ only re-exports from its own role | role package `__init__` | __init__ declares code · imports ⟨import⟩ | domain/checks.py:1861,1874 | test_role_init_only_reexports_its_own_role, test_relative_imports_resolve_against_the_package |
| TB041 | the tesser distribution holds only the namespaces its consumers import | tesser distribution `__init__` | is not a consumer namespace | domain/checks.py:1894,1934 | test_the_distribution_holds_only_consumer_namespaces, test_a_stray_subpackage_in_the_distribution_is_a_finding |
| TB042 | a tesser __init__ only re-exports from the distribution | tesser distribution `__init__` | __init__ declares code · imports ⟨import⟩ | domain/checks.py:1905,1918 | test_a_tesser_init_only_reexports_from_the_distribution |
| TB062 | a shell module imports only the tesser distribution and the shell stdlib | tesser distribution module | imports ⟨import⟩ | domain/checks.py:1949 | test_a_shell_module_stays_on_the_shell_stdlib |
| TB042 | a kernel __init__ only re-exports from its own kernel | kernel `__init__` | __init__ declares code · imports ⟨import⟩ | domain/checks.py:1964,1977 | test_a_kernel_init_only_reexports_from_its_own_kernel, test_a_kernel_init_rejects_a_near_miss_package |
| TB052 | every kernel class declares its block | kernel module | declares no ts.* base | domain/checks.py:1999 | test_every_kernel_class_declares_its_block |
| TB052 | a kernel holds only domain kinds — value objects, entities, aggregates, and specs | kernel module | is ⟨kind⟩ | domain/checks.py:2008 | test_a_kernel_holds_only_domain_kinds |
| TB062 | a kernel imports only its kernel, tesser.domain, declared kernels, and the pure stdlib | kernel module | imports ⟨import⟩ | domain/checks.py:2072 | test_kernel_import_allowlist, test_the_exported_kernel_never_imports_the_private_kernel |
| TB042 | a srv or app __init__ is empty | srv / app `__init__` | __init__ declares code | domain/checks.py:2084 | test_srv_and_app_tesser_form_modes |
| TB050 | a kernel module imports tesser.domain exactly once, as ts | kernel module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154,2163 | test_kernel_tesser_import_rules |
| TB050 | a kernel module imports only tesser.domain | kernel module | imports ⟨import⟩ | domain/checks.py:2125 | test_kernel_tesser_import_rules |
| TB050 | a norm module is from-imported by name, never whole — the ts alias belongs to the placement's own package | kernel module | imports ⟨import⟩ whole | domain/checks.py:2112 | test_a_norm_module_is_from_imported_where_its_placement_allows |
| TB050 | an app module imports tesser.app exactly once, as ts | app module | never imports tesser.app · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154,2163 | test_srv_and_app_statement_totality, test_srv_and_app_tesser_form_modes |
| TB050 | an app module's tesser imports are tesser.app, and tesser.errors | app module | imports ⟨import⟩ | domain/checks.py:2125 | test_srv_and_app_tesser_form_modes |
| TB050 | a srv module imports tesser.srv exactly once, as ts | srv module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154,2163 | test_srv_and_app_tesser_form_modes |
| TB050 | a srv module's tesser imports are tesser.srv, and tesser.errors | srv module | imports ⟨import⟩ | domain/checks.py:2125 | test_srv_and_app_statement_totality |
| TB050 | a protocol module imports tesser.srv exactly once, as ts | protocol module | never imports tesser.srv · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154,2163 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a protocol module imports only tesser.srv | protocol module | imports ⟨import⟩ | domain/checks.py:2125 | test_protocol_module_tesser_import_is_exactly_once_as_ts |
| TB050 | a ports module imports tesser.application exactly once, as ts | ports module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154,2163 | test_a_ports_module_tesser_import_rules |
| TB050 | a ports module imports only tesser.application | ports module | imports ⟨import⟩ | domain/checks.py:2125 | test_a_ports_module_stdlib_allowlist, test_a_ports_module_tesser_import_rules |
| TB050 | a role module imports its tesser package exactly once, as ts | context role module | never imports ⟨package⟩ · imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154,2163 | test_role_module_tesser_import_is_exactly_once_as_ts, test_nested_imports_neither_classify_nor_satisfy_presence, test_srv_and_app_tesser_form_modes, test_a_norm_module_is_from_imported_where_its_placement_allows |
| TB050 | a domain module's tesser imports are tesser.domain, tesser.errors, and tesser.serialization | context role module | imports ⟨import⟩ | domain/checks.py:2125 | test_placement_totality_is_flagged, test_a_role_may_be_a_package |
| TB050 | a test module's tesser imports are tesser.testing, tesser.errors, and tesser.serialization | test module | imports ⟨import⟩ | domain/checks.py:2125 | test_test_module_tesser_import_rules |
| TB050 | a test module imports tesser.testing at most once, as ts | test module | imports ⟨import⟩ again · imports names from ⟨import⟩ · imports ⟨import⟩ without the ts alias | domain/checks.py:2134,2145,2154 | test_test_module_tesser_import_rules |
| TB050 | an application module's tesser imports are tesser.application and tesser.errors | context role module | imports ⟨import⟩ | domain/checks.py:2125 | test_a_norm_module_is_from_imported_where_its_placement_allows |
| TB050 | an adapters module's tesser imports are tesser.adapters and tesser.errors | context role module | imports ⟨import⟩ | domain/checks.py:2125 | test_any_role_but_client_may_from_import_tesser_errors |
| TB050 | a component module's tesser imports are tesser.component, and tesser.errors | context role module | imports ⟨import⟩ | domain/checks.py:2125 | test_wiring_bootstrap_and_srv_may_from_import_tesser_errors |
| TB050 | a role module imports only its own tesser package | context role module | imports ⟨import⟩ | domain/checks.py:2125 | test_any_role_but_client_may_from_import_tesser_errors |
| TB051 | a kernel module holds classes, never functions | kernel module | is a module function | domain/checks.py:2177 | test_kernel_statement_totality |
| TB051 | a srv module holds classes, never functions | srv module | is a module function | domain/checks.py:2177 | test_srv_and_app_statement_totality |
| TB051 | a protocol module holds classes, never functions | protocol module | is a module function | domain/checks.py:2177 | test_protocol_module_totality_is_flagged |
| TB051 | a context role module holds classes, never functions | context role module | is a module function | domain/checks.py:2177 | test_placement_totality_is_flagged, test_a_final_constant_passes_and_a_declared_function_is_still_a_module_function |
| TB051 | kernel constants are Final | kernel module | declares a module constant without Final | domain/checks.py:2206,2216 | test_kernel_statement_totality |
| TB051 | a kernel module holds only imports, classes, and Final constants | kernel module | has a loose module-level statement | domain/checks.py:2226 | test_kernel_statement_totality |
| TB051 | app constants are Final | app module | declares a module constant without Final | domain/checks.py:2206,2216 | test_srv_and_app_statement_totality |
| TB051 | an app module holds only imports, classes, declared functions, and Final constants | app module | has a loose module-level statement | domain/checks.py:2226 | test_srv_and_app_statement_totality |
| TB051 | srv constants are Final | srv module | declares a module constant without Final | domain/checks.py:2206,2216 | test_srv_and_app_statement_totality, test_srv_and_app_tesser_form_modes |
| TB051 | a srv module holds only imports, declared classes, and Final constants | srv module | has a loose module-level statement | domain/checks.py:2226 | test_srv_and_app_statement_totality |
| TB051 | protocol constants are Final | protocol module | declares a module constant without Final | domain/checks.py:2206,2216 | test_protocol_module_totality_is_flagged |
| TB051 | a protocol module holds only imports, declared classes, and Final constants | protocol module | has a loose module-level statement | domain/checks.py:2226 | test_protocol_module_totality_is_flagged |
| TB051 | module constants are Final | context role module | declares a module constant without Final | domain/checks.py:2206,2216 | test_placement_totality_is_flagged |
| TB051 | a context module holds only imports, classes, and Final constants | context role module | has a loose module-level statement | domain/checks.py:2226 | test_placement_totality_is_flagged |
| TB051 | a class holds only public methods | every class, in every module | is a private method | domain/checks.py:2249 | test_a_private_method_is_flagged_in_every_module_kind |
| TB020 | code speaks for itself — comments, docstrings, and loose strings belong in the doc layer | every module | carries a code comment · carries ⟨kind⟩ | domain/checks.py:2267,2296 | test_comments_docstrings_and_bare_strings_are_flagged |
| TB030 | a test double is a hand-written fake, never a mocking library or a runtime patcher | every module | imports a mocking library · reaches for pytest MonkeyPatch · takes the ⟨name⟩ fixture | domain/checks.py:2318,2330,2343,2358,2372,2402 | test_mocking_library_and_patcher_fixtures_are_flagged |
| TB033 | a shadowed builtin is never called — rename the binding | every module | binds ⟨builtin⟩ and calls it in the same scope | domain/checks.py:2487 | test_a_called_shadowed_builtin_is_flagged |
| TB004 | compare value objects by value, never by their string form | every module | equates two str() calls | domain/checks.py:2524 | test_string_form_equality_is_flagged |
| TB002 | a value object's field is hashable — a tuple or frozenset, never a mutable collection | value object class | field ⟨field⟩ is a mutable collection | domain/checks.py:2542 | test_a_value_object_mutable_collection_field_is_flagged |
| TB010 | a value object hides its representation — a public field belongs on a spec | value object class | exposes field ⟨field⟩ | domain/checks.py:2566 | test_a_value_object_hides_its_representation |
| TB010 | a value object's accessor returns a value object — the canonical exit is the only primitive door | value object class | passes the raw primitive through | domain/checks.py:2592 | test_a_value_object_hides_its_representation |
| TB016 | bool and complex are not value-object material — model the raw value or reach for an enum | value object class | field ⟨field⟩ is a ⟨scalar⟩ | domain/checks.py:2615 | test_composition_norms |
| TB016 | a compound backs itself with child value objects | value object class | field ⟨field⟩ is a bare primitive | domain/checks.py:2628 | test_composition_norms |
| TB017 | a value object has one door — its own __init__ | value object class | is a second construction door | domain/checks.py:2694 | test_a_value_object_has_one_construction_door |
| TB015 | a structured domain object has no primitive exit — decompose through leaf components | value object conversion dunder | is a primitive exit | domain/checks.py:2759,2774 | test_exit_norms_leaf_and_structured |
| TB015 | a leaf defines exactly its backing type's conversion dunder | value object conversion dunder | is a mismatched exit | domain/checks.py:2738 | test_exit_norms_leaf_and_structured |
| TB018 | a canonical exit is a one-line delegation to its canonical_* policy | value object conversion dunder | hand-rolls its exit | domain/checks.py:2748 | test_exit_norms_leaf_and_structured |
| TB011 | an accessor returns a defensive copy, never the backing store | entity or aggregate accessor | hands back its backing collection | domain/checks.py:2812 | test_an_accessor_never_hands_back_the_backing_collection |
| TB012 | an aggregate is referenced by its ID value object, never held | entity or aggregate field | field ⟨field⟩ holds another aggregate root | domain/checks.py:2839 | test_an_aggregate_is_referenced_by_id_never_held |
| TB015 | a domain object never serializes itself — a spec is construction data, not an exit | domain object public method | returns a spec | domain/checks.py:2920 | test_domain_returns_and_spec_returns |
| TB019 | a domain object's public behavior hands back domain objects — the licensed exits are the protocol dunders, the canonical exit, and a -> None transition | domain object public method | returns ⟨types⟩ | domain/checks.py:2932 | test_domain_returns_and_spec_returns |
| TB051 | an app function declares itself with @ts.load | app module | is an undeclared module function | domain/checks.py:3007 | test_srv_and_app_statement_totality |
| TB052 | every app class declares its block | app module | declares no ts.* base | domain/checks.py:3020 | test_srv_and_app_statement_totality |
| TB052 | only an app, an app loader, an app config, an app config spec, and a config repository live in an app module | app module | is ⟨kind⟩ | domain/checks.py:3030 | test_an_app_module_holds_only_app_kinds |
| TB052 | a srv class declares its block | srv module | declares no ts.* base | domain/checks.py:3073 | test_srv_and_app_statement_totality |
| TB052 | only a host class lives in a srv module | srv module | is ⟨kind⟩ | domain/checks.py:3082 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB064 | a protocol module is context-generic and imports no context | protocol module | imports ⟨import⟩ | domain/checks.py:3125 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module never imports srv or app | protocol module | imports ⟨import⟩ | domain/checks.py:3135 | test_protocol_module_totality_is_flagged |
| TB052 | a protocol class declares its block | protocol module | declares no ts.* base | domain/checks.py:3159 | test_protocol_module_totality_is_flagged |
| TB064 | a protocol module imports nothing else from its tree | protocol module | imports ⟨import⟩ | domain/checks.py:3145 | test_a_protocol_module_imports_nothing_else_from_its_tree |
| TB052 | only protocol ports, protocol records, protocol rejections, protocol requests, and protocol responses live in a protocol module | protocol module | is ⟨kind⟩ | domain/checks.py:3168 | test_protocol_module_totality_is_flagged |
| TB042 | a ports __init__ is empty | ports `__init__` | __init__ declares code | domain/checks.py:3212 | test_a_ports_init_is_empty |
| TB052 | a ports module declares exactly one port, so no two ports can share a request or a response | ports module | declares ⟨count⟩ ports · declares no port | domain/checks.py:3514,3524 | test_a_ports_module_declares_exactly_one_port |
| TB051 | a ports module holds only imports and classes | ports module | has a loose module-level statement | domain/checks.py:3536 | test_a_ports_module_holds_only_imports_and_classes |
| TB067 | a ports module is a leaf and imports nothing from its tree, its own siblings included | ports module | imports ⟨import⟩ | domain/checks.py:3246 | test_a_ports_module_is_a_leaf |
| TB052 | a ports module declares its port and its DTOs at module level, where the one-port count can see them | ports module | is a nested class | domain/checks.py:3269 | test_a_nested_class_cannot_hide_a_second_port |
| TB051 | a ports module holds no expression that runs at import, and a metaclass is logic every adapter imports | ports module | carries a class keyword | domain/checks.py:3282 | test_a_ports_class_carries_no_keyword |
| TB051 | a ports module names concrete shapes, because a type parameter is a slot the shape rules cannot read and a bound is an expression | ports module | is generic | domain/checks.py:3296,3327 | test_a_ports_module_runs_nothing_at_import |
| TB051 | a ports module holds no expression that runs at import, and a base built by a call is logic every adapter imports | ports module | computes a base | domain/checks.py:3346 | test_a_ports_module_runs_nothing_at_import |
| TB051 | only an enum member is class-level data in a ports module, because anything else runs at import in the one application module adapters may import | ports module | carries a class-level statement | domain/checks.py:3439 | test_a_ports_class_carries_no_class_level_statement |
| TB052 | a ports class declares its block | ports module | declares no ts.* base | domain/checks.py:3479 | test_a_ports_module_holds_only_port_kinds |
| TB052 | a port DTO is never subclassed, because a response hierarchy is a union mypy cannot check for exhaustiveness | ports module | subclasses a port DTO | domain/checks.py:3504 | test_a_port_dto_is_never_subclassed |
| TB067 | a ports module imports only tesser.application and the pure stdlib | ports module | imports ⟨import⟩ | domain/checks.py:3256 | test_a_ports_module_stdlib_allowlist |
| TB051 | a ports module holds no expression that runs at import, and an annotation is evaluated like any other | ports module | computes an annotation | domain/checks.py:3316 | test_a_ports_module_computes_no_annotation |
| TB051 | a ports module holds no expression that runs at import, because every adapter imports it | ports module | carries a computed default | domain/checks.py:3367 | test_a_ports_module_runs_nothing_at_import, test_an_async_port_method_runs_nothing_at_import |
| TB051 | a ports enum is a closed set of names and nothing else, because a method or a decorator here is logic every adapter imports | ports module | carries more than its members | domain/checks.py:3422 | test_a_ports_enum_carries_nothing_but_its_members |
| TB052 | a ports enum is an enum.Enum, because a str- or int-backed member compares equal to a raw literal and reopens the typo the enum closes | ports module | is an enum.⟨enum⟩ | domain/checks.py:3467 | test_a_ports_enum_is_a_plain_enum |
| TB052 | only a port and the requests and responses it speaks live in a ports module | ports module | is ⟨kind⟩ | domain/checks.py:3488 | test_a_ports_module_holds_only_port_kinds |
| TB051 | a port method declares a shape and never a body, because a ports module holds no logic to import | port protocol method | carries a body | domain/checks.py:3652 | test_a_port_method_declares_a_shape_and_never_a_body |
| TB081 | a port declares only its public calls and __call__, because a private name is not private to anyone implementing or holding the port | port protocol method | is not a call an implementer provides | domain/checks.py:3662 | test_a_port_declares_only_the_calls_an_implementer_provides |
| TB081 | a port method speaks requests and responses declared in its own ports module, never a bare ts.Request or ts.Response, which two ports would share | port protocol method | names a shape it does not declare | domain/checks.py:3705 | test_a_port_speaks_shapes_it_declares_itself |
| TB051 | a ports module holds no decorator, because a decorator is a call that runs at import in the one application module adapters may import | ports module | is decorated | domain/checks.py:3721 | test_a_ports_module_runs_nothing_at_import |
| TB069 | a ports module holds only the shapes its rules can read, so anything else is a finding by default rather than a gap nobody enumerated | ports module | holds a ⟨node⟩ | domain/checks.py:3754 | test_a_ports_module_holds_only_shapes_the_rules_can_read |
| TB052 | an adapters module holds one adapter kind | context role module | mixes adapter kinds | domain/checks.py:3820 | test_an_adapters_module_holds_one_kind |
| TB052 | every context class declares its block | context role module | declares no ts.* base | domain/checks.py:3777 | test_placement_totality_is_flagged |
| TB052 | a host lives in srv and a protocol kind in a protocol module, never a context | context role module | is ⟨kind⟩ | domain/checks.py:3786 | test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv |
| TB052 | a kind lives only in its role module | context role module | is ⟨kind⟩, whose home is ⟨role⟩ | domain/checks.py:3796 | test_placement_totality_is_flagged, test_a_role_may_be_a_package, test_wiring_is_a_role, test_a_mapper_lives_only_in_the_application_role |
| TB061 | a context reaches another context only through its client, and only from gateways and components | context role module | imports ⟨import⟩ | domain/checks.py:3952 | test_wiring_is_a_role, test_import_matrix_is_flagged, test_only_a_gateway_reaches_a_foreign_client, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |
| TB062 | domain, client, and application import only their context, their kernels, their tesser package, and the pure stdlib | context role module | imports ⟨import⟩ | domain/checks.py:3986 | test_pure_core_stdlib_allowlist, test_nested_imports_neither_classify_nor_satisfy_presence, test_pure_core_allowlist_covers_application_and_domain_future, test_an_undeclared_package_in_a_pure_role_is_still_a_finding, test_a_pure_role_kernel_import_needs_the_kernel_to_exist |
| TB060 | only a handler imports its own context's client | context role module | imports ⟨import⟩ | domain/checks.py:3921 | test_only_a_handler_imports_its_own_client |
| TB060 | the same-context matrix is a role to itself, application to domain and client, adapters to application/ports, component to application, adapters, and client | context role module | imports ⟨import⟩ | domain/checks.py:3941 | test_import_matrix_is_flagged, test_an_adapter_reaches_application_only_through_ports |
| TB066 | of the app shell a context imports only protocol, and only from its handlers | context role module | imports ⟨import⟩ | domain/checks.py:4006 | test_a_context_role_reaches_the_app_shell_only_as_handlers_to_protocol |
| TB063 | a host reaches a context only through its handlers | srv / app module | imports ⟨import⟩ | domain/checks.py:4041 | test_srv_and_app_import_rows, test_a_denied_app_edge_is_not_form_checked |
| TB063 | the composition root never imports a host | srv / app module | imports ⟨import⟩ | domain/checks.py:4064 | test_srv_and_app_import_rows |
| TB063 | an app builds from components, clients, and adapters, never domain or application | srv / app module | imports ⟨import⟩ | domain/checks.py:4051 | test_srv_and_app_import_rows |
| TB066 | production code never imports the tests package | srv / app module | imports ⟨import⟩ | domain/checks.py:4073 | test_production_never_imports_the_tests_package |
| TB066 | an app composes the application and never imports protocol | srv / app module | imports ⟨import⟩ | domain/checks.py:4083 | test_production_never_imports_the_tests_package |
| TB070 | a test reaches only what its placement allows | test module, by where it is placed | imports ⟨import⟩, but a test placed in ⟨tier⟩ does not reach that package · imports ⟨import⟩, but a test placed in the root tests package reaches a context only through its component and client · imports ⟨import⟩, but a test placed in a kernel reaches no context · imports ⟨import⟩, but a test placed in srv reaches a context only through its handlers · imports ⟨import⟩, but a test placed in an app reaches a context only through its component, client, and adapters · imports ⟨import⟩, but a test placed in protocol reaches no context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of its own context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches no neighbouring context · imports ⟨import⟩, but a test placed in ⟨tier⟩ reaches only ⟨roles⟩ of a neighbouring context | domain/checks.py:4104,4145,4164,4184,4204,4223,4259,4270,4281 | test_a_handler_sibling_fakes_only_the_client, test_a_srv_test_reaches_a_context_only_through_its_handlers, test_a_test_reaches_only_what_its_placement_allows, test_a_repository_sibling_test_reaches_its_kind_and_application_only, test_a_component_sibling_test_mirrors_production_component_reach, test_a_client_sibling_test_reaches_only_its_own_client, test_an_app_test_reaches_a_context_like_a_production_app, test_a_protocol_test_reaches_no_context, test_a_root_test_reaches_a_context_only_through_component_and_client, test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does, test_a_context_tests_module_reaches_its_own_tests_package, test_a_placed_conftest_carries_its_tier, test_adapter_kind_and_protocol_tests_shell_reach, test_a_kernel_test_reaches_only_its_kernel |
| TB070 | a sibling test lives in a role package or an adapter kind package (handlers, gateways, repositories) | test module, by where it is placed | resolves to no test tier | domain/checks.py:4125 | test_a_test_that_resolves_to_no_tier_is_itself_a_finding, test_an_unplaced_test_module_is_still_governed |
| TB070 | an eval lives only in a gateway, the one place a sampled real-model call is honest | eval module (`eval_*.py`) | is an eval outside a gateway | domain/checks.py:4307 | test_an_eval_lives_only_in_a_gateway |
| TB071 | a test module holds tests, @ts.helper builders, and @ts.fake doubles | test module | is neither a test nor a declared helper | domain/checks.py:4388 | test_test_module_totality_is_flagged, test_the_shells_tests_keep_function_totality |
| TB071 | a test module holds only imports, tests, helpers, and fakes | test module | has a loose module-level statement | domain/checks.py:4428 | test_test_module_totality_is_flagged, test_the_shells_tests_keep_function_totality |
| TB072 | a test double declares itself with @ts.fake | test module | is an undeclared class | domain/checks.py:4405 | test_test_module_totality_is_flagged |
| TB072 | a fake implements the contract it doubles | test module | implements no application port, protocol port, client, or config repository | domain/checks.py:4418 | test_a_dotted_module_base_resolves, test_test_module_totality_is_flagged |
| TB073 | a helper takes only defaulted primitives | @ts.helper function | parameter ⟨name⟩ has no default · parameter ⟨name⟩ is not a primitive | domain/checks.py:4451,4466 | test_helper_rules_are_flagged |
| TB073 | a helper builds a spec or a DTO | @ts.helper function | returns no construction data | domain/checks.py:4477 | test_helper_rules_are_flagged, test_a_helper_builds_any_construction_data_but_never_a_protocol_or_a_domain_object |
| TB073 | a helper only constructs | @ts.helper function | has control flow | domain/checks.py:4487 | test_helper_rules_are_flagged |
| TB081 | a service depends only on ports | service `__init__` | parameter ⟨name⟩ is not a ts.Port | domain/checks.py:4511 | test_service_dependencies_must_be_ports |
| TB081 | an adapter speaks records, never domain objects | repository or gateway method | carries ⟨kind⟩ in its signature | domain/checks.py:4547 | test_records_never_carry_domain_objects, test_relative_imports_resolve_against_the_package |
| TB081 | a port speaks records, never domain objects | port protocol method | carries ⟨kind⟩ in its signature | domain/checks.py:4547 | test_records_never_carry_domain_objects |
| TB080 | a value object constructs from primitives and value objects | value object `__init__` | parameter ⟨name⟩ is not allowed | domain/checks.py:4582 | test_domain_field_rules_are_flagged |
| TB080 | a spec only carries construction data | spec class | defines a method on a spec | domain/checks.py:4605 | test_domain_field_rules_are_flagged |
| TB080 | a spec field is a primitive, a value object, or a child spec | spec class | parameter ⟨name⟩ is not allowed | domain/checks.py:4620 | test_domain_field_rules_are_flagged, test_optional_construction_data_is_the_only_union |
| TB080 | a port DTO declares its fields as __init__ parameters, where the field rules can read them | request/response DTO | carries a class-level statement | domain/checks.py:4663 | test_a_dto_declares_its_fields_where_the_rules_can_read_them |
| TB080 | a DTO declares its fields as named __init__ parameters, where the field rules can read them | request/response DTO | uses *args/**kwargs | domain/checks.py:4680 | test_a_dto_declares_its_fields_where_the_rules_can_read_them |
| TB080 | a DTO carries data and nothing else | request/response DTO | defines a method on a DTO | domain/checks.py:4690 | test_domain_field_rules_are_flagged, test_an_async_method_on_a_dto_is_still_a_method |
| TB080 | a port DTO constructor only assigns its parameters, because a ports module holds no logic to import | request/response DTO | carries logic | domain/checks.py:4732 | test_a_port_dto_constructor_only_assigns_its_parameters |
| TB080 | a port DTO field is never a bare bool — model the outcome as an enum | request/response DTO | field ⟨name⟩ is a bool | domain/checks.py:4751 | test_a_port_dto_field_is_never_a_bare_bool |
| TB080 | a port DTO field is never a union, optional included — model the outcome as an enum | request/response DTO | field ⟨name⟩ is a union | domain/checks.py:4762 | test_a_port_dto_field_is_never_a_union |
| TB080 | a DTO field is a primitive or another DTO | request/response DTO | parameter ⟨name⟩ is not allowed | domain/checks.py:4780 | test_domain_field_rules_are_flagged, test_a_client_dto_with_a_sibling_enum_stays_strict |
| TB080 | a mapper is named for what it maps to, because its parameters already say what it maps from | mapper class | does not start with MapTo | domain/checks.py:4797 | test_mapper_shape_rules_are_flagged |
| TB080 | a mapper originates nothing — every value it exposes comes from what it was given | mapper class | carries the literal ⟨literal⟩ | domain/checks.py:4886 | test_mapper_shape_rules_are_flagged |
| TB080 | a mapper holds only __init__ and the accessors it exposes | mapper class | is a method | domain/checks.py:4837 | test_mapper_shape_rules_are_flagged |
| TB080 | a nested mapper accessor ends in _mapper, so the reader knows to keep dotting | mapper class | returns a mapper | domain/checks.py:4851 | test_mapper_shape_rules_are_flagged |
| TB080 | a mapper takes whole objects, never a field already pulled off one | mapper class | parameter ⟨name⟩ is a primitive | domain/checks.py:4819 | test_mapper_shape_rules_are_flagged |
| TB080 | a mapper exposes the parts and the caller assembles them, so every field is named where it is read | mapper class | constructs what it maps to | domain/checks.py:4871 | test_a_mapper_that_constructs_its_target_is_flagged |
| TB082 | a value crossing into a port has passed through a domain type | public service method | sends ⟨field⟩ from its request straight to a port | domain/checks.py:4927 | test_a_raw_request_value_reaching_a_port_is_flagged |
| TB081 | a component releases what it constructed | component class | defines no close | domain/checks.py:4942 | test_a_component_releases_what_it_constructed |
| TB080 | an aggregate constructs from exactly one ts.Spec | aggregate class | defines no __init__ | domain/checks.py:4968 | test_aggregate_constructor_violations_are_flagged |
| TB080 | an entity constructs from exactly one ts.Spec | entity class | defines no __init__ | domain/checks.py:4968 | test_domain_field_rules_are_flagged |
| TB080 | a config constructs from exactly one ts.Spec | config class | defines no __init__ | domain/checks.py:4994,5020 | test_a_config_constructs_from_exactly_one_spec |
| TB080 | a domain constructor takes exactly one ts.Spec | aggregate or entity `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain/checks.py:5062,5071,5082 | test_aggregate_constructor_violations_are_flagged |
| TB080 | a config constructor takes exactly one ts.Spec | config `__init__` | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Spec | domain/checks.py:5062,5071,5082 | test_a_config_constructs_from_exactly_one_spec |
| TB081 | a port method takes exactly one ts.Request | port protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:5062,5071,5082 | test_a_port_method_speaks_one_request_and_one_response, test_a_port_method_shape_survives_async_and_dunder_call |
| TB081 | a port method returns a ts.Response | port protocol method | does not return a ts.Response | domain/checks.py:5095 | test_a_port_method_speaks_one_request_and_one_response |
| TB081 | a client method takes exactly one ts.Request | client protocol method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:5062,5071,5082 | test_client_method_rules_are_flagged |
| TB081 | a client method returns a ts.Response | client protocol method | does not return a ts.Response | domain/checks.py:5095 | test_client_method_rules_are_flagged |
| TB081 | a service method takes exactly one ts.Request | public service method | uses *args/**kwargs · takes ⟨count⟩ parameters · parameter ⟨name⟩ is not a ts.Request | domain/checks.py:5062,5071,5082 | test_primitive_parameter_and_return_are_flagged, test_arity_and_missing_annotations_are_flagged |
| TB081 | a service method returns a ts.Response | public service method | does not return a ts.Response | domain/checks.py:5095 | test_primitive_parameter_and_return_are_flagged, test_indirect_subclass_still_classifies |
| TB082 | a service inlines its logic | every service method, including private | delegates to self.⟨method⟩ · delegates to ⟨function⟩ | domain/checks.py:5125,5134 | test_service_delegation_is_flagged |
| TB082 | a service method names what it computes, and reads an accessor where it is used | public service method | names a straight accessor | domain/checks.py:5160 | test_a_straight_accessor_local_is_flagged |
| TB082 | a service method names what it computes in a local, and passes a name, a reader, or a declared kind | public service method | computes in an argument | domain/checks.py:5178 | test_computing_in_an_argument_and_assembling_from_two_readers_are_flagged |
| TB082 | a declared kind is assembled from the accessors of one mapper | public service method | assembles from ⟨count⟩ readers | domain/checks.py:5207 | test_computing_in_an_argument_and_assembling_from_two_readers_are_flagged |
| TB082 | a service method satisfies a condition with one domain call | public service method | if condition is not a single call · match subject is not a single call | domain/checks.py:5219,5250 | test_service_body_rules_are_flagged |
| TB082 | a service method branches one level deep | public service method | nests a conditional | domain/checks.py:5240,5264 | test_service_body_rules_are_flagged, test_elif_chain_is_one_level |
| TB050 | a tesser import is module-level | role, srv/app, or test module | imports ⟨import⟩ inside a function | domain/checks.py:5278 | test_protocol_module_totality_is_flagged, test_nested_imports_neither_classify_nor_satisfy_presence |
| TB043 | a relative import resolves inside the tree | role, srv/app, or test module | imports ⟨import⟩ beyond the package root | domain/checks.py:5288 | test_relative_imports_resolve_against_the_package |
| TB053 | a context module is imported as an aliased module, never its members | direction-legal context import (role modules and their __init__, srv/app, test modules) | imports names from ⟨import⟩ · imports ⟨import⟩ without an alias | domain/checks.py:5304,5314 | test_role_init_only_reexports_its_own_role, test_a_role_init_may_import_a_module_but_never_a_class, test_context_module_import_form, test_relative_imports_resolve_against_the_package, test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges |

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
