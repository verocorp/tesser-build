from pathlib import Path
from typing import Final

import tesser.adapters as ts

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

    def sources(self, root: str) -> tuple[tuple[str, str, str | None, bool], ...]:
        found: list[tuple[str, str, str | None, bool]] = []
        base = Path(root)
        for path in sorted(base.rglob("*.py")):
            relative = path.relative_to(base)
            if SKIP_DIRS & set(relative.parts[:-1]):
                continue
            parts = list(relative.with_suffix("").parts)
            is_package = bool(parts) and parts[-1] == "__init__"
            if is_package:
                parts = parts[:-1]
            if not parts:
                continue
            try:
                source: str | None = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                source = None
            found.append((str(relative), ".".join(parts), source, is_package))
        return tuple(found)
