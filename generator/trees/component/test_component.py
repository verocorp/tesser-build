from __future__ import annotations

import pathlib

import trees.client as client
import trees.component as component


class TestConfig:

    def test_a_config_carries_the_templates_root(self) -> None:
        config = component.Config(component.Spec(templates_root="/templates"))

        assert config.templates_root == "/templates"


class TestTrees:

    def test_the_built_client_renders_the_templates_it_is_pointed_at_into_the_output_directory(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "templates" / "{{context}}").mkdir(parents=True)
        (tmp_path / "templates" / "{{context}}" / "{{aggregate}}.py.tmpl").write_text("class {{Aggregate}}:\n")
        (tmp_path / "spec.toml").write_text(
            'app_name = "voice"\n'
            'bounded_context_name = "calls"\n'
            'aggregate_root_class_name = "Call"\n'
            'durable_execution_engine = "restate"\n'
            'database = "postgres"\n'
            'identity_field_name = "call_id"\n'
            'identity_port_operation_name = "issue_call_id"\n'
            '[aggregate_fields]\nperson_name = "str"\n'
            '[sample_values]\ncall_id = ["call-1", "call-2"]\nperson_name = ["Ada", "Grace"]\n'
            '[client]\nwrite_operation_name = "place_call"\nread_operation_name = "get_call"\n'
            'read_response_fields = ["call_id", "person_name"]\n'
            '[orchestrator]\noperation_name = "conduct_call"\n'
            '[action]\noperation_name = "record_call"\n'
            '[repository]\nsave_operation_name = "save_call"\nload_operation_name = "load_call"\n'
            'load_response_collection_name = "calls"\n'
            '[acceptance_test]\ntest_class_name = "TestPlacingCalls"\n'
            'test_method_name = "test_a_call_is_successfully_made"\nasserted_field = "person_name"\n'
            'random_values = ["Ada", "Grace"]\n'
            '[environment_variables]\nstorage_url = "CALLS_STORAGE"\nrestate_ingress_url = "RESTATE_INGRESS"\n'
        )
        trees = component.Trees(component.Config(component.Spec(templates_root=str(tmp_path / "templates"))))

        generate_tree_response = trees.client.generate_tree(
            client.GenerateTreeRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )
        trees.close()

        assert generate_tree_response.problems == ()
        assert (tmp_path / "out" / "calls" / "call.py").read_text() == "class Call:\n"

    def test_the_built_client_turns_a_missing_spec_file_into_a_problem(self, tmp_path: pathlib.Path) -> None:
        trees = component.Trees(component.Config(component.Spec(templates_root=str(tmp_path))))

        generate_tree_response = trees.client.generate_tree(
            client.GenerateTreeRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )
        trees.close()

        assert generate_tree_response.problems == (f"there is no spec file at {tmp_path / 'spec.toml'}",)
        assert not (tmp_path / "out").exists()
