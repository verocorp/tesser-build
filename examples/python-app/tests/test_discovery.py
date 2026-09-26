from __future__ import annotations

import configparser
import pathlib

import tessercheck.client as tessercheck_client
import tessercheck.component as tessercheck_component


def test_totality_import_contracts_name_every_discovered_context() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    parser = configparser.ConfigParser()
    parser.read(root / ".importlinter", encoding="utf-8")
    declared = set(parser["importlinter"]["root_packages"].split())
    guarded = set(parser["importlinter:contract:host-reaches-only-handlers"]["forbidden_modules"].split())
    contexts = set(inspect_tree_response.contexts)
    assert contexts <= declared, f"context(s) absent from .importlinter root_packages: {sorted(contexts - declared)}"
    assert contexts <= guarded, f"a host may reach these contexts unchecked: {sorted(contexts - guarded)}"


def test_totality_every_root_package_classifies() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    assert not inspect_tree_response.unclassified, f"unclassified package(s) at app root: {inspect_tree_response.unclassified}"
    assert inspect_tree_response.contexts, "discovery found no contexts — the classifier is broken"


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
