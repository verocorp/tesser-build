import tesser.application as ts

import tessercheck.application.mapping as mapping
import tessercheck.domain.checks as checks
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
        return client.CheckResponse(findings=mapping.findings(read))  # tesser:debt TB082

    def rulebook(self, request: client.RulebookRequest) -> client.RulebookResponse:
        tree_root = checks.TreeRoot(request.tree)
        tree = str(tree_root)
        read = self._rulebook_reader.read(rulebook_sources.ReadRulebookRequest(tree=tree))
        return client.RulebookResponse(rendered=mapping.rendered_rulebook(read))  # tesser:debt TB082
