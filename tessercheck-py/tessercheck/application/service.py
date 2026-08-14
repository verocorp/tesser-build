import tesser.application as ts

import tessercheck.application.mapping as mapping
import tessercheck.application.ports.source_reader as source_reader
import tessercheck.client.client as client


class TessercheckService(ts.ApplicationService):

    def __init__(self, reader: source_reader.SourceReader) -> None:
        self._reader = reader

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        read = self._reader.sources(source_reader.ReadSourcesRequest(root=request.root))
        return client.CheckResponse(findings=mapping.findings(read))
