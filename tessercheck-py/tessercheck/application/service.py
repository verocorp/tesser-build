import typing

import tesser.application as ts

import tessercheck.application.ports as ports
import tessercheck.client as client
import tessercheck.domain as domain


class MapToCodebaseSpec(ts.Mapper, domain.CodebaseSpec):

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
        super().__init__(
            sources=tuple(rows),
            declared=declared,
            nested=read_sources_response.nested,
            symlinked=read_sources_response.symlinked,
            exports=read_sources_response.exports,
            imports=read_sources_response.imports,
            stdlib=read_sources_response.stdlib,
            pure_stdlib=read_sources_response.pure_stdlib,
        )


class MapToCheckResponse(ts.Mapper, client.CheckResponse):

    def __init__(self, read_sources_response: ports.ReadSourcesResponse) -> None:
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        super().__init__(
            findings=tuple(
                f"{violation.path()}:{int(violation.line())}: "
                f"{violation.code()} {violation.text()}"
                for violation in codebase.violations()
            )
        )


class MapToMarkingSpec(ts.Mapper, domain.MarkingSpec):

    def __init__(
        self,
        read_sources_response: ports.ReadSourcesResponse,
        codebase: domain.Codebase,
    ) -> None:
        marks: list[tuple[str, int, str]] = []
        for violation in codebase.violations():
            mark = violation.mark()
            if mark is None:
                continue
            marks.append((
                str(violation.path()),
                int(violation.line()),
                str(mark.code()),
            ))
        super().__init__(
            sources=tuple(
                (source.path, source.text) for source in read_sources_response.sources
            ),
            marks=tuple(marks),
        )


class MapToMarkResponse(ts.Mapper, client.MarkResponse):

    def __init__(
        self,
        write_sources_response: ports.WriteSourcesResponse,
        read_sources_response: ports.ReadSourcesResponse,
    ) -> None:
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        super().__init__(
            files=write_sources_response.written,
            remaining=tuple(
                f"{violation.path()}:{int(violation.line())}: "
                f"{violation.code()} {violation.text()}"
                for violation in codebase.violations()
            ),
        )


class MapToRenamingSpec(ts.Mapper, domain.RenamingSpec):

    def __init__(
        self,
        read_sources_response: ports.ReadSourcesResponse,
        codebase: domain.Codebase,
    ) -> None:
        renames: list[tuple[str, int, str, str]] = []
        for violation in codebase.violations():
            rename = violation.rename()
            if rename is None:
                continue
            renames.append((
                str(violation.path()),
                int(violation.line()),
                str(rename.actual()),
                str(rename.derived()),
            ))
        super().__init__(
            sources=tuple(
                (source.path, source.text) for source in read_sources_response.sources
            ),
            renames=tuple(renames),
        )


class MapToWriteSourcesRequest(ts.Mapper, ports.WriteSourcesRequest):

    def __init__(
        self,
        tree_root: domain.TreeRoot,
        rewritten_modules: tuple[domain.RewrittenModule, ...],
    ) -> None:
        super().__init__(
            tree=str(tree_root),
            sources=tuple(
                ports.RewrittenSource(
                    path=str(rewritten_module.path()),
                    text=str(rewritten_module.text()),
                )
                for rewritten_module in rewritten_modules
            ),
        )


class MapToRenameResponse(ts.Mapper, client.RenameResponse):

    def __init__(
        self,
        write_sources_response: ports.WriteSourcesResponse,
        codebase: domain.Codebase,
    ) -> None:
        remaining: list[str] = []
        for violation in codebase.violations():
            rename = violation.rename()
            if rename is not None:
                continue
            remaining.append(
                f"{violation.path()}:{int(violation.line())}: "
                f"{violation.code()} {violation.text()}"
            )
        super().__init__(
            files=write_sources_response.written, remaining=tuple(sorted(remaining))
        )


class TessercheckService(ts.ApplicationService):

    def __init__(
        self,
        source_reader: ports.SourceReader,
        source_writer: ports.SourceWriter,
        rulebook_sources: ports.RulebookSources,
    ) -> None:
        self._source_reader = source_reader
        self._source_writer = source_writer
        self._rulebook_sources = rulebook_sources

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        tree_root = domain.TreeRoot(check_request.tree)
        tree = str(tree_root)
        read_sources_response = self._source_reader.sources(ports.ReadSourcesRequest(tree=tree))
        return MapToCheckResponse(read_sources_response)

    def mark(self, mark_request: client.MarkRequest) -> client.MarkResponse:
        tree_root = domain.TreeRoot(mark_request.tree)
        tree = str(tree_root)
        read_sources_request = ports.ReadSourcesRequest(tree=tree)
        read_sources_response = self._source_reader.sources(read_sources_request)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        marking = domain.Marking(MapToMarkingSpec(read_sources_response, codebase))
        rewritten_modules = marking.rewritten()
        write_sources_request = MapToWriteSourcesRequest(tree_root, rewritten_modules)
        write_sources_response = self._source_writer.write(write_sources_request)
        read_sources_response = self._source_reader.sources(read_sources_request)
        return MapToMarkResponse(write_sources_response, read_sources_response)

    def rename(self, rename_request: client.RenameRequest) -> client.RenameResponse:
        tree_root = domain.TreeRoot(rename_request.tree)
        tree = str(tree_root)
        read_sources_request = ports.ReadSourcesRequest(tree=tree)
        read_sources_response = self._source_reader.sources(read_sources_request)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        renaming = domain.Renaming(MapToRenamingSpec(read_sources_response, codebase))
        rewritten_modules = renaming.rewritten()
        write_sources_request = MapToWriteSourcesRequest(tree_root, rewritten_modules)
        write_sources_response = self._source_writer.write(write_sources_request)
        return MapToRenameResponse(write_sources_response, codebase)

    def rulebook(self, rulebook_request: client.RulebookRequest) -> client.RulebookResponse:
        tree_root = domain.TreeRoot(rulebook_request.tree)
        tree = str(tree_root)
        read_rulebook_response = self._rulebook_sources.read(ports.ReadRulebookRequest(tree=tree))
        modules = tuple((module.name, module.text) for module in read_rulebook_response.test_modules)
        rulebook = domain.Rulebook(
            domain.RulebookSpec(
                checks_text=read_rulebook_response.checks_text,
                test_modules=modules,
                contracts_text=read_rulebook_response.contracts_text,
            )
        )
        rendered = str(rulebook)
        return client.RulebookResponse(rendered=rendered)
