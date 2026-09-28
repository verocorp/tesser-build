import pathlib
import subprocess

import pytest

import tesserinspect.adapters.repositories as repositories
import tesserinspect.application.ports as ports


def test_real_git_checkout_includes_staged_unstaged_new_deleted_and_renamed_files(
    tmp_path: pathlib.Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name in (
        "test_staged.py",
        "test_unstaged.py",
        "test_deleted.py",
        "test_old.py",
    ):
        (tmp_path / name).write_text(
            f"def {name[:-3]}():\n    pass\n", encoding="utf-8"
        )
    (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "add",
            "--",
            ".gitignore",
            "test_staged.py",
            "test_unstaged.py",
            "test_deleted.py",
            "test_old.py",
        ],
        check=True,
    )
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    (tmp_path / "test_staged.py").write_text(
        "def test_staged():\n    assert True\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "--", "test_staged.py"], check=True
    )
    (tmp_path / "test_unstaged.py").write_text(
        "def test_unstaged():\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / "test_deleted.py").unlink()
    subprocess.run(
        ["git", "-C", str(tmp_path), "mv", "test_old.py", "test_renamed.py"], check=True
    )
    (tmp_path / "test_new.py").write_text(
        "raise RuntimeError('must never execute')\n", encoding="utf-8"
    )
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored/test_bad.py").write_bytes(b"\xff")
    git_checkout_reader = repositories.GitCheckoutReader()

    read_checkout_response = git_checkout_reader.read_checkout(
        ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
    )

    assert len(read_checkout_response.baseline) == 40
    assert set(read_checkout_response.changes) == {
        ("test_staged.py", "", "M"),
        ("test_unstaged.py", "", "M"),
        ("test_deleted.py", "", "D"),
        ("test_renamed.py", "test_old.py", "R100"),
        ("test_new.py", "", "?"),
    }
    assert "ignored/test_bad.py" not in read_checkout_response.paths
    assert "test_deleted.py" not in read_checkout_response.paths
    assert (
        "test_new.py",
        "raise RuntimeError('must never execute')\n",
    ) in read_checkout_response.sources


def test_rejects_invalid_refs_and_option_injection(tmp_path: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    git_checkout_reader = repositories.GitCheckoutReader()

    with pytest.raises(ValueError, match="not an option"):
        git_checkout_reader.read_checkout(
            ports.ReadCheckoutRequest(repo=str(tmp_path), base="--help")
        )
    with pytest.raises(subprocess.CalledProcessError):
        git_checkout_reader.read_checkout(
            ports.ReadCheckoutRequest(repo=str(tmp_path), base="missing-ref")
        )


def test_rejects_non_repository_and_non_utf8_source(tmp_path: pathlib.Path) -> None:
    git_checkout_reader = repositories.GitCheckoutReader()
    with pytest.raises(subprocess.CalledProcessError):
        git_checkout_reader.read_checkout(
            ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
        )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    (tmp_path / "test_bad.py").write_bytes(b"\xff")

    with pytest.raises(UnicodeDecodeError):
        git_checkout_reader.read_checkout(
            ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
        )


def test_never_follows_source_symlink(tmp_path: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    (tmp_path / "test_link.py").symlink_to("/etc/passwd")
    git_checkout_reader = repositories.GitCheckoutReader()

    with pytest.raises(OSError):
        git_checkout_reader.read_checkout(
            ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
        )


def test_staged_add_then_worktree_delete_is_retained_without_reading_absent_file(
    tmp_path: pathlib.Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    (tmp_path / "test_added.py").write_text("pass\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "test_added.py"], check=True)
    (tmp_path / "test_added.py").unlink()
    git_checkout_reader = repositories.GitCheckoutReader()

    read_checkout_response = git_checkout_reader.read_checkout(
        ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
    )

    assert read_checkout_response.working_tree_changes == (
        ("test_added.py", "", "A", "D"),
    )
    assert read_checkout_response.sources == ()


def test_repo_configured_filters_diff_drivers_and_fsmonitor_never_execute(
    tmp_path: pathlib.Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "test_changed.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "test_changed.py"], check=True)
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    (tmp_path / ".gitattributes").write_text(
        "*.py filter=trap diff=trap\n", encoding="utf-8"
    )
    (tmp_path / "test_changed.py").write_text("value = 2\n", encoding="utf-8")
    for key in (
        "filter.trap.clean",
        "filter.trap.process",
        "diff.trap.command",
        "diff.trap.textconv",
        "core.fsmonitor",
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", key, "touch EXECUTED; cat"],
            check=True,
        )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "filter.trap.required", "true"],
        check=True,
    )
    git_checkout_reader = repositories.GitCheckoutReader()

    read_checkout_response = git_checkout_reader.read_checkout(
        ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
    )

    assert ("test_changed.py", "", "M") in read_checkout_response.changes
    assert not (tmp_path / "EXECUTED").exists()


def test_staged_delete_then_untracked_recreation_reads_current_source(
    tmp_path: pathlib.Path,
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "test_recreated.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "test_recreated.py"], check=True)
    tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(tmp_path), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=f"tree {tree}\nauthor Synthetic Fixture <fixture@example.invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@example.invalid> 0 +0000\n\nSynthetic test baseline\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-ref", "HEAD", commit], check=True
    )
    subprocess.run(["git", "-C", str(tmp_path), "rm", "test_recreated.py"], check=True)
    (tmp_path / "test_recreated.py").write_text("value = 2\n", encoding="utf-8")
    git_checkout_reader = repositories.GitCheckoutReader()

    read_checkout_response = git_checkout_reader.read_checkout(
        ports.ReadCheckoutRequest(repo=str(tmp_path), base="HEAD")
    )

    assert ("test_recreated.py", "value = 2\n") in read_checkout_response.sources
    assert (
        "test_recreated.py",
        "",
        "D",
        " ",
    ) in read_checkout_response.working_tree_changes
    assert (
        "test_recreated.py",
        "",
        "?",
        "?",
    ) in read_checkout_response.working_tree_changes
