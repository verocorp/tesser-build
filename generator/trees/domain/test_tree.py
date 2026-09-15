from __future__ import annotations

import pytest

import tesser.testing as ts

import trees.domain as domain


@ts.helper
def tree_spec(
    state: str = "read",
    target: str = "absent",
    aggregate: str = "Call",
    engine: str = "restate",
    minted_by: str = "domain",
    field_kind: str = "str",
    write: str = "place_call",
    asserts: str = "person_name",
    template_path: str = "{{context}}/domain/{{aggregate}}.py.tmpl",
    template_text: str = "class {{Aggregate}}:\n",
) -> domain.TreeSpec:
    return domain.TreeSpec(
        state=state,
        note="spec.toml",
        target=target,
        app="voice",
        context="calls",
        aggregate=aggregate,
        engine=engine,
        store="postgres",
        identity="call_id",
        minted_by=minted_by,
        fields=(("person_name", field_kind), ("phone_number", "str")),
        write=write,
        read="get_call",
        read_answers=("call_id", "person_name"),
        orchestrator="conduct_call",
        action="record_call",
        save="save_call",
        load="load_call",
        asserts=asserts,
        storage_env="CALLS_STORAGE",
        ingress_env="RESTATE_INGRESS",
        templates=((template_path, template_text),),
    )


class TestTreeRendering:

    def test_a_template_path_and_its_text_render_from_the_spec(self) -> None:
        tree = domain.Tree(tree_spec())

        assert tree.health() is domain.Health.CLEAN
        assert [(str(generated_file.path()), str(generated_file.content())) for generated_file in tree.files()] == [
            ("calls/domain/call.py", "class Call:\n")
        ]

    def test_a_pascal_case_aggregate_names_its_modules_in_snake_case(self) -> None:
        tree = domain.Tree(tree_spec(aggregate="PurchaseOrder", template_text="{{aggregate}} {{Aggregate}}"))

        assert [(str(generated_file.path()), str(generated_file.content())) for generated_file in tree.files()] == [
            ("calls/domain/purchase_order.py", "purchase_order PurchaseOrder")
        ]

    def test_a_list_section_repeats_once_per_field_and_the_last_takes_no_comma(self) -> None:
        tree = domain.Tree(
            tree_spec(template_text="({{#record_fields}}{{field}}: {{py_type}}{{comma}}{{/record_fields}})")
        )

        assert str(tree.files()[0].content()) == "(call_id: str, person_name: str, phone_number: str)"

    def test_a_section_alone_on_its_line_takes_its_line_with_it(self) -> None:
        text = "a\n{{#domain_mints}}\nimport uuid\n{{/domain_mints}}\nb\n"

        minted_in_the_domain = domain.Tree(tree_spec(template_text=text))
        minted_by_the_store = domain.Tree(tree_spec(minted_by="store", template_text=text))

        assert str(minted_in_the_domain.files()[0].content()) == "a\nimport uuid\nb\n"
        assert str(minted_by_the_store.files()[0].content()) == "a\nb\n"

    def test_an_inverted_section_renders_only_when_its_flag_is_off(self) -> None:
        text = "{{^domain_mints}}given{{/domain_mints}}"

        minted_in_the_domain = domain.Tree(tree_spec(template_text=text))
        minted_by_the_client = domain.Tree(tree_spec(minted_by="client", template_text=text))

        assert str(minted_in_the_domain.files()[0].content()) == ""
        assert str(minted_by_the_client.files()[0].content()) == "given"

    def test_a_field_flag_opens_a_section_inside_a_list_section(self) -> None:
        tree = domain.Tree(
            tree_spec(template_text="{{#record_fields}}{{#is_identity}}{{Field}}{{/is_identity}}{{/record_fields}}")
        )

        assert str(tree.files()[0].content()) == "CallId"

    def test_the_prose_joins_three_fields_with_commas_and_a_final_and(self) -> None:
        tree = domain.Tree(tree_spec(template_text="{{#record_fields}}{{prose}}a {{field}}{{/record_fields}}"))

        assert str(tree.files()[0].content()) == "a call_id, a person_name, and a phone_number"

    def test_an_int_field_takes_an_unquoted_sample_and_its_int_exit(self) -> None:
        tree = domain.Tree(
            tree_spec(field_kind="int", template_text="{{#fields}}{{field}}={{sample}} {{dunder}} {{sql_type}};{{/fields}}")
        )

        assert str(tree.files()[0].content()) == (
            'person_name=1 __int__ bigint;phone_number="phone_number-1" __str__ text;'
        )

    def test_an_identity_the_domain_does_not_mint_is_construction_data(self) -> None:
        text = "{{#spec_fields}}{{field}} {{/spec_fields}}|{{#write_fields}}{{field}} {{/write_fields}}"

        minted_in_the_domain = domain.Tree(tree_spec(template_text=text))
        minted_by_the_store = domain.Tree(tree_spec(minted_by="store", template_text=text))
        minted_by_the_client = domain.Tree(tree_spec(minted_by="client", template_text=text))

        assert str(minted_in_the_domain.files()[0].content()) == "person_name phone_number |person_name phone_number "
        assert str(minted_by_the_store.files()[0].content()) == (
            "call_id person_name phone_number |person_name phone_number "
        )
        assert str(minted_by_the_client.files()[0].content()) == (
            "call_id person_name phone_number |call_id person_name phone_number "
        )

    def test_the_derived_operation_and_class_names(self) -> None:
        tree = domain.Tree(
            tree_spec(template_text="{{Identity}} {{issue}} {{Issue}} {{Conduct}} {{conduct_words}} {{App}}App")
        )

        assert str(tree.files()[0].content()) == "CallId issue_call_id IssueCallId ConductCall conduct call VoiceApp"

    def test_a_name_the_spec_does_not_bind_is_a_template_error(self) -> None:
        with pytest.raises(ValueError):
            domain.Tree(tree_spec(template_text="{{nothing}}"))

    def test_a_section_that_never_closes_is_a_template_error(self) -> None:
        with pytest.raises(ValueError):
            domain.Tree(tree_spec(template_text="{{#fields}}never closed"))


class TestTreeProblems:

    def test_an_engine_without_templates_is_a_problem_and_nothing_renders(self) -> None:
        tree = domain.Tree(tree_spec(engine="temporal"))

        assert tree.health() is domain.Health.PROBLEMS
        assert [str(text) for text in tree.problems()] == [
            "engine 'temporal' has no templates; the one engine is 'restate'"
        ]
        assert tree.files() == ()

    def test_a_missing_spec_file_is_the_one_problem(self) -> None:
        tree = domain.Tree(tree_spec(state="missing"))

        assert [str(text) for text in tree.problems()] == ["there is no spec file at spec.toml"]

    def test_an_occupied_output_directory_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(target="occupied"))

        assert [str(text) for text in tree.problems()] == ["the output directory is not empty"]

    def test_an_operation_named_twice_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(write="record_call"))

        assert [str(text) for text in tree.problems()] == [
            "operation 'record_call' is named twice; every operation has a name of its own"
        ]

    def test_an_operation_of_one_word_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(write="place"))

        assert [str(text) for text in tree.problems()] == [
            "client write 'place' is not a snake_case verb and noun, like place_call"
        ]

    def test_a_field_type_without_templates_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(field_kind="float"))

        assert [str(text) for text in tree.problems()] == [
            "field 'person_name' is a 'float'; a field is one of str, int"
        ]

    def test_an_assertion_on_a_field_the_read_does_not_answer_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(asserts="phone_number"))

        assert [str(text) for text in tree.problems()] == [
            "acceptance asserts 'phone_number', which the client read does not answer"
        ]

    def test_an_unknown_minter_is_a_problem(self) -> None:
        tree = domain.Tree(tree_spec(minted_by="nobody"))

        assert [str(text) for text in tree.problems()] == [
            "identity minted_by 'nobody' is not one of domain, store, client"
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
