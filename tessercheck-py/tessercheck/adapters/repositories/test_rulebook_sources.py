from __future__ import annotations

import pathlib

import pytest

import tessercheck.adapters.repositories.rulebook_sources as rulebook_repository
import tessercheck.application.ports.rulebook_sources as rulebook_sources


def test_the_read_carries_the_checks_text_and_the_contracts_text(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "CODES = ('TB040',)\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text(
        "def test_wired() -> None:\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / ".importlinter").write_text(
        "[importlinter:contract:pure]\nname = domain stays pure\n", encoding="utf-8"
    )
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(tmp_path))
    )
    assert read.checks_text == "CODES = ('TB040',)\n"
    assert "domain stays pure" in read.contracts_text


def test_the_wired_module_leads_and_the_domain_siblings_follow_in_order(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "CODES = ()\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text(
        "wired = 1\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "domain" / "test_zebra.py").write_text(
        "zebra = 1\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "domain" / "test_alpha.py").write_text(
        "alpha = 1\n", encoding="utf-8"
    )
    (tmp_path / ".importlinter").write_text("[importlinter]\n", encoding="utf-8")
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(tmp_path))
    )
    assert [module.name for module in read.test_modules] == [
        "tessercheck/tests/test_checks.py",
        "tessercheck/domain/test_alpha.py",
        "tessercheck/domain/test_zebra.py",
    ]
    assert [module.text for module in read.test_modules] == [
        "wired = 1\n",
        "alpha = 1\n",
        "zebra = 1\n",
    ]


def test_a_domain_module_that_is_not_a_test_is_left_out(tmp_path: pathlib.Path) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "CODES = ()\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "domain" / "rulebook.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text(
        "wired = 1\n", encoding="utf-8"
    )
    (tmp_path / ".importlinter").write_text("[importlinter]\n", encoding="utf-8")
    read = rulebook_repository.FilesystemRulebookSources().read(
        rulebook_sources.ReadRulebookRequest(tree=str(tmp_path))
    )
    assert [module.name for module in read.test_modules] == [
        "tessercheck/tests/test_checks.py"
    ]


def test_a_tree_without_the_checks_module_refuses_to_answer(tmp_path: pathlib.Path) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text(
        "wired = 1\n", encoding="utf-8"
    )
    (tmp_path / ".importlinter").write_text("[importlinter]\n", encoding="utf-8")
    with pytest.raises(OSError):
        rulebook_repository.FilesystemRulebookSources().read(
            rulebook_sources.ReadRulebookRequest(tree=str(tmp_path))
        )


def test_a_tree_without_the_contracts_file_refuses_to_answer(tmp_path: pathlib.Path) -> None:
    (tmp_path / "tessercheck" / "domain").mkdir(parents=True)
    (tmp_path / "tessercheck" / "tests").mkdir(parents=True)
    (tmp_path / "tessercheck" / "domain" / "checks.py").write_text(
        "CODES = ()\n", encoding="utf-8"
    )
    (tmp_path / "tessercheck" / "tests" / "test_checks.py").write_text(
        "wired = 1\n", encoding="utf-8"
    )
    with pytest.raises(OSError):
        rulebook_repository.FilesystemRulebookSources().read(
            rulebook_sources.ReadRulebookRequest(tree=str(tmp_path))
        )
