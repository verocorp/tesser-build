from __future__ import annotations

import pathlib

import trees.adapters.repositories as repositories
import trees.application.ports as ports


class TestFilesystemGenerationReader:

    def test_a_spec_file_reads_whole(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text(
            'app = "voice"\ncontext = "calls"\naggregate = "Call"\nengine = "restate"\nstore = "postgres"\n'
            '[identity]\nname = "call_id"\nminted_by = "domain"\n'
            '[fields]\nperson_name = "str"\nphone_number = "str"\n'
            '[client]\nwrite = "place_call"\nread = "get_call"\nread_answers = ["call_id", "person_name"]\n'
            '[orchestrator]\noperation = "conduct_call"\n'
            '[action]\noperation = "record_call"\n'
            '[port]\nsave = "save_call"\nload = "load_call"\n'
            '[acceptance]\nasserts = "person_name"\n'
            '[env]\nstorage = "CALLS_STORAGE"\ningress = "RESTATE_INGRESS"\n'
        )
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path / "templates"))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec == ports.SpecRecord(
            state=ports.SpecState.READ,
            note="",
            app="voice",
            context="calls",
            aggregate="Call",
            engine="restate",
            store="postgres",
            identity="call_id",
            minted_by="domain",
            fields=(
                ports.FieldRecord(name="person_name", kind="str"),
                ports.FieldRecord(name="phone_number", kind="str"),
            ),
            write="place_call",
            read="get_call",
            read_answers=("call_id", "person_name"),
            orchestrator="conduct_call",
            action="record_call",
            save="save_call",
            load="load_call",
            asserts="person_name",
            storage_env="CALLS_STORAGE",
            ingress_env="RESTATE_INGRESS",
        )

    def test_the_templates_are_every_tmpl_file_under_the_root_by_relative_path(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "templates" / "{{context}}" / "domain").mkdir(parents=True)
        (tmp_path / "templates" / "{{context}}" / "domain" / "{{aggregate}}.py.tmpl").write_text("class {{Aggregate}}:\n")
        (tmp_path / "templates" / ".tesser-root.tmpl").write_text("app\n")
        (tmp_path / "templates" / "README.md").write_text("not a template\n")
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path / "templates"))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.templates == (
            ports.TemplateRecord(path=".tesser-root.tmpl", text="app\n"),
            ports.TemplateRecord(path="{{context}}/domain/{{aggregate}}.py.tmpl", text="class {{Aggregate}}:\n"),
        )

    def test_an_output_directory_that_does_not_exist_is_absent(self, tmp_path: pathlib.Path) -> None:
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.target == ports.TargetRecord(state=ports.TargetState.ABSENT)

    def test_an_output_directory_with_nothing_in_it_is_empty(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "out").mkdir()
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.target == ports.TargetRecord(state=ports.TargetState.EMPTY)

    def test_an_output_directory_with_a_file_in_it_is_occupied(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "out").mkdir()
        (tmp_path / "out" / "kept.txt").write_text("kept\n")
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.target == ports.TargetRecord(state=ports.TargetState.OCCUPIED)

    def test_a_missing_spec_file_is_missing_and_names_its_path(self, tmp_path: pathlib.Path) -> None:
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec.state is ports.SpecState.MISSING
        assert read_generation_response.spec.note == str(tmp_path / "spec.toml")
        assert read_generation_response.spec.app == ""

    def test_a_spec_file_that_is_not_toml_is_malformed(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text("app = \n")
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec.state is ports.SpecState.MALFORMED
        assert read_generation_response.spec.note != ""

    def test_a_spec_file_that_is_not_utf8_is_unreadable(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_bytes(b"\xff\xfe\x00app")
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec.state is ports.SpecState.UNREADABLE

    def test_a_value_of_the_wrong_type_reads_as_nothing(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text(
            'app = 1\n[fields]\nperson_name = 2\n[client]\nread_answers = "person_name"\n'
        )
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec.app == ""
        assert read_generation_response.spec.fields == (ports.FieldRecord(name="person_name", kind=""),)
        assert read_generation_response.spec.read_answers == ()
