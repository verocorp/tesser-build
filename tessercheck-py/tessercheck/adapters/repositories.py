import os
import sys
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
    }
)

DECLARATION: Final[str] = ".tesser-root"

SKIP_DIRECTIVE: Final[str] = "skip"

EXPORT_DIRECTIVE: Final[str] = "export"

IMPORT_DIRECTIVE: Final[str] = "import"


class FilesystemSourceReader(ts.Repository):

    def sources(
        self, request: source_reader.ReadSourcesRequest
    ) -> source_reader.ReadSourcesResponse:
        base = Path(request.root)
        form, skips, exports, imports = self._declaration(base)
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
            exports=exports,
            imports=imports,
            stdlib=tuple(sorted(sys.stdlib_module_names)),
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

    def _declaration(
        self, base: Path
    ) -> tuple[source_reader.RootForm, frozenset[str], tuple[str, ...], tuple[str, ...]]:
        try:
            text = (base / DECLARATION).read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return source_reader.RootForm.MISSING, frozenset(), (), ()
        except (UnicodeDecodeError, OSError):
            return source_reader.RootForm.UNREADABLE, frozenset(), (), ()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines or lines[0] != "app":
            return source_reader.RootForm.UNRECOGNIZED, frozenset(), (), ()
        skips: set[str] = set()
        exports: list[str] = []
        imports: list[str] = []
        for line in lines[1:]:
            directive, _, value = line.partition(" ")
            value = value.strip()
            if not value:
                return source_reader.RootForm.UNRECOGNIZED, frozenset(), (), ()
            if directive == SKIP_DIRECTIVE and "/" not in value:
                skips.add(value)
            elif directive == EXPORT_DIRECTIVE and value.isidentifier():
                exports.append(value)
            elif directive == IMPORT_DIRECTIVE and all(
                part.isidentifier() for part in value.split(".")
            ):
                imports.append(value)
            else:
                return source_reader.RootForm.UNRECOGNIZED, frozenset(), (), ()
        return source_reader.RootForm.APP, frozenset(skips), tuple(exports), tuple(imports)
