import typing

import tesser.application as ts

import tessercheck.application.ports as ports
import tessercheck.client as client
import tessercheck.domain as domain


class MapToCheckResponse(ts.Mapper, client.CheckResponse):

    def __init__(self, read_sources_response: ports.ReadSourcesResponse) -> None:
        rows: list[tuple[str, str, str | None, bool]] = []
        for source in read_sources_response.sources:
            match source.state:
                case ports.SourceState.READ:
                    text: str | None = source.text
                case ports.SourceState.UNREADABLE:
                    text = None
                case _ as unreachable:
                    typing.assert_never(unreachable)
            match source.form:
                case ports.ModuleForm.PACKAGE:
                    is_package = True
                case ports.ModuleForm.MODULE:
                    is_package = False
                case _ as unreachable_form:
                    typing.assert_never(unreachable_form)
            rows.append((source.path, source.name, text, is_package))
        match read_sources_response.root:
            case ports.RootForm.APP:
                declared = domain.DECLARED_APP
            case ports.RootForm.MISSING:
                declared = domain.DECLARED_MISSING
            case ports.RootForm.UNREADABLE:
                declared = domain.DECLARED_UNREADABLE
            case ports.RootForm.UNRECOGNIZED:
                declared = domain.DECLARED_UNRECOGNIZED
            case _ as unreachable_root:
                typing.assert_never(unreachable_root)
        codebase = domain.Codebase(
            domain.CodebaseSpec(
                sources=tuple(rows),
                declared=declared,
                nested=read_sources_response.nested,
                symlinked=read_sources_response.symlinked,
                exports=read_sources_response.exports,
                imports=read_sources_response.imports,
                stdlib=read_sources_response.stdlib,
                pure_stdlib=read_sources_response.pure_stdlib,
            )
        )
        super().__init__(
            findings=tuple(
                f"{violation.path()}:{int(violation.line())}: "
                f"{violation.code()} {violation.text()}"
                for violation in codebase.violations()
            )
        )


class TessercheckService(ts.ApplicationService):

    def __init__(
        self,
        source_reader: ports.SourceReader,
        rulebook_sources: ports.RulebookSources,
    ) -> None:
        self._source_reader = source_reader
        self._rulebook_sources = rulebook_sources

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        tree_root = domain.TreeRoot(check_request.tree)
        tree = str(tree_root)
        read = self._source_reader.sources(ports.ReadSourcesRequest(tree=tree))
        return MapToCheckResponse(read)

    def rulebook(self, rulebook_request: client.RulebookRequest) -> client.RulebookResponse:
        tree_root = domain.TreeRoot(rulebook_request.tree)
        tree = str(tree_root)
        read = self._rulebook_sources.read(ports.ReadRulebookRequest(tree=tree))
        modules = tuple((module.name, module.text) for module in read.test_modules)
        rulebook = domain.Rulebook(
            domain.RulebookSpec(
                checks_text=read.checks_text,
                test_modules=modules,
                contracts_text=read.contracts_text,
            )
        )
        rendered = str(rulebook)
        return client.RulebookResponse(rendered=rendered)
