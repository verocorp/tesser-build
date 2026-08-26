from __future__ import annotations

import alpha.client.client as alpha_client
import alpha.component.component as alpha_component
import alpha.component.config as alpha_config
import beta.component.component as beta_component
import beta.component.config as beta_config


def test_two_real_components_wire_end_to_end() -> None:
    beta = beta_component.Beta(beta_config.Config(beta_config.Spec(keys=("w",))))
    alpha = alpha_component.Alpha(alpha_config.Config(alpha_config.Spec(storage="memory")), beta.client)
    added = alpha.client.add(alpha_client.AddRequest(id="w", name="a", count=1))
    assert tuple(view.id for view in added.wholes) == ("w",)
    alpha.close()
    beta.close()
