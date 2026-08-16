import tesser.application as ts

import tessercheck.application.mapping as mapping
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
        read = self._reader.sources(source_reader.ReadSourcesRequest(root=request.root))
        return client.CheckResponse(findings=mapping.findings(read))

    def rulebook(self, request: client.RulebookRequest) -> client.RulebookResponse:
        read = self._rulebook_reader.read(
            rulebook_sources.ReadRulebookRequest(root=request.root)
        )
        return client.RulebookResponse(rendered=mapping.rendered_rulebook(read))
