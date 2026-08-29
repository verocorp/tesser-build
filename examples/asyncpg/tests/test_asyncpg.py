from __future__ import annotations

import alpha.client.client as alpha_client
import app.loader as loader
import beta.client.client as beta_client


class TestLoadedApp:

    async def test_the_loaded_app_writes_and_reads_both_contexts(self) -> None:
        built = loader.load()
        await built.start()
        held = await built.beta.client.hold(beta_client.HoldRequest(key="e2e-held"))
        checked = await built.beta.client.check(beta_client.CheckRequest(key="e2e-held"))
        unheld = await built.beta.client.check(beta_client.CheckRequest(key="e2e-never-held"))
        taken = await built.alpha.client.add(alpha_client.AddRequest(name="e2e-taken", part="p"))
        found = await built.alpha.client.find(alpha_client.FindRequest(name="e2e-taken"))
        missing = await built.alpha.client.find(alpha_client.FindRequest(name="e2e-never-added"))
        kept = await built.alpha.client.add(alpha_client.AddRequest(name="e2e-held", part="e2e-held"))
        unsaved = await built.alpha.client.find(alpha_client.FindRequest(name="e2e-held"))
        await built.close()
        assert held.key == "e2e-held"
        assert checked.held == "yes"
        assert unheld.held == "no"
        assert taken.name == "e2e-taken"
        assert found.found == "yes"
        assert missing.found == "no"
        assert kept.name == "e2e-held"
        assert unsaved.found == "no"
