from pathlib import Path

import pytest

import tessercheck.domain.checks as domain
import tessercheck.tests.conftest as conftest

def test_skip_dirs_are_not_walked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, ".venv/lib/junk.py", "def f(:\n")
    conftest.write_module(tmp_path, "node_modules/pkg/mod.py", "x = 1\n")
    assert conftest.check_tree(tmp_path) == ()

def test_a_utf8_bom_file_is_checked_normally(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / "app" / "domain" / "bom.py").write_bytes(
        b"\xef\xbb\xbfimport tesser.domain as ts\n"
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("bom" in f for f in findings)


def test_an_undeclared_tree_is_a_finding_and_nothing_else_is(tmp_path: Path) -> None:
    conftest.write_module(tmp_path, "stray.py", "import os\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "this tree is not declared; a checkable tree carries a .tesser-root file "
        "containing 'app' at its root" in f
        for f in findings
    ), f"an undeclared tree was walked as if declared: {findings}"


def test_an_unrecognized_declaration_is_a_finding(tmp_path: Path) -> None:
    conftest.write_module(tmp_path, "stray.py", "import os\n")
    (tmp_path / ".tesser-root").write_text("domain\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "this tree declares an unrecognized kind; a declaration is "
        "'app', then only 'skip <dir>' lines" in f
        for f in findings
    ), f"an unrecognized declaration passed: {findings}"


def test_an_unknown_directive_is_an_unrecognized_kind(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nignore stuff\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "unrecognized kind" in findings[0], findings


def test_an_unreadable_declaration_is_a_finding(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_bytes(b"\xff\xfe\x00app")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "this tree's declaration is not readable; "
        "a .tesser-root is a plain UTF-8 text file" in f
        for f in findings
    ), f"an undecodable declaration passed: {findings}"


def test_a_declaration_that_is_a_directory_is_unreadable(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").mkdir()
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "not readable" in findings[0], findings


def test_a_bom_prefixed_declaration_still_reads(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".tesser-root").write_bytes(b"\xef\xbb\xbfapp\n")
    assert conftest.check_raw(tmp_path) == ()


def test_a_nested_declaration_is_a_finding_and_masks_the_walk(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os\n")
    (tmp_path / "app" / ".tesser-root").write_text("app\n")
    findings = conftest.check_tree(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "declares a nested tree root; a tessercheck run covers one declared tree, "
        "so run that tree directly" in f
        for f in findings
    ), f"a nested declaration passed: {findings}"


def test_a_skipped_dir_hides_no_nested_declaration(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / ".tesser-root").write_text("app\n")
    assert conftest.check_tree(tmp_path) == ()


def test_a_declared_skip_dir_is_not_walked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".tesser-root").write_text("app\nskip fixtures\n")
    conftest.write_module(tmp_path, "fixtures/bad.py", "def f(:\n")
    assert conftest.check_raw(tmp_path) == ()


def test_a_symlinked_directory_is_a_finding(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "bad.py").write_text("def f(:\n")
    (tmp_path / "vendored").symlink_to(outside)
    findings = conftest.check_tree(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "vendored:1: TB045 is a symlinked directory; a declared tree is walked in "
        "full, and a symlink escapes the walk" in f
        for f in findings
    ), f"a symlinked directory escaped the walk silently: {findings}"


def test_a_declaration_finding_is_never_inline_suppressible(tmp_path: Path) -> None:
    conftest.write_module(
        tmp_path, "stray.py", "import os  # tessercheck:ignore TB044\n"
    )
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "TB044" in findings[0], findings


def test_a_bare_skip_directive_is_an_unrecognized_kind(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "unrecognized kind" in findings[0], findings


def test_a_skip_directive_with_a_path_is_an_unrecognized_kind(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip a/b\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "unrecognized kind" in findings[0], findings


def test_an_undeclared_testdata_dir_is_walked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "testdata/stray.py", "import os\n")
    findings = conftest.check_tree(tmp_path)
    assert any("TB040" in f and "testdata.stray" in f for f in findings), findings


def test_a_declared_skip_applies_at_any_depth(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".tesser-root").write_text("app\nskip fixtures\n")
    conftest.write_module(tmp_path, "app/domain/fixtures/bad.py", "def f(:\n")
    assert conftest.check_raw(tmp_path) == ()
