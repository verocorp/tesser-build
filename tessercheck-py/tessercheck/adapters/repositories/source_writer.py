import pathlib

import tesser.adapters as ts

import tessercheck.application.ports as ports


class FilesystemSourceWriter(ts.Repository):

    def write(
        self, write_sources_request: ports.WriteSourcesRequest
    ) -> ports.WriteSourcesResponse:
        base = pathlib.Path(write_sources_request.tree)
        written = 0
        for source in write_sources_request.sources:
            path = base / source.path
            path.write_text(source.text, encoding="utf-8")
            written += 1
        return ports.WriteSourcesResponse(written=written)
