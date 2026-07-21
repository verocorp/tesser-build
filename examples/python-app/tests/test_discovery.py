from __future__ import annotations

import pathlib

from tests.discovery import ROOT, classify, exposes_client


def test_totality_every_root_package_classifies() -> None:
    contexts, unclassified = classify(ROOT)
    assert not unclassified, f"unclassified package(s) at app root: {unclassified}"
    assert contexts, "discovery found no contexts — the classifier is broken"


def test_totality_guard_teeth_flags_clientless_context(tmp_path: pathlib.Path) -> None:
    (tmp_path / "billing").mkdir()
    (tmp_path / "billing" / "__init__.py").write_text('"""a context that forgot its Client"""\n')
    contexts, unclassified = classify(tmp_path)
    assert unclassified == ["billing"]
    assert not contexts


def test_discovery_teeth_finds_client_bearing_context(tmp_path: pathlib.Path) -> None:
    (tmp_path / "billing").mkdir()
    (tmp_path / "billing" / "__init__.py").write_text("from billing.client import Client\n")
    contexts, unclassified = classify(tmp_path)
    assert contexts == ["billing"]
    assert not unclassified


def test_web_dir_is_app_level_not_a_context(tmp_path: pathlib.Path) -> None:
    (tmp_path / "web" / "admin").mkdir(parents=True)
    (tmp_path / "web" / "ops").mkdir()
    (tmp_path / "billing").mkdir()
    (tmp_path / "billing" / "__init__.py").write_text("from billing.client import Client\n")
    contexts, unclassified = classify(tmp_path)
    assert contexts == ["billing"]
    assert "web" not in unclassified
    assert "web" not in contexts


def test_exposes_client_detects_direct_definition(tmp_path: pathlib.Path) -> None:
    (tmp_path / "__init__.py").write_text(
        "from typing import Protocol\n\nclass Client(Protocol):\n    def ping(self) -> None: ...\n"
    )
    assert exposes_client(tmp_path)
