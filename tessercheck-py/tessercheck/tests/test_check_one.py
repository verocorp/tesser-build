import pathlib
import shutil

import tessercheck.tests.conftest as conftest


def test_check_one_matches_the_whole_tree_on_every_example_with_findings_injected(
    tmp_path: pathlib.Path,
) -> None:
    for tree in conftest.example_trees():
        root = tmp_path / tree.rsplit("/", 1)[-1]
        shutil.copytree(conftest.repo_root() / tree, root)
        touched = conftest.inject_findings(root)
        whole = conftest.check_raw(root)
        assert any(conftest.findings_on(whole, path) for path in touched), tree
        paths = conftest.governed_paths(root)
        for path in conftest.bounded_rebuilds(paths, must=touched):
            check_file_response = conftest.check_file_raw(root, path)
            assert check_file_response.governance == "governed", (tree, path)
            assert check_file_response.findings == conftest.findings_on(whole, path), (tree, path)


def test_check_one_matches_the_whole_tree_on_the_analyzer_itself_with_findings_injected(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "tessercheck-py"
    shutil.copytree(
        conftest.repo_root() / "tessercheck-py",
        root,
        ignore=shutil.ignore_patterns("__pycache__", ".venv", "build", "*.egg-info"),
    )
    touched = conftest.inject_findings(root)
    whole = conftest.check_raw(root)
    assert any(conftest.findings_on(whole, path) for path in touched)
    for path in conftest.bounded_rebuilds(conftest.governed_paths(root), must=touched, most=4):
        check_file_response = conftest.check_file_raw(root, path)
        assert check_file_response.governance == "governed", path
        assert check_file_response.findings == conftest.findings_on(whole, path), path


def test_check_one_matches_the_whole_tree_on_the_fixture_trees(tmp_path: pathlib.Path) -> None:
    for tree in conftest.fixture_trees():
        root = tmp_path / tree.rsplit("/", 1)[-1]
        shutil.copytree(conftest.repo_root() / tree, root)
        whole = conftest.check_tree(root)
        assert whole
        for path in conftest.governed_paths(root):
            check_file_response = conftest.check_file_raw(root, path)
            assert check_file_response.findings == conftest.findings_on(whole, path), (tree, path)


def test_check_one_reports_a_broken_tree_declaration_whole(tmp_path: pathlib.Path) -> None:
    conftest.write_module(tmp_path, "loose.py", "x = 1\n")
    conftest.write_module(tmp_path, "inner/.tesser-root", "app\n")
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    whole = conftest.check_raw(tmp_path)
    check_file_response = conftest.check_file_raw(tmp_path, "loose.py")
    assert whole
    assert all(" TB044 " in finding for finding in whole)
    assert check_file_response.governance == "undeclared"
    assert check_file_response.findings == whole


def test_check_one_governs_a_file_that_does_not_parse(tmp_path: pathlib.Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "shop/domain/broken.py", "def broken(:\n")
    whole = conftest.check_raw(tmp_path)
    check_file_response = conftest.check_file_raw(tmp_path, "shop/domain/broken.py")
    assert check_file_response.governance == "governed"
    assert check_file_response.findings == conftest.findings_on(whole, "shop/domain/broken.py")
    assert any(" TB043 " in finding for finding in check_file_response.findings)


def test_check_one_on_a_skipped_path_is_silent_while_the_whole_tree_is_too(tmp_path: pathlib.Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip legacy\n", encoding="utf-8")
    conftest.write_module(tmp_path, "legacy/old.py", "x = 1\n")
    conftest.conforming_tree(tmp_path)
    assert conftest.check_raw(tmp_path) == ()
    check_file_response = conftest.check_file_raw(tmp_path, "legacy/old.py")
    assert (check_file_response.governance, check_file_response.findings) == ("skipped", ())
