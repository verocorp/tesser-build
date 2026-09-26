from __future__ import annotations

import pathlib

import tessercheck.client as tessercheck_client
import tessercheck.component as tessercheck_component

import campaign.client as campaign_client
import linkpolicy.client as linkpolicy_client
import reports.client as reports_client


def test_required_roles_present_per_context() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    for context in inspect_tree_response.contexts:
        for role in ("domain", "application", "component"):
            assert f"{context}/{role}" in inspect_tree_response.directories, f"{context}/{role} missing"


def test_public_interface_is_client_plus_dtos_in_the_client_package() -> None:
    assert hasattr(campaign_client, "CampaignClient")
    assert hasattr(linkpolicy_client, "LinkPolicyClient")
    assert hasattr(reports_client, "ReportsClient")


def test_config_lives_in_the_component_not_on_the_public_top_level() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    sources = {source.path: source for source in inspect_tree_response.sources}
    for context in inspect_tree_response.contexts:
        assert "Config" in sources[f"{context}/component/__init__.py"].exported_names, f"{context}/component does not export its Config"
        assert f"{context}/config.py" not in sources, f"{context} config leaked to the public top level"
