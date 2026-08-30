from __future__ import annotations

import campaign.client.client as campaign_client
import linkpolicy.client.client as linkpolicy_client
import reports.client.client as reports_client
import tests.discovery as discovery
import tests.support as support


def test_required_roles_present_per_context() -> None:
    for ctx in discovery.discovered_contexts():
        for role in ("domain", "application", "component"):
            assert (support.ROOT / ctx / role).is_dir(), f"{ctx}/{role} missing"


def test_public_interface_is_client_plus_dtos_in_the_client_module() -> None:
    assert hasattr(campaign_client, "Client")
    assert hasattr(linkpolicy_client, "Client")
    assert hasattr(reports_client, "Client")


def test_config_lives_in_the_component_not_on_the_public_top_level() -> None:
    for ctx in discovery.discovered_contexts():
        assert (support.ROOT / ctx / "component" / "config.py").is_file()
        assert not (support.ROOT / ctx / "config.py").exists(), f"{ctx} config leaked to the public top level"
