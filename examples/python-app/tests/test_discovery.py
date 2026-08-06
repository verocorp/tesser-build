from __future__ import annotations

import configparser
import pathlib

from tests.discovery import ROOT, classify, discovered_contexts, exposes_client


def test_totality_import_contracts_name_every_discovered_context() -> None:
    parser = configparser.ConfigParser()
    parser.read(ROOT / ".importlinter", encoding="utf-8")
    declared = set(parser["importlinter"]["root_packages"].split())
    guarded = set(parser["importlinter:contract:host-reaches-only-handlers"]["forbidden_modules"].split())
    contexts = set(discovered_contexts())
    assert contexts <= declared, f"context(s) absent from .importlinter root_packages: {sorted(contexts - declared)}"
    assert contexts <= guarded, f"a host may reach these contexts unchecked: {sorted(contexts - guarded)}"


def test_import_contract_totality_teeth_flags_an_unguarded_context(tmp_path: pathlib.Path) -> None:
    config = tmp_path / ".importlinter"
    config.write_text(
        "[importlinter]\nroot_packages =\n    campaign\n    srv\n\n"
        "[importlinter:contract:host-reaches-only-handlers]\nforbidden_modules =\n    campaign\n",
        encoding="utf-8",
    )
    parser = configparser.ConfigParser()
    parser.read(config, encoding="utf-8")
    declared = set(parser["importlinter"]["root_packages"].split())
    guarded = set(parser["importlinter:contract:host-reaches-only-handlers"]["forbidden_modules"].split())
    assert {"campaign", "reports"} - declared == {"reports"}
    assert {"campaign", "reports"} - guarded == {"reports"}


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
    (tmp_path / "billing" / "__init__.py").write_text("")
    (tmp_path / "billing" / "client.py").write_text(
        "from typing import Protocol\n\nclass Client(Protocol):\n    def ping(self) -> None: ...\n"
    )
    contexts, unclassified = classify(tmp_path)
    assert contexts == ["billing"]
    assert not unclassified


def test_web_dir_is_app_level_not_a_context(tmp_path: pathlib.Path) -> None:
    (tmp_path / "web" / "admin").mkdir(parents=True)
    (tmp_path / "web" / "ops").mkdir()
    (tmp_path / "billing").mkdir()
    (tmp_path / "billing" / "__init__.py").write_text("")
    (tmp_path / "billing" / "client.py").write_text(
        "from typing import Protocol\n\nclass Client(Protocol):\n    def ping(self) -> None: ...\n"
    )
    contexts, unclassified = classify(tmp_path)
    assert contexts == ["billing"]
    assert "web" not in unclassified
    assert "web" not in contexts


def test_exposes_client_detects_direct_definition(tmp_path: pathlib.Path) -> None:
    (tmp_path / "client.py").write_text(
        "from typing import Protocol\n\nclass Client(Protocol):\n    def ping(self) -> None: ...\n"
    )
    assert exposes_client(tmp_path)


def test_exposes_client_detects_a_client_package_reexport(tmp_path: pathlib.Path) -> None:
    (tmp_path / "client").mkdir()
    (tmp_path / "client" / "__init__.py").write_text("from client.iface import Client\n")
    assert exposes_client(tmp_path)
