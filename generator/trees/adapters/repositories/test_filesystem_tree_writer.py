from __future__ import annotations

import pathlib

import trees.adapters.repositories as repositories
import trees.application.ports as ports


class TestFilesystemTreeWriter:

    def test_every_file_is_written_under_the_output_directory_at_its_path(self, tmp_path: pathlib.Path) -> None:
        filesystem_tree_writer = repositories.FilesystemTreeWriter()

        write_tree_response = filesystem_tree_writer.write_tree(
            ports.WriteTreeRequest(
                out_dir=str(tmp_path / "out"),
                files=(
                    ports.FileRecord(path=".tesser-root", text="app\n"),
                    ports.FileRecord(path="calls/domain/call.py", text="class Call:\n"),
                    ports.FileRecord(path="calls/__init__.py", text=""),
                ),
            )
        )

        assert (tmp_path / "out" / ".tesser-root").read_text() == "app\n"
        assert (tmp_path / "out" / "calls" / "domain" / "call.py").read_text() == "class Call:\n"
        assert (tmp_path / "out" / "calls" / "__init__.py").read_text() == ""
        assert write_tree_response.paths == (".tesser-root", "calls/domain/call.py", "calls/__init__.py")
