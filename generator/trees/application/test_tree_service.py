from __future__ import annotations

import tesser.testing as ts

import trees.application as application
import trees.application.ports as ports
import trees.client as client


@ts.fake
class FakeGenerationReader(ports.GenerationReader):

    def __init__(self, read_generation_response: ports.ReadGenerationResponse) -> None:
        self._read_generation_response = read_generation_response
        self.asked: list[ports.ReadGenerationRequest] = []

    def read_generation(self, read_generation_request: ports.ReadGenerationRequest) -> ports.ReadGenerationResponse:
        self.asked.append(read_generation_request)
        return self._read_generation_response


@ts.fake
class FakeTreeWriter(ports.TreeWriter):

    def __init__(self) -> None:
        self.written: list[ports.WriteTreeRequest] = []

    def write_tree(self, write_tree_request: ports.WriteTreeRequest) -> ports.WriteTreeResponse:
        self.written.append(write_tree_request)
        return ports.WriteTreeResponse(paths=tuple(file_record.path for file_record in write_tree_request.files))


@ts.helper
def read_generation_response(
    state: str = "read", target: str = "absent", durable_execution_engine: str = "restate"
) -> ports.ReadGenerationResponse:
    return ports.ReadGenerationResponse(
        spec=ports.SpecRecord(
            state=ports.SpecState(state),
            note="spec.toml",
            unknown_keys=(),
            app_name="voice",
            bounded_context_name="calls",
            aggregate_root_class_name="Call",
            durable_execution_engine=durable_execution_engine,
            database="postgres",
            identity_field_name="call_id",
            identity_port_operation_name="issue_call_id",
            aggregate_fields=(ports.FieldRecord(name="person_name", kind="str"),),
            sample_values=(
                ports.SampleRecord(
                    name="call_id",
                    values=(ports.ValueRecord(kind="str", text="call-1"), ports.ValueRecord(kind="str", text="call-2")),
                ),
                ports.SampleRecord(
                    name="person_name",
                    values=(ports.ValueRecord(kind="str", text="Ada"), ports.ValueRecord(kind="str", text="Grace")),
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
            random_values=(ports.ValueRecord(kind="str", text="Ada"),),
            storage_url_variable="CALLS_STORAGE",
            restate_ingress_url_variable="RESTATE_INGRESS",
        ),
        target=ports.TargetRecord(state=ports.TargetState(target)),
        templates=(ports.TemplateRecord(path="{{context}}/domain/{{aggregate}}.py.tmpl", text="class {{Aggregate}}:\n"),),
    )


class TestTreeService:

    def test_a_clean_spec_is_written_as_the_files_it_renders(self) -> None:
        fake_tree_writer = FakeTreeWriter()
        tree_service = application.TreeService(FakeGenerationReader(read_generation_response()), fake_tree_writer)

        generate_tree_response = tree_service.generate_tree(
            client.GenerateTreeRequest(spec_path="spec.toml", out_dir="out")
        )

        assert [
            (
                write_tree_request.out_dir,
                [(file_record.path, file_record.text) for file_record in write_tree_request.files],
            )
            for write_tree_request in fake_tree_writer.written
        ] == [("out", [("calls/domain/call.py", "class Call:\n")])]
        assert generate_tree_response.problems == ()
        assert generate_tree_response.paths == ("calls/domain/call.py",)

    def test_the_reader_is_asked_for_the_spec_and_the_output_directory_it_was_given(self) -> None:
        fake_generation_reader = FakeGenerationReader(read_generation_response())
        tree_service = application.TreeService(fake_generation_reader, FakeTreeWriter())

        tree_service.generate_tree(client.GenerateTreeRequest(spec_path="specs/voice.toml", out_dir="/tmp/voice"))

        assert [
            (read_generation_request.spec_path, read_generation_request.out_dir)
            for read_generation_request in fake_generation_reader.asked
        ] == [("specs/voice.toml", "/tmp/voice")]

    def test_a_spec_with_problems_writes_nothing_and_answers_the_problems(self) -> None:
        fake_tree_writer = FakeTreeWriter()
        tree_service = application.TreeService(
            FakeGenerationReader(read_generation_response(durable_execution_engine="temporal")), fake_tree_writer
        )

        generate_tree_response = tree_service.generate_tree(
            client.GenerateTreeRequest(spec_path="spec.toml", out_dir="out")
        )

        assert fake_tree_writer.written == []
        assert generate_tree_response.problems == (
            "durable_execution_engine 'temporal' has no templates; the one engine is 'restate'",
        )
        assert generate_tree_response.paths == ()

    def test_an_occupied_output_directory_writes_nothing(self) -> None:
        fake_tree_writer = FakeTreeWriter()
        tree_service = application.TreeService(
            FakeGenerationReader(read_generation_response(target="occupied")), fake_tree_writer
        )

        generate_tree_response = tree_service.generate_tree(
            client.GenerateTreeRequest(spec_path="spec.toml", out_dir="out")
        )

        assert fake_tree_writer.written == []
        assert generate_tree_response.problems == ("the output directory is not empty",)

    def test_a_missing_spec_file_is_answered_as_a_problem(self) -> None:
        tree_service = application.TreeService(
            FakeGenerationReader(read_generation_response(state="missing")), FakeTreeWriter()
        )

        generate_tree_response = tree_service.generate_tree(
            client.GenerateTreeRequest(spec_path="spec.toml", out_dir="out")
        )

        assert generate_tree_response.problems == ("there is no spec file at spec.toml",)
