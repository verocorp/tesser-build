import tesser.application as ts

import tessercheck.application.mapping as mapping
import tessercheck.domain.checks as checks
import tessercheck.domain.rulebook as rulebook
import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.application.ports.source_reader as source_reader
import tessercheck.client.client as client


class TessercheckService(ts.ApplicationService):

    def __init__(
        self,
        reader: source_reader.SourceReader,
        rulebook_reader: rulebook_sources.RulebookSources,
    ) -> None:
        self._reader = reader
        self._rulebook_reader = rulebook_reader

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        tree_root = checks.TreeRoot(request.tree)
        tree = str(tree_root)
        read = self._reader.sources(source_reader.ReadSourcesRequest(tree=tree))
        return mapping.MapToCheckResponse(read=read)

    def rulebook(self, request: client.RulebookRequest) -> client.RulebookResponse:
        tree_root = checks.TreeRoot(request.tree)
        tree = str(tree_root)
        read = self._rulebook_reader.read(rulebook_sources.ReadRulebookRequest(tree=tree))
        modules = tuple((module.name, module.text) for module in read.test_modules)
        book = rulebook.Rulebook(
            rulebook.RulebookSpec(
                checks_text=read.checks_text,
                test_modules=modules,
                contracts_text=read.contracts_text,
            )
        )
        rendered = str(book)
        return client.RulebookResponse(rendered=rendered)
