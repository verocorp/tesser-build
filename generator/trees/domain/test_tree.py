from __future__ import annotations

import pytest

import tesser.testing as ts

import trees.domain as domain


@ts.helper
def tree_spec(
    state: str = "read",
    target: str = "absent",
    aggregate_root_class_name: str = "Call",
    durable_execution_engine: str = "restate",
    person_name_kind: str = "str",
    person_name_sample_kind: str = "str",
    person_name_first_sample: str = "Ada",
    person_name_second_sample: str = "Grace",
    write_operation_name: str = "place_call",
    asserted_field: str = "person_name",
    random_value_kind: str = "str",
    random_value: str = "Ada",
    template_path: str = "{{context}}/domain/{{aggregate}}.py.tmpl",
    template_text: str = "class {{Aggregate}}:\n",
) -> domain.TreeSpec:
    return domain.TreeSpec(
        state=state,
        note="spec.toml",
        unknown_keys=(),
        target=target,
        app_name="voice",
        bounded_context_name="calls",
        aggregate_root_class_name=aggregate_root_class_name,
        durable_execution_engine=durable_execution_engine,
        database="postgres",
        identity_field_name="call_id",
        identity_port_operation_name="issue_call_id",
        aggregate_fields=(("person_name", person_name_kind), ("phone_number", "str")),
        sample_values=(
            ("call_id", (("str", "call-1"), ("str", "call-2"))),
            (
                "person_name",
                ((person_name_sample_kind, person_name_first_sample), (person_name_sample_kind, person_name_second_sample)),
            ),
            ("phone_number", (("str", "+15555550100"), ("str", "+15555550101"))),
        ),
        write_operation_name=write_operation_name,
        read_operation_name="get_call",
        read_response_fields=("call_id", "person_name"),
        orchestrator_operation_name="conduct_call",
        action_operation_name="record_call",
        save_operation_name="save_call",
        load_operation_name="load_call",
        load_response_collection_name="calls",
        test_class_name="TestPlacingCalls",
        test_method_name="test_a_call_is_successfully_made",
        asserted_field=asserted_field,
        random_values=((random_value_kind, random_value),),
        storage_url_variable="CALLS_STORAGE",
        restate_ingress_url_variable="RESTATE_INGRESS",
        templates=((template_path, template_text),),
    )


@ts.helper
def tree_spec_naming_an_unknown_key(unknown_key: str = "client.write_operation") -> domain.TreeSpec:
    return domain.TreeSpec(
        state="read",
        note="spec.toml",
        unknown_keys=(unknown_key,),
        target="absent",
        app_name="voice",
        bounded_context_name="calls",
        aggregate_root_class_name="Call",
        durable_execution_engine="restate",
        database="postgres",
        identity_field_name="call_id",
        identity_port_operation_name="issue_call_id",
        aggregate_fields=(("person_name", "str"),),
        sample_values=(
            ("call_id", (("str", "call-1"), ("str", "call-2"))),
            ("person_name", (("str", "Ada"), ("str", "Grace"))),
        ),
        write_operation_name="place_call",
        read_operation_name="get_call",
        read_response_fields=("call_id", "person_name"),
        orchestrator_operation_name="conduct_call",
        action_operation_name="record_call",
        save_operation_name="save_call",
        load_operation_name="load_call",
        load_response_collection_name="calls",
        test_class_name="TestPlacingCalls",
        test_method_name="test_a_call_is_successfully_made",
        asserted_field="person_name",
        random_values=(("str", "Ada"),),
        storage_url_variable="CALLS_STORAGE",
        restate_ingress_url_variable="RESTATE_INGRESS",
        templates=(("{{context}}/domain/{{aggregate}}.py.tmpl", "class {{Aggregate}}:\n"),),
    )


class TestTreeRendering:

    def test_a_template_path_and_its_text_render_from_the_spec(self) -> None:
        tree = domain.Tree(tree_spec())

        assert tree.health() is domain.Health.CLEAN
        assert [(str(generated_file.path()), str(generated_file.content())) for generated_file in tree.files()] == [
            ("calls/domain/call.py", "class Call:\n")
        ]

    def test_a_pascal_case_aggregate_root_names_its_modules_in_snake_case(self) -> None:
        tree = domain.Tree(
            tree_spec(aggregate_root_class_name="PurchaseOrder", template_text="{{aggregate}} {{Aggregate}}")
        )

        assert [(str(generated_file.path()), str(generated_file.content())) for generated_file in tree.files()] == [
            ("calls/domain/purchase_order.py", "purchase_order PurchaseOrder")
        ]

    def test_a_list_section_repeats_once_per_field_and_the_last_takes_no_comma(self) -> None:
        tree = domain.Tree(
            tree_spec(template_text="({{#record_fields}}{{field}}: {{py_type}}{{comma}}{{/record_fields}})")
        )

        assert str(tree.files()[0].content()) == "(call_id: str, person_name: str, phone_number: str)"

    def test_a_section_alone_on_its_line_takes_its_line_with_it(self) -> None:
        tree = domain.Tree(tree_spec(template_text="a\n{{#fields}}\n{{field}}\n{{/fields}}\nb\n"))

        assert str(tree.files()[0].content()) == "a\nperson_name\nphone_number\nb\n"

    def test_a_field_flag_opens_and_inverts_a_section_inside_a_list_section(self) -> None:
        tree = domain.Tree(
            tree_spec(
                template_text=(
                    "{{#record_fields}}{{#is_identity}}{{Field}}:{{/is_identity}}"
                    "{{^is_identity}}{{field}} {{/is_identity}}{{/record_fields}}"
                )
            )
        )

        assert str(tree.files()[0].content()) == "CallId:person_name phone_number "

    def test_the_prose_joins_three_fields_with_commas_and_a_final_and(self) -> None:
        tree = domain.Tree(tree_spec(template_text="{{#record_fields}}{{prose}}a {{field}}{{/record_fields}}"))

        assert str(tree.files()[0].content()) == "a call_id, a person_name, and a phone_number"

    def test_the_sample_values_render_as_literals_beside_a_value_of_the_wrong_type(self) -> None:
        tree = domain.Tree(
            tree_spec(template_text="{{#record_fields}}{{field}}={{sample}}/{{sample2}}/{{wrong}};{{/record_fields}}")
        )

        assert str(tree.files()[0].content()) == (
            'call_id="call-1"/"call-2"/1;person_name="Ada"/"Grace"/1;phone_number="+15555550100"/"+15555550101"/1;'
        )

    def test_an_int_field_renders_unquoted_samples_and_its_int_exit(self) -> None:
        tree = domain.Tree(
            tree_spec(
                person_name_kind="int",
                person_name_sample_kind="int",
                person_name_first_sample="1",
                person_name_second_sample="2",
                random_value_kind="int",
                random_value="3",
                template_text="{{#fields}}{{field}}={{sample}} {{wrong}} {{dunder}} {{sql_type}};{{/fields}}{{random_choices}}",
            )
        )

        assert str(tree.files()[0].content()) == (
            'person_name=1 "1" __int__ bigint;phone_number="+15555550100" 1 __str__ text;(3,)'
        )

    def test_the_names_the_spec_gives_and_the_names_derived_from_them(self) -> None:
        tree = domain.Tree(
            tree_spec(
                template_text=(
                    "{{Identity}} {{issue}} {{Issue}} {{Conduct}} {{conduct_words}} {{App}}App "
                    "{{collection}} {{identity_raw}} {{test_class}}.{{test_method}} {{random_choices}}"
                )
            )
        )

        assert str(tree.files()[0].content()) == (
            "CallId issue_call_id IssueCallId ConductCall conduct call VoiceApp "
            'calls call-1 TestPlacingCalls.test_a_call_is_successfully_made ("Ada",)'
        )

    def test_a_name_the_spec_does_not_bind_is_a_template_error(self) -> None:
        with pytest.raises(ValueError):
            domain.Tree(tree_spec(template_text="{{nothing}}"))

    def test_a_section_that_never_closes_is_a_template_error(self) -> None:
        with pytest.raises(ValueError):
            domain.Tree(tree_spec(template_text="{{#fields}}never closed"))


class TestTreeProblems:

    def test_an_engine_without_templates_is_a_problem_and_nothing_renders(self) -> None:
        tree = domain.Tree(tree_spec(durable_execution_engine="temporal"))

        assert tree.health() is domain.Health.PROBLEMS
        assert [str(text) for text in tree.problems()] == [
            "durable_execution_engine 'temporal' has no templates; the one engine is 'restate'"
        ]
        assert tree.files() == ()

    def test_a_key_the_spec_does_not_take_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec_naming_an_unknown_key(unknown_key="client.write_operation"))

        assert [str(text) for text in tree.problems()] == [
            "the spec names 'client.write_operation', which is not a key the spec takes"
        ]

    def test_a_missing_spec_file_is_the_one_problem(self) -> None:
        tree = domain.Tree(tree_spec(state="missing"))

        assert [str(text) for text in tree.problems()] == ["there is no spec file at spec.toml"]

    def test_an_occupied_output_directory_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(target="occupied"))

        assert [str(text) for text in tree.problems()] == ["the output directory is not empty"]

    def test_an_operation_named_twice_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(write_operation_name="record_call"))

        assert [str(text) for text in tree.problems()] == [
            "operation 'record_call' is named twice; every operation has a name of its own"
        ]

    def test_an_operation_of_one_word_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(write_operation_name="place"))

        assert [str(text) for text in tree.problems()] == [
            "client.write_operation_name 'place' is not a snake_case verb and noun, like place_call"
        ]

    def test_a_field_type_without_templates_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(person_name_kind="float"))

        assert [str(text) for text in tree.problems()] == [
            "aggregate_fields names 'person_name' as 'float'; a field is one of str, int"
        ]

    def test_sample_values_of_the_wrong_type_are_a_problem(self) -> None:
        tree = domain.Tree(
            tree_spec(person_name_sample_kind="int", person_name_first_sample="1", person_name_second_sample="2")
        )

        assert [str(text) for text in tree.problems()] == [
            "sample_values for 'person_name' holds a value that is not a str"
        ]

    def test_a_sample_value_carrying_a_quote_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(person_name_first_sample='O"Brien'))

        assert [str(text) for text in tree.problems()] == [
            "sample value 'O\"Brien' for 'person_name' is not printable ASCII free of quotes and backslashes"
        ]

    def test_sample_values_that_repeat_are_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(person_name_second_sample="Ada"))

        assert [str(text) for text in tree.problems()] == [
            "sample_values for 'person_name' repeats a value; its values differ"
        ]

    def test_an_assertion_on_a_field_the_read_does_not_answer_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(asserted_field="phone_number"))

        assert [str(text) for text in tree.problems()] == [
            "acceptance_test.asserted_field 'phone_number' is not an aggregate field the client read answers"
        ]

    def test_random_values_of_the_wrong_type_are_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(random_value_kind="int", random_value="3"))

        assert [str(text) for text in tree.problems()] == [
            "acceptance_test.random_values holds a value that is not a str"
        ]


class TestGenerationPaths:

    def test_the_paths_come_back_as_they_were_given(self) -> None:
        generation_paths = domain.GenerationPaths(
            domain.GenerationPathsSpec(spec_path="specs/voice.toml", out_dir="/tmp/voice")
        )

        assert (str(generation_paths.spec_path()), str(generation_paths.out_dir())) == (
            "specs/voice.toml",
            "/tmp/voice",
        )
