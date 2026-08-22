import typing

import tesser.application as ts

import tessercheck.application.ports.source_reader as source_reader
import tessercheck.domain.checks as domain


def findings(read: source_reader.ReadSourcesResponse) -> tuple[str, ...]:  # tesser:debt TB051
    rows: list[tuple[str, str, str | None, bool]] = []
    for source in read.sources:
        match source.state:
            case source_reader.SourceState.READ:
                text: str | None = source.text
            case source_reader.SourceState.UNREADABLE:
                text = None
            case _ as unreachable:
                typing.assert_never(unreachable)
        match source.form:
            case source_reader.ModuleForm.PACKAGE:
                is_package = True
            case source_reader.ModuleForm.MODULE:
                is_package = False
            case _ as unreachable_form:
                typing.assert_never(unreachable_form)
        rows.append((source.path, source.name, text, is_package))
    match read.root:
        case source_reader.RootForm.APP:
            declared = domain.DECLARED_APP
        case source_reader.RootForm.MISSING:
            declared = domain.DECLARED_MISSING
        case source_reader.RootForm.UNREADABLE:
            declared = domain.DECLARED_UNREADABLE
        case source_reader.RootForm.UNRECOGNIZED:
            declared = domain.DECLARED_UNRECOGNIZED
        case _ as unreachable_root:
            typing.assert_never(unreachable_root)
    codebase = domain.Codebase(
        domain.CodebaseSpec(
            sources=tuple(rows),
            declared=declared,
            nested=read.nested,
            symlinked=read.symlinked,
            exports=read.exports,
            imports=read.imports,
            stdlib=read.stdlib,
        )
    )
    return tuple(
        f"{violation.path()}:{int(violation.line())}: "
        f"{violation.code()} {violation.text()}"
        for violation in codebase.violations()
    )

