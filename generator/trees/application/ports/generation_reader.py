from __future__ import annotations

import enum
import typing

import tesser.application as ts


class SpecState(enum.Enum):
    READ = "read"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    MALFORMED = "malformed"


class TargetState(enum.Enum):
    ABSENT = "absent"
    EMPTY = "empty"
    OCCUPIED = "occupied"


class FieldRecord(ts.Response):

    def __init__(self, name: str, kind: str) -> None:
        self.name = name
        self.kind = kind


class ValueRecord(ts.Response):

    def __init__(self, kind: str, text: str) -> None:
        self.kind = kind
        self.text = text


class SampleRecord(ts.Response):

    def __init__(self, name: str, values: tuple[ValueRecord, ...]) -> None:
        self.name = name
        self.values = values


class SpecRecord(ts.Response):

    def __init__(
        self,
        state: SpecState,
        note: str,
        unknown_keys: tuple[str, ...],
        app_name: str,
        bounded_context_name: str,
        aggregate_root_class_name: str,
        durable_execution_engine: str,
        database: str,
        identity_field_name: str,
        identity_port_operation_name: str,
        aggregate_fields: tuple[FieldRecord, ...],
        sample_values: tuple[SampleRecord, ...],
        write_operation_name: str,
        read_operation_name: str,
        read_response_fields: tuple[str, ...],
        orchestrator_operation_name: str,
        action_operation_name: str,
        save_operation_name: str,
        load_operation_name: str,
        load_response_collection_name: str,
        test_class_name: str,
        test_method_name: str,
        asserted_field: str,
        random_values: tuple[ValueRecord, ...],
        storage_url_variable: str,
        restate_ingress_url_variable: str,
    ) -> None:
        self.state = state
        self.note = note
        self.unknown_keys = unknown_keys
        self.app_name = app_name
        self.bounded_context_name = bounded_context_name
        self.aggregate_root_class_name = aggregate_root_class_name
        self.durable_execution_engine = durable_execution_engine
        self.database = database
        self.identity_field_name = identity_field_name
        self.identity_port_operation_name = identity_port_operation_name
        self.aggregate_fields = aggregate_fields
        self.sample_values = sample_values
        self.write_operation_name = write_operation_name
        self.read_operation_name = read_operation_name
        self.read_response_fields = read_response_fields
        self.orchestrator_operation_name = orchestrator_operation_name
        self.action_operation_name = action_operation_name
        self.save_operation_name = save_operation_name
        self.load_operation_name = load_operation_name
        self.load_response_collection_name = load_response_collection_name
        self.test_class_name = test_class_name
        self.test_method_name = test_method_name
        self.asserted_field = asserted_field
        self.random_values = random_values
        self.storage_url_variable = storage_url_variable
        self.restate_ingress_url_variable = restate_ingress_url_variable


class TargetRecord(ts.Response):

    def __init__(self, state: TargetState) -> None:
        self.state = state


class TemplateRecord(ts.Response):

    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.text = text


class ReadGenerationRequest(ts.Request):

    def __init__(self, spec_path: str, out_dir: str) -> None:
        self.spec_path = spec_path
        self.out_dir = out_dir


class ReadGenerationResponse(ts.Response):

    def __init__(self, spec: SpecRecord, target: TargetRecord, templates: tuple[TemplateRecord, ...]) -> None:
        self.spec = spec
        self.target = target
        self.templates = templates


class GenerationReader(ts.Port, typing.Protocol):

    def read_generation(self, read_generation_request: ReadGenerationRequest) -> ReadGenerationResponse: ...
