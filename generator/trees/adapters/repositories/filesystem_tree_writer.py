from __future__ import annotations

import pathlib

import tesser.adapters as ts

import trees.application.ports as ports


class FilesystemTreeWriter(ts.Repository):

    def write_tree(self, write_tree_request: ports.WriteTreeRequest) -> ports.WriteTreeResponse:
        root = pathlib.Path(write_tree_request.out_dir)
        for file_record in write_tree_request.files:
            written = root / file_record.path
            written.parent.mkdir(parents=True, exist_ok=True)
            written.write_text(file_record.text, encoding="utf-8")
        return ports.WriteTreeResponse(paths=tuple(file_record.path for file_record in write_tree_request.files))
