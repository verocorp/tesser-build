from pathlib import Path
from typing import Final

import tesser.adapters as ts

import tessercheck.application.ports.source_reader as source_reader

SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
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
        "testdata",
    }
)


class FilesystemSourceReader(ts.Repository):

    def sources(
        self, request: source_reader.ReadSourcesRequest
    ) -> source_reader.ReadSourcesResponse:
        found: list[source_reader.SourceFile] = []
        base = Path(request.root)
        for path in sorted(base.rglob("*.py")):
            relative = path.relative_to(base)
            if SKIP_DIRS & set(relative.parts[:-1]):
                continue
            parts = list(relative.with_suffix("").parts)
            is_package = bool(parts) and parts[-1] == "__init__"
            form = (
                source_reader.ModuleForm.PACKAGE
                if is_package
                else source_reader.ModuleForm.MODULE
            )
            if is_package:
                parts = parts[:-1]
            if not parts:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
                state = source_reader.SourceState.READ
            except (UnicodeDecodeError, OSError):
                text = ""
                state = source_reader.SourceState.UNREADABLE
            found.append(
                source_reader.SourceFile(
                    path=str(relative),
                    name=".".join(parts),
                    text=text,
                    state=state,
                    form=form,
                )
            )
        return source_reader.ReadSourcesResponse(sources=tuple(found))
