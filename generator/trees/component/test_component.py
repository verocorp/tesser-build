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
            'app = "voice"\ncontext = "calls"\naggregate = "Call"\nengine = "restate"\nstore = "postgres"\n'
            '[identity]\nname = "call_id"\nminted_by = "domain"\n'
            '[fields]\nperson_name = "str"\n'
            '[client]\nwrite = "place_call"\nread = "get_call"\nread_answers = ["person_name"]\n'
            '[orchestrator]\noperation = "conduct_call"\n'
            '[action]\noperation = "record_call"\n'
            '[port]\nsave = "save_call"\nload = "load_call"\n'
            '[acceptance]\nasserts = "person_name"\n'
            '[env]\nstorage = "CALLS_STORAGE"\ningress = "RESTATE_INGRESS"\n'
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
