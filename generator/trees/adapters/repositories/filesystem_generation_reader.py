from __future__ import annotations

import pathlib
import tomllib
import typing

import tesser.adapters as ts

import trees.application.ports as ports

TEMPLATE_SUFFIX: typing.Final[str] = ".tmpl"

SCALARS: typing.Final[tuple[tuple[str, str, str], ...]] = (
    ("app_name", "", "app_name"),
    ("bounded_context_name", "", "bounded_context_name"),
    ("aggregate_root_class_name", "", "aggregate_root_class_name"),
    ("durable_execution_engine", "", "durable_execution_engine"),
    ("database", "", "database"),
    ("identity_field_name", "", "identity_field_name"),
    ("identity_port_operation_name", "", "identity_port_operation_name"),
    ("write_operation_name", "client", "write_operation_name"),
    ("read_operation_name", "client", "read_operation_name"),
    ("orchestrator_operation_name", "orchestrator", "operation_name"),
    ("action_operation_name", "action", "operation_name"),
    ("save_operation_name", "repository", "save_operation_name"),
    ("load_operation_name", "repository", "load_operation_name"),
    ("load_response_collection_name", "repository", "load_response_collection_name"),
    ("test_class_name", "acceptance_test", "test_class_name"),
    ("test_method_name", "acceptance_test", "test_method_name"),
    ("asserted_field", "acceptance_test", "asserted_field"),
    ("storage_url_variable", "environment_variables", "storage_url"),
    ("restate_ingress_url_variable", "environment_variables", "restate_ingress_url"),
)

LISTS: typing.Final[tuple[tuple[str, str], ...]] = (
    ("client", "read_response_fields"),
    ("acceptance_test", "random_values"),
)

FIELD_TABLES: typing.Final[tuple[str, ...]] = ("aggregate_fields", "sample_values")


class FilesystemGenerationReader(ts.Repository):

    def __init__(self, templates_root: str) -> None:
        self._templates_root = templates_root

    def read_generation(self, read_generation_request: ports.ReadGenerationRequest) -> ports.ReadGenerationResponse:
        spec_path = pathlib.Path(read_generation_request.spec_path)
        stated: dict[str, object] = {}
        note = ""
        try:
            stated = tomllib.loads(spec_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            state = ports.SpecState.MISSING
            note = str(spec_path)
        except UnicodeDecodeError:
            state = ports.SpecState.UNREADABLE
            note = str(spec_path)
        except tomllib.TOMLDecodeError as error:
            state = ports.SpecState.MALFORMED
            note = str(error)
        except OSError:
            state = ports.SpecState.UNREADABLE
            note = str(spec_path)
        else:
            state = ports.SpecState.READ
        allowed = {(table, key) for _, table, key in SCALARS} | set(LISTS)
        known_tables = {table for table, _ in allowed if table} | set(FIELD_TABLES)
        unknown_keys: list[str] = []
        for key, value in stated.items():
            if isinstance(value, dict) and key in FIELD_TABLES:
                continue
            if isinstance(value, dict) and key in known_tables:
                unknown_keys.extend(f"{key}.{inner}" for inner in value if (key, inner) not in allowed)
            elif ("", key) not in allowed:
                unknown_keys.append(key)
        tables: dict[str, dict[str, object]] = {"": stated}
        tables.update({key: value for key, value in stated.items() if isinstance(value, dict)})
        texts = {name: tables.get(table, {}).get(key) for name, table, key in SCALARS}
        answers = tables.get("client", {}).get("read_response_fields")
        randoms = tables.get("acceptance_test", {}).get("random_values")
        out_dir = pathlib.Path(read_generation_request.out_dir)
        if not out_dir.exists():
            target = ports.TargetState.ABSENT
        elif out_dir.is_dir() and not any(out_dir.iterdir()):
            target = ports.TargetState.EMPTY
        else:
            target = ports.TargetState.OCCUPIED
        templates_root = pathlib.Path(self._templates_root)
        found = sorted(templates_root.rglob(f"*{TEMPLATE_SUFFIX}")) if templates_root.is_dir() else []
        return ports.ReadGenerationResponse(
            spec=ports.SpecRecord(
                state=state,
                note=note,
                unknown_keys=tuple(unknown_keys),
                aggregate_fields=tuple(
                    ports.FieldRecord(name=name, kind=kind if isinstance(kind, str) else "")
                    for name, kind in tables.get("aggregate_fields", {}).items()
                ),
                sample_values=tuple(
                    ports.SampleRecord(
                        name=name,
                        values=(
                            tuple(
                                ports.ValueRecord(
                                    kind=(
                                        "str"
                                        if isinstance(sample, str)
                                        else ("int" if isinstance(sample, int) and not isinstance(sample, bool) else "other")
                                    ),
                                    text=str(sample) if isinstance(sample, (str, int)) and not isinstance(sample, bool) else "",
                                )
                                for sample in samples
                            )
                            if isinstance(samples, list)
                            else ()
                        ),
                    )
                    for name, samples in tables.get("sample_values", {}).items()
                ),
                read_response_fields=(
                    tuple(answer for answer in answers if isinstance(answer, str)) if isinstance(answers, list) else ()
                ),
                random_values=(
                    tuple(
                        ports.ValueRecord(
                            kind=(
                                "str"
                                if isinstance(random, str)
                                else ("int" if isinstance(random, int) and not isinstance(random, bool) else "other")
                            ),
                            text=str(random) if isinstance(random, (str, int)) and not isinstance(random, bool) else "",
                        )
                        for random in randoms
                    )
                    if isinstance(randoms, list)
                    else ()
                ),
                **{name: value if isinstance(value, str) else "" for name, value in texts.items()},
            ),
            target=ports.TargetRecord(state=target),
            templates=tuple(
                ports.TemplateRecord(path=str(path.relative_to(templates_root)), text=path.read_text(encoding="utf-8"))
                for path in found
                if path.is_file()
            ),
        )
