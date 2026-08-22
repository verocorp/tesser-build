from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import tesser.adapters as ts

import repo.application.ports.repo_reader as repo_reader

SKIP_DIRS: Final[frozenset[str]] = frozenset(
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

HIDDEN_TRACKED: Final[frozenset[str]] = frozenset({".github"})

DECLARATION: Final[str] = ".tesser-root"

REQUIREMENTS: Final[str] = "requirements-dev.txt"


class FilesystemRepoReader(ts.Repository):

    def read(self, request: repo_reader.ReadRepoRequest) -> repo_reader.ReadRepoResponse:
        base = Path(request.repo_root)
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
        declarations, requirements = self._walk(base)
        return repo_reader.ReadRepoResponse(
            manifest=self._manifest(base / "manifest.json"),
            verify=self._file(base / "scripts" / "verify"),
            workflow=self._file(base / ".github" / "workflows" / "test.yml"),
            top=self._entries(base),
            examples=self._entries(base / "examples"),
            declarations=declarations,
            requirements=requirements,
        )

    def _manifest(self, path: Path) -> repo_reader.ManifestRecord:  # tesser:debt TB051
        record = self._file(path)
        match record.state:
            case repo_reader.FileState.MISSING:
                return repo_reader.ManifestRecord(
                    state=repo_reader.ManifestState.MISSING, rows=(), note=""
                )
            case repo_reader.FileState.UNREADABLE:
                return repo_reader.ManifestRecord(
                    state=repo_reader.ManifestState.UNREADABLE, rows=(), note=""
                )
            case repo_reader.FileState.READ:
                return self._rows(record.text)
            case _ as unreachable:
                raise AssertionError(unreachable)

    def _rows(self, text: str) -> repo_reader.ManifestRecord:  # tesser:debt TB051
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            return repo_reader.ManifestRecord(
                state=repo_reader.ManifestState.MALFORMED, rows=(), note=str(error)
            )
        if not isinstance(parsed, dict) or not all(
            isinstance(key, str) and isinstance(kind, str)
            for key, kind in parsed.items()
        ):
            return repo_reader.ManifestRecord(
                state=repo_reader.ManifestState.MISSHAPEN, rows=(), note=""
            )
        return repo_reader.ManifestRecord(
            state=repo_reader.ManifestState.READ,
            rows=tuple(
                repo_reader.RowRecord(key=key, kind=kind)
                for key, kind in parsed.items()
            ),
            note="",
        )

    def _file(self, path: Path) -> repo_reader.FileRecord:  # tesser:debt TB051
        try:
            text = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return repo_reader.FileRecord(state=repo_reader.FileState.MISSING, text="")
        except (UnicodeDecodeError, OSError):
            return repo_reader.FileRecord(state=repo_reader.FileState.UNREADABLE, text="")
        return repo_reader.FileRecord(state=repo_reader.FileState.READ, text=text)

    def _entries(self, base: Path) -> tuple[repo_reader.EntryRecord, ...]:  # tesser:debt TB051
        if not base.is_dir():
            return ()
        found: list[repo_reader.EntryRecord] = []
        for entry in self._listing(base):
            if entry.name in SKIP_DIRS:
                continue
            if entry.name.startswith(".") and entry.name not in HIDDEN_TRACKED:
                continue
            if entry.is_symlink():
                if entry.is_dir() or not entry.exists():
                    found.append(
                        repo_reader.EntryRecord(
                            name=entry.name, form=repo_reader.EntryForm.SYMLINK
                        )
                    )
            elif entry.is_dir():
                found.append(
                    repo_reader.EntryRecord(
                        name=entry.name, form=repo_reader.EntryForm.DIRECTORY
                    )
                )
        return tuple(found)

    def _walk(  # tesser:debt TB051
        self, root: Path
    ) -> tuple[tuple[repo_reader.DeclarationRecord, ...], tuple[str, ...]]:
        declarations: list[repo_reader.DeclarationRecord] = []
        requirements: list[str] = []
        pending = [root]
        while pending:
            base = pending.pop()
            for entry in self._listing(base):
                if entry.name in SKIP_DIRS:
                    continue
                if entry.is_dir() and not entry.is_symlink():
                    pending.append(entry)
                elif entry.name == DECLARATION and not entry.is_dir():
                    record = self._file(entry)
                    declarations.append(
                        repo_reader.DeclarationRecord(
                            path=str(entry.relative_to(root)),
                            state=record.state,
                            text=record.text,
                        )
                    )
                elif entry.name == REQUIREMENTS and not entry.is_dir():
                    requirements.append(str(entry.parent.relative_to(root)))
        return tuple(declarations), tuple(requirements)

    def _listing(self, base: Path) -> tuple[Path, ...]:  # tesser:debt TB051
        try:
            return tuple(sorted(base.iterdir()))
        except OSError:
            return ()
