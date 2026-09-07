import pathlib

import tesser.adapters as ts

import tessercheck.application.ports as ports


class FilesystemSourceWriter(ts.Repository):

    def write(
        self, write_sources_request: ports.WriteSourcesRequest
    ) -> ports.WriteSourcesResponse:
        base = pathlib.Path(write_sources_request.tree).resolve()
        written = 0
        for source in write_sources_request.sources:
            path = base / source.path
            if path.is_symlink():
                continue
            resolved = path.resolve()
            if resolved != base and base not in resolved.parents:
                continue
            path.write_text(source.text, encoding="utf-8")
            written += 1
        return ports.WriteSourcesResponse(written=written)
