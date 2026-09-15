from __future__ import annotations

import os
import pathlib
import subprocess
import sys


class TestGenerateHost:

    def test_the_voice_spec_generates_and_exits_zero_listing_what_it_wrote(self, tmp_path: pathlib.Path) -> None:
        tree = pathlib.Path(__file__).resolve().parents[2]

        result = subprocess.run(
            [sys.executable, "-m", "srv.cli.generate", str(tree / "specs" / "voice.toml"), str(tmp_path / "voice")],
            cwd=tree,
            env={**os.environ, "PYTHONPATH": os.pathsep.join([str(tree), str(tree.parent / "tesser-py")])},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert "calls/domain/call.py" in result.stdout.splitlines()
        assert (tmp_path / "voice" / "calls" / "domain" / "call.py").is_file()

    def test_an_occupied_output_directory_exits_one_on_stderr(self, tmp_path: pathlib.Path) -> None:
        tree = pathlib.Path(__file__).resolve().parents[2]
        (tmp_path / "voice").mkdir()
        (tmp_path / "voice" / "kept.txt").write_text("kept\n")

        result = subprocess.run(
            [sys.executable, "-m", "srv.cli.generate", str(tree / "specs" / "voice.toml"), str(tmp_path / "voice")],
            cwd=tree,
            env={**os.environ, "PYTHONPATH": os.pathsep.join([str(tree), str(tree.parent / "tesser-py")])},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert result.stderr == "generate: the output directory is not empty\n"

    def test_a_missing_argument_exits_two_with_the_usage(self) -> None:
        tree = pathlib.Path(__file__).resolve().parents[2]

        result = subprocess.run(
            [sys.executable, "-m", "srv.cli.generate"],
            cwd=tree,
            env={**os.environ, "PYTHONPATH": os.pathsep.join([str(tree), str(tree.parent / "tesser-py")])},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 2
        assert "usage: python -m srv.cli.generate" in result.stderr
