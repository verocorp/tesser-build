from __future__ import annotations

import alpha.client.client as alpha_client
import app.loader as loader
import beta.client.client as beta_client


class TestLoadedApp:

    async def test_the_loaded_app_writes_and_reads_both_contexts(self) -> None:
        app = loader.load()
        await app.open()
        held = await app.beta.client.hold(beta_client.HoldRequest(key="e2e-held"))
        checked = await app.beta.client.check(beta_client.CheckRequest(key="e2e-held"))
        unheld = await app.beta.client.check(beta_client.CheckRequest(key="e2e-never-held"))
        taken = await app.alpha.client.add(alpha_client.AddRequest(name="e2e-taken", part="p"))
        found = await app.alpha.client.find(alpha_client.FindRequest(name="e2e-taken"))
        missing = await app.alpha.client.find(alpha_client.FindRequest(name="e2e-never-added"))
        kept = await app.alpha.client.add(alpha_client.AddRequest(name="e2e-held", part="e2e-held"))
        cleared = await app.alpha.client.find(alpha_client.FindRequest(name="e2e-held"))
        dropped = await app.alpha.client.add(
            alpha_client.AddRequest(name="e2e-never-held", part="e2e-never-held")
        )
        refused = await app.alpha.client.find(alpha_client.FindRequest(name="e2e-never-held"))
        reloaded = await app.alpha.client.take(alpha_client.TakeRequest(name="e2e-never-held", part="q"))
        retaken = await app.alpha.client.take(alpha_client.TakeRequest(name="e2e-taken", part="q"))
        await app.close()
        assert held.key == "e2e-held"
        assert checked.held == "yes"
        assert unheld.held == "no"
        assert taken.name == "e2e-taken"
        assert found.found == "yes"
        assert missing.found == "no"
        assert kept.name == "e2e-held"
        assert kept.standing == "kept"
        assert cleared.found == "yes"
        assert dropped.name == "e2e-never-held"
        assert dropped.standing == "released"
        assert refused.found == "yes"
        assert reloaded.standing == "released"
        assert retaken.part == "q"
