from __future__ import annotations

import pathlib
import tomllib
import typing

import tesser.adapters as ts

import trees.application.ports as ports

TEMPLATE_SUFFIX: typing.Final[str] = ".tmpl"

KEYS: typing.Final[tuple[tuple[str, str, str], ...]] = (
    ("app", "", "app"),
    ("context", "", "context"),
    ("aggregate", "", "aggregate"),
    ("engine", "", "engine"),
    ("store", "", "store"),
    ("identity", "identity", "name"),
    ("minted_by", "identity", "minted_by"),
    ("write", "client", "write"),
    ("read", "client", "read"),
    ("orchestrator", "orchestrator", "operation"),
    ("action", "action", "operation"),
    ("save", "port", "save"),
    ("load", "port", "load"),
    ("asserts", "acceptance", "asserts"),
    ("storage_env", "env", "storage"),
    ("ingress_env", "env", "ingress"),
)


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
        tables: dict[str, dict[str, object]] = {"": stated}
        tables.update({key: value for key, value in stated.items() if isinstance(value, dict)})
        texts = {name: tables.get(table, {}).get(key) for name, table, key in KEYS}
        answers = tables.get("client", {}).get("read_answers")
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
                fields=tuple(
                    ports.FieldRecord(name=name, kind=kind if isinstance(kind, str) else "")
                    for name, kind in tables.get("fields", {}).items()
                ),
                read_answers=(
                    tuple(answer for answer in answers if isinstance(answer, str)) if isinstance(answers, list) else ()
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
