from __future__ import annotations

import alpha.client.client as alpha_client
import app.loader as loader
import beta.client.client as beta_client


class TestLoadedApp:

    async def test_a_second_load_reads_what_the_first_wrote(self) -> None:
        first = loader.load()
        held = await first.beta.client.hold(beta_client.HoldRequest(key="k"))
        await first.close()
        second = loader.load()
        checked = await second.beta.client.check(beta_client.CheckRequest(key="k"))
        await second.close()
        assert held.key == "k"
        assert checked.held == "yes"

    async def test_alpha_takes_a_new_part_and_checks_a_held_one_through_beta(self) -> None:
        built = loader.load()
        await built.beta.client.hold(beta_client.HoldRequest(key="a"))
        taken = await built.alpha.client.add(alpha_client.AddRequest(name="b", part="p"))
        checked = await built.alpha.client.add(alpha_client.AddRequest(name="a", part="a"))
        await built.close()
        assert taken.name == "b"
        assert checked.name == "a"
