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
def field_record(name: str = "person_name", kind: str = "str") -> ports.FieldRecord:
    return ports.FieldRecord(name=name, kind=kind)


@ts.helper
def value_record(kind: str = "str", text: str = "call-1") -> ports.ValueRecord:
    return ports.ValueRecord(kind=kind, text=text)


@ts.helper
def sample_record(
    name: str = "call_id",
    values: tuple[ports.ValueRecord, ...] = (value_record(), value_record(text="call-2")),
) -> ports.SampleRecord:
    return ports.SampleRecord(name=name, values=values)


@ts.helper
def spec_record(
    state: ports.SpecState = ports.SpecState.READ,
    note: str = "spec.toml",
    unknown_keys: tuple[str, ...] = (),
    app_name: str = "voice",
    bounded_context_name: str = "calls",
    aggregate_root_class_name: str = "Call",
    durable_execution_engine: str = "restate",
    database: str = "postgres",
    identity_field_name: str = "call_id",
    identity_port_operation_name: str = "issue_call_id",
    aggregate_fields: tuple[ports.FieldRecord, ...] = (field_record(),),
    sample_values: tuple[ports.SampleRecord, ...] = (
        sample_record(),
        sample_record(name="person_name", values=(value_record(text="Ada"), value_record(text="Grace"))),
    ),
    write_operation_name: str = "place_call",
    read_operation_name: str = "get_call",
    read_response_fields: tuple[str, ...] = ("call_id", "person_name"),
    orchestrator_operation_name: str = "conduct_call",
    action_operation_name: str = "record_call",
    save_operation_name: str = "save_call",
    load_operation_name: str = "load_call",
    load_response_collection_name: str = "calls",
    test_class_name: str = "TestPlacingCalls",
    test_method_name: str = "test_a_call_is_successfully_made",
    asserted_field: str = "person_name",
    random_values: tuple[ports.ValueRecord, ...] = (value_record(text="Ada"),),
    storage_url_variable: str = "CALLS_STORAGE",
    restate_ingress_url_variable: str = "RESTATE_INGRESS",
) -> ports.SpecRecord:
    return ports.SpecRecord(
        state=state,
        note=note,
        unknown_keys=unknown_keys,
        app_name=app_name,
        bounded_context_name=bounded_context_name,
        aggregate_root_class_name=aggregate_root_class_name,
        durable_execution_engine=durable_execution_engine,
        database=database,
        identity_field_name=identity_field_name,
        identity_port_operation_name=identity_port_operation_name,
        aggregate_fields=aggregate_fields,
        sample_values=sample_values,
        write_operation_name=write_operation_name,
        read_operation_name=read_operation_name,
        read_response_fields=read_response_fields,
        orchestrator_operation_name=orchestrator_operation_name,
        action_operation_name=action_operation_name,
        save_operation_name=save_operation_name,
        load_operation_name=load_operation_name,
        load_response_collection_name=load_response_collection_name,
        test_class_name=test_class_name,
        test_method_name=test_method_name,
        asserted_field=asserted_field,
        random_values=random_values,
        storage_url_variable=storage_url_variable,
        restate_ingress_url_variable=restate_ingress_url_variable,
    )


@ts.helper
def target_record(state: ports.TargetState = ports.TargetState.ABSENT) -> ports.TargetRecord:
    return ports.TargetRecord(state=state)


@ts.helper
def template_record(
    path: str = "{{context}}/domain/{{aggregate}}.py.tmpl", text: str = "class {{Aggregate}}:\n"
) -> ports.TemplateRecord:
    return ports.TemplateRecord(path=path, text=text)


@ts.helper
def read_generation_response(
    spec: ports.SpecRecord = spec_record(),
    target: ports.TargetRecord = target_record(),
    templates: tuple[ports.TemplateRecord, ...] = (template_record(),),
) -> ports.ReadGenerationResponse:
    return ports.ReadGenerationResponse(spec=spec, target=target, templates=templates)


class TestTreeService:

    def test_a_clean_spec_is_written_as_the_files_it_renders(self) -> None:
        fake_tree_writer = FakeTreeWriter()
        tree_service = application.TreeService(
            FakeGenerationReader(
                read_generation_response(
                    spec=spec_record(bounded_context_name="calls", aggregate_root_class_name="Call"),
                    templates=(
                        template_record(path="{{context}}/domain/{{aggregate}}.py.tmpl", text="class {{Aggregate}}:\n"),
                    ),
                )
            ),
            fake_tree_writer,
        )

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
            FakeGenerationReader(read_generation_response(spec=spec_record(durable_execution_engine="temporal"))), fake_tree_writer
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
            FakeGenerationReader(read_generation_response(target=target_record(state=ports.TargetState.OCCUPIED))), fake_tree_writer
        )

        generate_tree_response = tree_service.generate_tree(
            client.GenerateTreeRequest(spec_path="spec.toml", out_dir="out")
        )

        assert fake_tree_writer.written == []
        assert generate_tree_response.problems == ("the output directory is not empty",)

    def test_a_missing_spec_file_is_answered_as_a_problem(self) -> None:
        tree_service = application.TreeService(
            FakeGenerationReader(read_generation_response(spec=spec_record(state=ports.SpecState.MISSING, note="spec.toml"))), FakeTreeWriter()
        )

        generate_tree_response = tree_service.generate_tree(
            client.GenerateTreeRequest(spec_path="spec.toml", out_dir="out")
        )

        assert generate_tree_response.problems == ("there is no spec file at spec.toml",)
