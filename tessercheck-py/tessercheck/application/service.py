import typing

import tesser.application as ts

import tesser.errors as errors
import tessercheck.application.ports as ports
import tessercheck.client as client
import tessercheck.domain as domain


class MapToTreeInspectionSpec(ts.Mapper, domain.TreeInspectionSpec):

    def __init__(self, read_sources_response: ports.ReadSourcesResponse) -> None:
        super().__init__(
            sources=tuple(
                (source.path, source.text if source.state is ports.SourceState.READ else None)
                for source in read_sources_response.sources
            ),
            directories=read_sources_response.directories,
            unreadable_directories=read_sources_response.unreadable_directories,
            declared=(
                read_sources_response.outcome is ports.ReadSourcesOutcome.APP
                and not read_sources_response.nested
                and not read_sources_response.symlinked
            ),
        )


class MapToInspectedSource(ts.Mapper, client.InspectedSource):

    def __init__(self, module_inspection: domain.ModuleInspection) -> None:
        super().__init__(
            path=str(module_inspection.path()),
            reached_contexts=tuple(module_inspection.reached()),
            client_calls=tuple(module_inspection.calls()),
            top_level_calls=tuple(module_inspection.top_level_calls()),
            exported_names=tuple(module_inspection.exports()),
        )


class MapToInspectTreeResponse(ts.Mapper, client.InspectTreeResponse):

    def __init__(self, tree_inspection: domain.TreeInspection) -> None:
        super().__init__(
            contexts=tuple(tree_inspection.contexts()),
            unclassified=tuple(tree_inspection.unclassified()),
            directories=tuple(tree_inspection.directories()),
            sources=tuple(MapToInspectedSource(module_inspection) for module_inspection in tree_inspection.modules()),
        )


class MapToCodebaseSpec(ts.Mapper, domain.CodebaseSpec):

    def __init__(
        self,
        read_sources_response: ports.ReadSourcesResponse,
        path: domain.Path | None = None,
    ) -> None:
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
        match read_sources_response.outcome:
            case ports.ReadSourcesOutcome.APP:
                declared = domain.DECLARED_APP
            case ports.ReadSourcesOutcome.MISSING:
                declared = domain.DECLARED_MISSING
            case ports.ReadSourcesOutcome.UNREADABLE:
                declared = domain.DECLARED_UNREADABLE
            case ports.ReadSourcesOutcome.UNRECOGNIZED:
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
            pruned=read_sources_response.pruned,
            scoped=() if path is None else (str(path),),
        )


class MapToCheckTreeResponse(ts.Mapper, client.CheckTreeResponse):

    def __init__(self, codebase: domain.Codebase) -> None:
        super().__init__(
            findings=tuple(sorted(
                f"{violation.path()}:{int(violation.line())}: "
                f"{violation.code()} {violation.text()}"
                for violation in codebase.violations()
            ))
        )


class MapToCheckFileResponse(ts.Mapper, client.CheckFileResponse):

    def __init__(self, codebase: domain.Codebase, path: domain.Path) -> None:
        match codebase.governance(path):
            case domain.Governance.GOVERNED:
                governance = domain.GOVERNANCE_GOVERNED
            case domain.Governance.SKIPPED:
                governance = domain.GOVERNANCE_SKIPPED
            case domain.Governance.OUTSIDE:
                governance = domain.GOVERNANCE_OUTSIDE
            case domain.Governance.UNDECLARED:
                governance = domain.GOVERNANCE_UNDECLARED
            case _ as never:
                typing.assert_never(never)
        violations = tuple(sorted(
            (
                f"{violation.path()}:{int(violation.line())}: {violation.code()} {violation.text()}",
                str(violation.code()),
            )
            for violation in codebase.violations()
        ))
        super().__init__(
            governance=governance,
            findings=tuple(finding for finding, code in violations),
            codes=tuple(code for finding, code in violations),
        )


class MapToCheckWriteResponse(ts.Mapper, client.CheckWriteResponse):

    def __init__(self, codebase: domain.Codebase, check_write_request: client.CheckWriteRequest) -> None:
        match codebase.governance(domain.Path(check_write_request.path)):
            case domain.Governance.GOVERNED:
                governance = domain.GOVERNANCE_GOVERNED
            case domain.Governance.SKIPPED:
                governance = domain.GOVERNANCE_SKIPPED
            case domain.Governance.OUTSIDE:
                governance = domain.GOVERNANCE_OUTSIDE
            case domain.Governance.UNDECLARED:
                governance = domain.GOVERNANCE_UNDECLARED
            case _ as never:
                typing.assert_never(never)
        violations = tuple(sorted(
            (
                f"{violation.path()}:{int(violation.line())}: {violation.code()} {violation.text()}",
                str(violation.code()),
            )
            for violation in codebase.violations()
        ))
        hook_run = domain.HookRun(domain.HookRunSpec(
            conf=check_write_request.conf, governance=governance, findings=len(violations)
        ))
        match hook_run.action():
            case domain.HookAction.DISABLED:
                action = "disabled"
            case domain.HookAction.SILENT:
                action = "silent"
            case domain.HookAction.ADVISE:
                action = "advise"
            case domain.HookAction.FEEDBACK:
                action = "feedback"
            case _ as never_action:
                typing.assert_never(never_action)
        super().__init__(
            governance=governance,
            mode=str(hook_run.conf()),
            action=action,
            findings=tuple(finding for finding, code in violations),
            codes=tuple(code for finding, code in violations),
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


class MapToMarkDebtResponse(ts.Mapper, client.MarkDebtResponse):

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


class MapToReadSourcesRequest(ts.Mapper, ports.ReadSourcesRequest):

    def __init__(self, tree_root: domain.TreeRoot) -> None:
        super().__init__(tree=str(tree_root))


class MapToReadRulebookRequest(ts.Mapper, ports.ReadRulebookRequest):

    def __init__(self, tree_root: domain.TreeRoot) -> None:
        super().__init__(tree=str(tree_root))


class MapToRulebookSpec(ts.Mapper, domain.RulebookSpec):

    def __init__(self, read_rulebook_response: ports.ReadRulebookResponse) -> None:
        super().__init__(
            checks_text=read_rulebook_response.checks_text,
            test_modules=tuple(
                (module.name, module.text)
                for module in read_rulebook_response.test_modules
            ),
            contracts_text=read_rulebook_response.contracts_text,
        )


class MapToRenderRulebookResponse(ts.Mapper, client.RenderRulebookResponse):

    def __init__(self, rulebook: domain.Rulebook) -> None:
        super().__init__(rendered=str(rulebook))


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


class MapToApplyRenamesResponse(ts.Mapper, client.ApplyRenamesResponse):

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

    def inspect_tree(self, inspect_tree_request: client.InspectTreeRequest) -> client.InspectTreeResponse:
        tree_root = domain.TreeRoot(inspect_tree_request.tree)
        read_sources_request = MapToReadSourcesRequest(tree_root)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        try:
            tree_inspection = domain.TreeInspection(MapToTreeInspectionSpec(read_sources_response))
        except errors.DomainError as domain_error:
            raise client.TreeNotInspected(domain_error.code, domain_error.message) from domain_error
        return MapToInspectTreeResponse(tree_inspection)

    def check_tree(self, check_tree_request: client.CheckTreeRequest) -> client.CheckTreeResponse:
        tree_root = domain.TreeRoot(check_tree_request.tree)
        read_sources_request = MapToReadSourcesRequest(tree_root)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        return MapToCheckTreeResponse(codebase)

    def check_file(self, check_file_request: client.CheckFileRequest) -> client.CheckFileResponse:
        tree_root = domain.TreeRoot(check_file_request.tree)
        read_sources_request = MapToReadSourcesRequest(tree_root)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        path = domain.Path(check_file_request.path)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response, path))
        return MapToCheckFileResponse(codebase, path)

    def check_write(self, check_write_request: client.CheckWriteRequest) -> client.CheckWriteResponse:
        tree_root = domain.TreeRoot(check_write_request.tree)
        read_sources_request = MapToReadSourcesRequest(tree_root)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        path = domain.Path(check_write_request.path)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response, path))
        return MapToCheckWriteResponse(codebase, check_write_request)

    def mark_debt(self, mark_debt_request: client.MarkDebtRequest) -> client.MarkDebtResponse:
        tree_root = domain.TreeRoot(mark_debt_request.tree)
        read_sources_request = MapToReadSourcesRequest(tree_root)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        marking = domain.Marking(MapToMarkingSpec(read_sources_response, codebase))
        rewritten_modules = marking.rewritten()
        write_sources_request = MapToWriteSourcesRequest(tree_root, rewritten_modules)
        write_sources_response = self._source_writer.write_sources(write_sources_request)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        return MapToMarkDebtResponse(write_sources_response, read_sources_response)

    def apply_renames(self, apply_renames_request: client.ApplyRenamesRequest) -> client.ApplyRenamesResponse:
        tree_root = domain.TreeRoot(apply_renames_request.tree)
        read_sources_request = MapToReadSourcesRequest(tree_root)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        codebase = domain.Codebase(MapToCodebaseSpec(read_sources_response))
        renaming = domain.Renaming(MapToRenamingSpec(read_sources_response, codebase))
        rewritten_modules = renaming.rewritten()
        write_sources_request = MapToWriteSourcesRequest(tree_root, rewritten_modules)
        write_sources_response = self._source_writer.write_sources(write_sources_request)
        read_sources_response = self._source_reader.read_sources(read_sources_request)
        return MapToApplyRenamesResponse(write_sources_response, read_sources_response)

    def render_rulebook(self, render_rulebook_request: client.RenderRulebookRequest) -> client.RenderRulebookResponse:
        tree_root = domain.TreeRoot(render_rulebook_request.tree)
        read_rulebook_request = MapToReadRulebookRequest(tree_root)
        read_rulebook_response = self._rulebook_sources.read_rulebook(read_rulebook_request)
        try:
            rulebook = domain.Rulebook(MapToRulebookSpec(read_rulebook_response))
        except errors.DomainError as domain_error:
            raise client.RulebookNotRendered(domain_error.code, domain_error.message) from domain_error
        return MapToRenderRulebookResponse(rulebook)
