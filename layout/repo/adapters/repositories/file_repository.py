from __future__ import annotations

import json
import pathlib
import typing

import tesser.adapters as ts

import repo.application.ports.repo_reader as repo_reader

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


class FilesystemRepoReader(ts.Repository):

    def read(self, request: repo_reader.ReadRepoRequest) -> repo_reader.ReadRepoResponse:
        base = pathlib.Path(request.repo_root)
        if not base.is_dir():
            return repo_reader.ReadRepoResponse(
                manifest=repo_reader.ManifestRecord(
                    state=repo_reader.ManifestState.MALFORMED,
                    rows=(),
                    note=f"{request.repo_root} is not a directory",
                ),
                verify=repo_reader.FileRecord(
                    state=repo_reader.FileState.MISSING, text=""
                ),
                workflow=repo_reader.FileRecord(
                    state=repo_reader.FileState.MISSING, text=""
                ),
                top=(),
                examples=(),
                declarations=(),
                requirements=(),
            )
        declarations: list[repo_reader.DeclarationRecord] = []
        requirements: list[str] = []
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
                        declaration_state = repo_reader.FileState.MISSING
                        declaration_text = ""
                    except (UnicodeDecodeError, OSError):
                        declaration_state = repo_reader.FileState.UNREADABLE
                        declaration_text = ""
                    else:
                        declaration_state = repo_reader.FileState.READ
                    declarations.append(
                        repo_reader.DeclarationRecord(
                            path=str(entry.relative_to(base)),
                            state=declaration_state,
                            text=declaration_text,
                        )
                    )
                elif entry.name == REQUIREMENTS and not entry.is_dir():
                    requirements.append(str(entry.parent.relative_to(base)))
        try:
            manifest_text = (base / "manifest.json").read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            manifest_state = repo_reader.FileState.MISSING
            manifest_text = ""
        except (UnicodeDecodeError, OSError):
            manifest_state = repo_reader.FileState.UNREADABLE
            manifest_text = ""
        else:
            manifest_state = repo_reader.FileState.READ
        match manifest_state:
            case repo_reader.FileState.MISSING:
                manifest = repo_reader.ManifestRecord(
                    state=repo_reader.ManifestState.MISSING, rows=(), note=""
                )
            case repo_reader.FileState.UNREADABLE:
                manifest = repo_reader.ManifestRecord(
                    state=repo_reader.ManifestState.UNREADABLE, rows=(), note=""
                )
            case repo_reader.FileState.READ:
                try:
                    parsed = json.loads(manifest_text)
                except json.JSONDecodeError as error:
                    manifest = repo_reader.ManifestRecord(
                        state=repo_reader.ManifestState.MALFORMED,
                        rows=(),
                        note=str(error),
                    )
                else:
                    if not isinstance(parsed, dict) or not all(
                        isinstance(key, str) and isinstance(kind, str)
                        for key, kind in parsed.items()
                    ):
                        manifest = repo_reader.ManifestRecord(
                            state=repo_reader.ManifestState.MISSHAPEN, rows=(), note=""
                        )
                    else:
                        manifest = repo_reader.ManifestRecord(
                            state=repo_reader.ManifestState.READ,
                            rows=tuple(
                                repo_reader.RowRecord(key=key, kind=kind)
                                for key, kind in parsed.items()
                            ),
                            note="",
                        )
            case _ as unreachable:
                raise AssertionError(unreachable)
        try:
            verify_text = (base / "scripts" / "verify").read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            verify = repo_reader.FileRecord(state=repo_reader.FileState.MISSING, text="")
        except (UnicodeDecodeError, OSError):
            verify = repo_reader.FileRecord(
                state=repo_reader.FileState.UNREADABLE, text=""
            )
        else:
            verify = repo_reader.FileRecord(
                state=repo_reader.FileState.READ, text=verify_text
            )
        try:
            workflow_text = (base / ".github" / "workflows" / "test.yml").read_text(
                encoding="utf-8-sig"
            )
        except FileNotFoundError:
            workflow = repo_reader.FileRecord(
                state=repo_reader.FileState.MISSING, text=""
            )
        except (UnicodeDecodeError, OSError):
            workflow = repo_reader.FileRecord(
                state=repo_reader.FileState.UNREADABLE, text=""
            )
        else:
            workflow = repo_reader.FileRecord(
                state=repo_reader.FileState.READ, text=workflow_text
            )
        top: list[repo_reader.EntryRecord] = []
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
                        repo_reader.EntryRecord(
                            name=entry.name, form=repo_reader.EntryForm.SYMLINK
                        )
                    )
            elif entry.is_dir():
                top.append(
                    repo_reader.EntryRecord(
                        name=entry.name, form=repo_reader.EntryForm.DIRECTORY
                    )
                )
        examples_base = base / "examples"
        examples: list[repo_reader.EntryRecord] = []
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
                            repo_reader.EntryRecord(
                                name=entry.name, form=repo_reader.EntryForm.SYMLINK
                            )
                        )
                elif entry.is_dir():
                    examples.append(
                        repo_reader.EntryRecord(
                            name=entry.name, form=repo_reader.EntryForm.DIRECTORY
                        )
                    )
        return repo_reader.ReadRepoResponse(
            manifest=manifest,
            verify=verify,
            workflow=workflow,
            top=tuple(top),
            examples=tuple(examples),
            declarations=tuple(declarations),
            requirements=tuple(requirements),
        )
