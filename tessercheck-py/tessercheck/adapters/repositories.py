import os
from pathlib import Path
from typing import Final

import tesser.adapters as ts

import tessercheck.application.ports.source_reader as source_reader
import tessercheck.application.ports.rulebook_sources as rulebook_sources

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
    }
)

DECLARATION: Final[str] = ".tesser-root"

SKIP_DIRECTIVE: Final[str] = "skip"


class FilesystemSourceReader(ts.Repository):

    def sources(
        self, request: source_reader.ReadSourcesRequest
    ) -> source_reader.ReadSourcesResponse:
        base = Path(request.root)
        form, skips = self._declaration(base)
        found: list[source_reader.SourceFile] = []
        nested: list[str] = []
        symlinked: list[str] = []
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            here = Path(dirpath)
            dirnames.sort()
            for name in list(dirnames):
                if name in SKIP_DIRS or name in skips:
                    dirnames.remove(name)
                elif (here / name).is_symlink():
                    dirnames.remove(name)
                    symlinked.append(str((here / name).relative_to(base)))
            for name in sorted(filenames):
                path = here / name
                relative = path.relative_to(base)
                if name == DECLARATION and here != base:
                    nested.append(str(relative))
                if name.endswith(".py") or name.endswith(".pyi"):
                    source = self._source(path, relative)
                    if source.name:
                        found.append(source)
        return source_reader.ReadSourcesResponse(
            root=form,
            nested=tuple(nested),
            symlinked=tuple(symlinked),
            sources=tuple(sorted(found, key=lambda source: source.path)),
        )

    def _source(self, path: Path, relative: Path) -> source_reader.SourceFile:
        parts = list(relative.with_suffix("").parts)
        is_package = bool(parts) and parts[-1] == "__init__"
        form = (
            source_reader.ModuleForm.PACKAGE
            if is_package
            else source_reader.ModuleForm.MODULE
        )
        if is_package:
            parts = parts[:-1]
        try:
            text = path.read_text(encoding="utf-8-sig")
            state = source_reader.SourceState.READ
        except (UnicodeDecodeError, OSError):
            text = ""
            state = source_reader.SourceState.UNREADABLE
        return source_reader.SourceFile(
            path=str(relative),
            name=".".join(parts),
            text=text,
            state=state,
            form=form,
        )

    def _declaration(self, base: Path) -> tuple[source_reader.RootForm, frozenset[str]]:
        try:
            text = (base / DECLARATION).read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return source_reader.RootForm.MISSING, frozenset()
        except (UnicodeDecodeError, OSError):
            return source_reader.RootForm.UNREADABLE, frozenset()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines or lines[0] != "app":
            return source_reader.RootForm.UNRECOGNIZED, frozenset()
        skips: set[str] = set()
        for line in lines[1:]:
            directive, _, value = line.partition(" ")
            value = value.strip()
            if directive != SKIP_DIRECTIVE or not value or "/" in value:
                return source_reader.RootForm.UNRECOGNIZED, frozenset()
            skips.add(value)
        return source_reader.RootForm.APP, frozenset(skips)


class FilesystemRulebookSources(ts.Repository):

    def read(
        self, request: rulebook_sources.ReadRulebookRequest
    ) -> rulebook_sources.ReadRulebookResponse:
        base = Path(request.root)
        modules = [
            base / "tessercheck" / "tests" / "test_checks.py",
            *sorted((base / "tessercheck" / "domain").glob("test_*.py")),
        ]
        return rulebook_sources.ReadRulebookResponse(
            checks_text=(base / "tessercheck" / "domain" / "checks.py").read_text(
                encoding="utf-8"
            ),
            test_modules=tuple(
                rulebook_sources.TestModuleText(
                    name=str(path.relative_to(base)),
                    text=path.read_text(encoding="utf-8"),
                )
                for path in modules
            ),
            contracts_text=(base / ".importlinter").read_text(encoding="utf-8"),
        )
