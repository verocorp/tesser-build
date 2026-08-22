import typing

import tesser.application as ts

import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.application.ports.source_reader as source_reader
import tessercheck.domain.checks as domain
import tessercheck.domain.rulebook as rulebook


@ts.do_not_use_function
def findings(read: source_reader.ReadSourcesResponse) -> tuple[str, ...]:  # tesser:debt TB051
    codebase = domain.Codebase(
        domain.CodebaseSpec(
            sources=_sources(read),
            declared=_declared(read),
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


@ts.do_not_use_function
def _declared(read: source_reader.ReadSourcesResponse) -> str:  # tesser:debt TB051
    match read.root:
        case source_reader.RootForm.APP:
            return domain.DECLARED_APP
        case source_reader.RootForm.MISSING:
            return domain.DECLARED_MISSING
        case source_reader.RootForm.UNREADABLE:
            return domain.DECLARED_UNREADABLE
        case source_reader.RootForm.UNRECOGNIZED:
            return domain.DECLARED_UNRECOGNIZED
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def _sources(  # tesser:debt TB051
    read: source_reader.ReadSourcesResponse,
) -> tuple[tuple[str, str, str | None, bool], ...]:
    return tuple(
        (source.path, source.name, _text(source), _is_package(source))
        for source in read.sources
    )


@ts.do_not_use_function
def _is_package(source: source_reader.SourceFile) -> bool:  # tesser:debt TB051
    match source.form:
        case source_reader.ModuleForm.PACKAGE:
            return True
        case source_reader.ModuleForm.MODULE:
            return False
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def _text(source: source_reader.SourceFile) -> str | None:  # tesser:debt TB051
    match source.state:
        case source_reader.SourceState.READ:
            return source.text
        case source_reader.SourceState.UNREADABLE:
            return None
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def rendered_rulebook(read: rulebook_sources.ReadRulebookResponse) -> str:  # tesser:debt TB051
    return rulebook.render(
        read.checks_text,
        tuple((module.name, module.text) for module in read.test_modules),
        read.contracts_text,
    )
