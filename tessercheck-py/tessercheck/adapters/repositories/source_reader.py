import os
import sys
import pathlib
import typing

import tesser.adapters as ts

import tessercheck.application.ports.source_reader as source_reader

SKIP_DIRS: typing.Final[frozenset[str]] = frozenset(
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

DECLARATION: typing.Final[str] = ".tesser-root"

SKIP_DIRECTIVE: typing.Final[str] = "skip"

EXPORT_DIRECTIVE: typing.Final[str] = "export"

IMPORT_DIRECTIVE: typing.Final[str] = "import"

STDLIB_DIRECTIVE: typing.Final[str] = "stdlib"


class FilesystemSourceReader(ts.Repository):

    def sources(
        self, request: source_reader.ReadSourcesRequest
    ) -> source_reader.ReadSourcesResponse:
        base = pathlib.Path(request.tree)
        root = source_reader.RootForm.APP
        skips: set[str] = set()
        exports: list[str] = []
        imports: list[str] = []
        pure_stdlib: list[str] = []
        try:
            declared = (base / DECLARATION).read_text(encoding="utf-8-sig")
            lines = [line.strip() for line in declared.splitlines() if line.strip()]
            if not lines or lines[0] != "app":
                root = source_reader.RootForm.UNRECOGNIZED
            else:
                for line in lines[1:]:
                    directive, _, value = line.partition(" ")
                    value = value.strip()
                    if not value:
                        root = source_reader.RootForm.UNRECOGNIZED
                        break
                    if directive == SKIP_DIRECTIVE and "/" not in value:
                        skips.add(value)
                    elif directive == EXPORT_DIRECTIVE and value.isidentifier():
                        exports.append(value)
                    elif directive == IMPORT_DIRECTIVE and all(
                        part.isidentifier() for part in value.split(".")
                    ):
                        imports.append(value)
                    elif directive == STDLIB_DIRECTIVE and all(
                        part.isidentifier() for part in value.split(".")
                    ):
                        pure_stdlib.append(value)
                    else:
                        root = source_reader.RootForm.UNRECOGNIZED
                        break
        except FileNotFoundError:
            root = source_reader.RootForm.MISSING
        except (UnicodeDecodeError, OSError):
            root = source_reader.RootForm.UNREADABLE
        if root is not source_reader.RootForm.APP:
            skips = set()
            exports = []
            imports = []
            pure_stdlib = []
        found: list[source_reader.SourceFile] = []
        nested: list[str] = []
        symlinked: list[str] = []
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            here = pathlib.Path(dirpath)
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
                    module = ".".join(parts)
                    if module:
                        found.append(
                            source_reader.SourceFile(
                                path=str(relative),
                                name=module,
                                text=text,
                                state=state,
                                form=form,
                            )
                        )
        return source_reader.ReadSourcesResponse(
            root=root,
            nested=tuple(nested),
            symlinked=tuple(symlinked),
            sources=tuple(sorted(found, key=lambda source: source.path)),
            exports=tuple(exports),
            imports=tuple(imports),
            stdlib=tuple(sorted(sys.stdlib_module_names)),
            pure_stdlib=tuple(pure_stdlib),
        )
