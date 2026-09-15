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


class SpecRecord(ts.Response):

    def __init__(
        self,
        state: SpecState,
        note: str,
        app: str,
        context: str,
        aggregate: str,
        engine: str,
        store: str,
        identity: str,
        minted_by: str,
        fields: tuple[FieldRecord, ...],
        write: str,
        read: str,
        read_answers: tuple[str, ...],
        orchestrator: str,
        action: str,
        save: str,
        load: str,
        asserts: str,
        storage_env: str,
        ingress_env: str,
    ) -> None:
        self.state = state
        self.note = note
        self.app = app
        self.context = context
        self.aggregate = aggregate
        self.engine = engine
        self.store = store
        self.identity = identity
        self.minted_by = minted_by
        self.fields = fields
        self.write = write
        self.read = read
        self.read_answers = read_answers
        self.orchestrator = orchestrator
        self.action = action
        self.save = save
        self.load = load
        self.asserts = asserts
        self.storage_env = storage_env
        self.ingress_env = ingress_env


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
