import pathlib
import shutil

import tessercheck.tests.conftest as conftest


def test_check_one_matches_the_whole_tree_on_every_gated_example() -> None:
    for tree in conftest.example_trees():
        root = conftest.repo_root() / tree
        whole = conftest.check_raw(root)
        paths = conftest.governed_paths(root)
        assert paths, tree
        for path in conftest.sampled(paths):
            check_file_response = conftest.check_file_raw(root, path)
            assert check_file_response.governance == "governed", (tree, path)
            assert check_file_response.findings == conftest.findings_on(whole, path), (tree, path)


def test_check_one_matches_the_whole_tree_on_the_fixture_trees_that_have_findings(
    tmp_path: pathlib.Path,
) -> None:
    seen_a_finding = False
    for tree in conftest.fixture_trees():
        root = tmp_path / tree.rsplit("/", 1)[-1]
        shutil.copytree(conftest.repo_root() / tree, root)
        whole = conftest.check_tree(root)
        for path in conftest.governed_paths(root):
            check_file_response = conftest.check_file_raw(root, path)
            expected = conftest.findings_on(whole, path)
            seen_a_finding = seen_a_finding or bool(expected)
            assert check_file_response.findings == expected, (tree, path)
    assert seen_a_finding


def test_check_one_reports_a_broken_tree_declaration_whole(tmp_path: pathlib.Path) -> None:
    conftest.write_module(tmp_path, "loose.py", "x = 1\n")
    conftest.write_module(tmp_path, "inner/.tesser-root", "app\n")
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    whole = conftest.check_raw(tmp_path)
    check_file_response = conftest.check_file_raw(tmp_path, "loose.py")
    assert whole
    assert all(":TB044" in finding or " TB044 " in finding for finding in whole)
    assert check_file_response.governance == "undeclared"
    assert check_file_response.findings == whole


def test_check_one_on_a_skipped_path_is_silent_while_the_whole_tree_is_too(tmp_path: pathlib.Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip legacy\n", encoding="utf-8")
    conftest.write_module(tmp_path, "legacy/old.py", "x = 1\n")
    conftest.conforming_tree(tmp_path)
    assert conftest.check_raw(tmp_path) == ()
    check_file_response = conftest.check_file_raw(tmp_path, "legacy/old.py")
    assert (check_file_response.governance, check_file_response.findings) == ("skipped", ())
