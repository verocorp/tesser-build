from __future__ import annotations

import pathlib

import tessercheck.adapters.repositories as repositories
import tessercheck.application.ports as ports


def test_a_rewritten_source_replaces_the_file_it_names(tmp_path: pathlib.Path) -> None:
    module = tmp_path / "widget.py"
    module.write_text("was = 1\n", encoding="utf-8")
    filesystem_source_writer = repositories.FilesystemSourceWriter()
    write_sources_request = ports.WriteSourcesRequest(
        tree=str(tmp_path),
        sources=(ports.RewrittenSource(path="widget.py", text="now = 2\n"),),
    )
    write_sources_response = filesystem_source_writer.write(write_sources_request)
    assert write_sources_response.written == 1
    assert module.read_text(encoding="utf-8") == "now = 2\n"


def test_writing_nothing_touches_nothing(tmp_path: pathlib.Path) -> None:
    module = tmp_path / "widget.py"
    module.write_text("was = 1\n", encoding="utf-8")
    filesystem_source_writer = repositories.FilesystemSourceWriter()
    write_sources_request = ports.WriteSourcesRequest(tree=str(tmp_path), sources=())
    write_sources_response = filesystem_source_writer.write(write_sources_request)
    assert write_sources_response.written == 0
    assert module.read_text(encoding="utf-8") == "was = 1\n"
