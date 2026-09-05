import tesser.application as ts

import tessercheck.application.mapping as mapping
import tessercheck.application.ports as ports
import tessercheck.client as client
import tessercheck.domain as domain


class TessercheckService(ts.ApplicationService):

    def __init__(
        self,
        reader: ports.SourceReader,
        rulebook_reader: ports.RulebookSources,
    ) -> None:
        self._reader = reader
        self._rulebook_reader = rulebook_reader

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        tree_root = domain.TreeRoot(request.tree)
        tree = str(tree_root)
        read = self._reader.sources(ports.ReadSourcesRequest(tree=tree))
        return mapping.MapToCheckResponse(read=read)

    def rulebook(self, request: client.RulebookRequest) -> client.RulebookResponse:
        tree_root = domain.TreeRoot(request.tree)
        tree = str(tree_root)
        read = self._rulebook_reader.read(ports.ReadRulebookRequest(tree=tree))
        modules = tuple((module.name, module.text) for module in read.test_modules)
        book = domain.Rulebook(
            domain.RulebookSpec(
                checks_text=read.checks_text,
                test_modules=modules,
                contracts_text=read.contracts_text,
            )
        )
        rendered = str(book)
        return client.RulebookResponse(rendered=rendered)
