import typing

import tesser.application as ts

import tessercheck.application.ports.source_reader as source_reader
import tessercheck.domain.checks as domain


@ts.function
def findings(read: source_reader.ReadSourcesResponse) -> tuple[str, ...]:
    codebase = domain.Codebase(domain.CodebaseSpec(sources=_sources(read)))
    return tuple(
        f"{violation.path()}:{int(violation.line())}: "
        f"{violation.code()} {violation.text()}"
        for violation in codebase.violations()
    )


@ts.function
def _sources(
    read: source_reader.ReadSourcesResponse,
) -> tuple[tuple[str, str, str | None, bool], ...]:
    return tuple(
        (source.path, source.name, _text(source), _is_package(source))
        for source in read.sources
    )


@ts.function
def _is_package(source: source_reader.SourceFile) -> bool:
    match source.form:
        case source_reader.ModuleForm.PACKAGE:
            return True
        case source_reader.ModuleForm.MODULE:
            return False
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def _text(source: source_reader.SourceFile) -> str | None:
    match source.state:
        case source_reader.SourceState.READ:
            return source.text
        case source_reader.SourceState.UNREADABLE:
            return None
        case _ as unreachable:
            typing.assert_never(unreachable)
