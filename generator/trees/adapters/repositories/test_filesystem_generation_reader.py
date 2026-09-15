from __future__ import annotations

import pathlib

import trees.adapters.repositories as repositories
import trees.application.ports as ports


class TestFilesystemGenerationReader:

    def test_a_spec_file_reads_whole(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text(
            'app_name = "voice"\n'
            'bounded_context_name = "calls"\n'
            'aggregate_root_class_name = "Call"\n'
            'durable_execution_engine = "restate"\n'
            'database = "postgres"\n'
            'identity_field_name = "call_id"\n'
            'identity_port_operation_name = "issue_call_id"\n'
            '[aggregate_fields]\nperson_name = "str"\nage = "int"\n'
            '[sample_values]\ncall_id = ["call-1", "call-2"]\nperson_name = ["Ada", "Grace"]\nage = [36, 85]\n'
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
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path / "templates"))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec == ports.SpecRecord(
            state=ports.SpecState.READ,
            note="",
            unknown_keys=(),
            app_name="voice",
            bounded_context_name="calls",
            aggregate_root_class_name="Call",
            durable_execution_engine="restate",
            database="postgres",
            identity_field_name="call_id",
            identity_port_operation_name="issue_call_id",
            aggregate_fields=(
                ports.FieldRecord(name="person_name", kind="str"),
                ports.FieldRecord(name="age", kind="int"),
            ),
            sample_values=(
                ports.SampleRecord(
                    name="call_id",
                    values=(ports.ValueRecord(kind="str", text="call-1"), ports.ValueRecord(kind="str", text="call-2")),
                ),
                ports.SampleRecord(
                    name="person_name",
                    values=(ports.ValueRecord(kind="str", text="Ada"), ports.ValueRecord(kind="str", text="Grace")),
                ),
                ports.SampleRecord(
                    name="age",
                    values=(ports.ValueRecord(kind="int", text="36"), ports.ValueRecord(kind="int", text="85")),
                ),
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
            random_values=(ports.ValueRecord(kind="str", text="Ada"), ports.ValueRecord(kind="str", text="Grace")),
            storage_url_variable="CALLS_STORAGE",
            restate_ingress_url_variable="RESTATE_INGRESS",
        )

    def test_every_key_the_spec_does_not_take_is_named_by_its_path(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text(
            'app_name = "voice"\napp = "voice"\n'
            '[client]\nwrite_operation = "place_call"\n'
            '[aggregate_fields]\nperson_name = "str"\n'
            '[port]\nsave = "save_call"\n'
        )
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec.unknown_keys == ("app", "client.write_operation", "port")

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
        assert read_generation_response.spec.app_name == ""

    def test_a_spec_file_that_is_not_toml_is_malformed(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text("app_name = \n")
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

    def test_a_value_of_the_wrong_type_reads_as_nothing_or_as_an_other_value(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "spec.toml").write_text(
            "app_name = 1\n"
            "[aggregate_fields]\nperson_name = 2\n"
            '[sample_values]\nperson_name = [true, 1.5]\ncall_id = "call-1"\n'
            '[client]\nread_response_fields = "person_name"\n'
        )
        filesystem_generation_reader = repositories.FilesystemGenerationReader(str(tmp_path))

        read_generation_response = filesystem_generation_reader.read_generation(
            ports.ReadGenerationRequest(spec_path=str(tmp_path / "spec.toml"), out_dir=str(tmp_path / "out"))
        )

        assert read_generation_response.spec.app_name == ""
        assert read_generation_response.spec.aggregate_fields == (ports.FieldRecord(name="person_name", kind=""),)
        assert read_generation_response.spec.sample_values == (
            ports.SampleRecord(
                name="person_name",
                values=(ports.ValueRecord(kind="other", text=""), ports.ValueRecord(kind="other", text="")),
            ),
            ports.SampleRecord(name="call_id", values=()),
        )
        assert read_generation_response.spec.read_response_fields == ()
