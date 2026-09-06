from __future__ import annotations

import json
import pathlib
import tomllib
import typing

import tesser.adapters as ts

import repo.application.ports as ports

SKIP_DIRS: typing.Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".claude",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".ruff_cache",
        "node_modules",
        "build",
        "dist",
        ".eggs",
    }
)

HIDDEN_TRACKED: typing.Final[frozenset[str]] = frozenset({".github"})

DECLARATION: typing.Final[str] = ".tesser-root"

REQUIREMENTS: typing.Final[str] = "requirements-dev.txt"

PYPROJECT: typing.Final[str] = "pyproject.toml"

RUFF: typing.Final[str] = "ruff.toml"


class FilesystemRepoReader(ts.Repository):

    def read(self, read_repo_request: ports.ReadRepoRequest) -> ports.ReadRepoResponse:
        base = pathlib.Path(read_repo_request.repo_root)
        if not base.is_dir():
            return ports.ReadRepoResponse(
                manifest=ports.ManifestRecord(
                    state=ports.ManifestState.MALFORMED,
                    rows=(),
                    note=f"{read_repo_request.repo_root} is not a directory",
                ),
                verify=ports.FileRecord(
                    state=ports.FileState.MISSING, text=""
                ),
                workflow=ports.FileRecord(
                    state=ports.FileState.MISSING, text=""
                ),
                top=(),
                examples=(),
                declarations=(),
                requirements=(),
                floors=(),
            )
        declarations: list[ports.DeclarationRecord] = []
        requirements: list[str] = []
        configs: list[pathlib.Path] = []
        pending = [base]
        while pending:
            walked = pending.pop()
            try:
                walked_listing = tuple(sorted(walked.iterdir()))
            except OSError:
                walked_listing = ()
            for entry in walked_listing:
                if entry.name in SKIP_DIRS:
                    continue
                if entry.is_dir() and not entry.is_symlink():
                    pending.append(entry)
                elif entry.name == DECLARATION and not entry.is_dir():
                    try:
                        declaration_text = entry.read_text(encoding="utf-8-sig")
                    except FileNotFoundError:
                        declaration_state = ports.FileState.MISSING
                        declaration_text = ""
                    except (UnicodeDecodeError, OSError):
                        declaration_state = ports.FileState.UNREADABLE
                        declaration_text = ""
                    else:
                        declaration_state = ports.FileState.READ
                    declarations.append(
                        ports.DeclarationRecord(
                            path=str(entry.relative_to(base)),
                            state=declaration_state,
                            text=declaration_text,
                        )
                    )
                elif entry.name == REQUIREMENTS and not entry.is_dir():
                    requirements.append(str(entry.parent.relative_to(base)))
                elif entry.name in (PYPROJECT, RUFF) and not entry.is_dir():
                    configs.append(entry)
        floors: list[ports.FloorRecord] = []
        for config in configs:
            config_path = str(config.relative_to(base))
            try:
                stated = tomllib.loads(config.read_text(encoding="utf-8-sig"))
            except (UnicodeDecodeError, OSError):
                floors.append(
                    ports.FloorRecord(
                        path=config_path,
                        key=ports.FloorKey.REQUIRES_PYTHON,
                        state=ports.FloorState.UNREADABLE,
                        value="",
                    )
                )
                continue
            except tomllib.TOMLDecodeError:
                floors.append(
                    ports.FloorRecord(
                        path=config_path,
                        key=ports.FloorKey.REQUIRES_PYTHON,
                        state=ports.FloorState.MALFORMED,
                        value="",
                    )
                )
                continue
            project = stated.get("project")
            if isinstance(project, dict):
                declared = project.get("requires-python")
                floors.append(
                    ports.FloorRecord(
                        path=config_path,
                        key=ports.FloorKey.REQUIRES_PYTHON,
                        state=(
                            ports.FloorState.READ
                            if isinstance(declared, str)
                            else ports.FloorState.UNDECLARED
                        ),
                        value=declared if isinstance(declared, str) else "",
                    )
                )
            if config.name == PYPROJECT:
                tool = stated.get("tool")
                ruff = tool.get("ruff") if isinstance(tool, dict) else None
            else:
                ruff = stated
            if isinstance(ruff, dict):
                target = ruff.get("target-version")
                if isinstance(target, str):
                    floors.append(
                        ports.FloorRecord(
                            path=config_path,
                            key=ports.FloorKey.TARGET_VERSION,
                            state=ports.FloorState.READ,
                            value=target,
                        )
                    )
        try:
            manifest_text = (base / "manifest.json").read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            manifest_state = ports.FileState.MISSING
            manifest_text = ""
        except (UnicodeDecodeError, OSError):
            manifest_state = ports.FileState.UNREADABLE
            manifest_text = ""
        else:
            manifest_state = ports.FileState.READ
        match manifest_state:
            case ports.FileState.MISSING:
                manifest = ports.ManifestRecord(
                    state=ports.ManifestState.MISSING, rows=(), note=""
                )
            case ports.FileState.UNREADABLE:
                manifest = ports.ManifestRecord(
                    state=ports.ManifestState.UNREADABLE, rows=(), note=""
                )
            case ports.FileState.READ:
                try:
                    parsed = json.loads(manifest_text)
                except json.JSONDecodeError as error:
                    manifest = ports.ManifestRecord(
                        state=ports.ManifestState.MALFORMED,
                        rows=(),
                        note=str(error),
                    )
                else:
                    if not isinstance(parsed, dict) or not all(
                        isinstance(key, str) and isinstance(kind, str)
                        for key, kind in parsed.items()
                    ):
                        manifest = ports.ManifestRecord(
                            state=ports.ManifestState.MISSHAPEN, rows=(), note=""
                        )
                    else:
                        manifest = ports.ManifestRecord(
                            state=ports.ManifestState.READ,
                            rows=tuple(
                                ports.RowRecord(key=key, kind=kind)
                                for key, kind in parsed.items()
                            ),
                            note="",
                        )
            case _ as unreachable:
                raise AssertionError(unreachable)
        try:
            verify_text = (base / "scripts" / "verify").read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            verify = ports.FileRecord(state=ports.FileState.MISSING, text="")
        except (UnicodeDecodeError, OSError):
            verify = ports.FileRecord(
                state=ports.FileState.UNREADABLE, text=""
            )
        else:
            verify = ports.FileRecord(
                state=ports.FileState.READ, text=verify_text
            )
        try:
            workflow_text = (base / ".github" / "workflows" / "test.yml").read_text(
                encoding="utf-8-sig"
            )
        except FileNotFoundError:
            workflow = ports.FileRecord(
                state=ports.FileState.MISSING, text=""
            )
        except (UnicodeDecodeError, OSError):
            workflow = ports.FileRecord(
                state=ports.FileState.UNREADABLE, text=""
            )
        else:
            workflow = ports.FileRecord(
                state=ports.FileState.READ, text=workflow_text
            )
        top: list[ports.EntryRecord] = []
        try:
            top_listing = tuple(sorted(base.iterdir()))
        except OSError:
            top_listing = ()
        for entry in top_listing:
            if entry.name in SKIP_DIRS:
                continue
            if entry.name.startswith(".") and entry.name not in HIDDEN_TRACKED:
                continue
            if entry.is_symlink():
                if entry.is_dir() or not entry.exists():
                    top.append(
                        ports.EntryRecord(
                            name=entry.name, form=ports.EntryForm.SYMLINK
                        )
                    )
            elif entry.is_dir():
                top.append(
                    ports.EntryRecord(
                        name=entry.name, form=ports.EntryForm.DIRECTORY
                    )
                )
        examples_base = base / "examples"
        examples: list[ports.EntryRecord] = []
        if examples_base.is_dir():
            try:
                examples_listing = tuple(sorted(examples_base.iterdir()))
            except OSError:
                examples_listing = ()
            for entry in examples_listing:
                if entry.name in SKIP_DIRS:
                    continue
                if entry.name.startswith(".") and entry.name not in HIDDEN_TRACKED:
                    continue
                if entry.is_symlink():
                    if entry.is_dir() or not entry.exists():
                        examples.append(
                            ports.EntryRecord(
                                name=entry.name, form=ports.EntryForm.SYMLINK
                            )
                        )
                elif entry.is_dir():
                    examples.append(
                        ports.EntryRecord(
                            name=entry.name, form=ports.EntryForm.DIRECTORY
                        )
                    )
        return ports.ReadRepoResponse(
            manifest=manifest,
            verify=verify,
            workflow=workflow,
            top=tuple(top),
            examples=tuple(examples),
            declarations=tuple(declarations),
            requirements=tuple(requirements),
            floors=tuple(floors),
        )
