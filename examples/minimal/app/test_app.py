from __future__ import annotations

import pytest

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.app as app
import app.config as config
import beta.component.config as beta_config
import tesser.errors as errors


def test_the_app_wires_alpha_through_beta() -> None:
    built = app.App(
        config.Config(
            config.Spec(
                alpha=alpha_config.Config(alpha_config.Spec(storage="memory")),
                beta=beta_config.Config(beta_config.Spec(keys=("w",))),
            )
        )
    )
    added = built.alpha.client.add(alpha_client.AddRequest(id="w", name="a", count=1))
    assert tuple(view.id for view in added.wholes) == ("w",)
    built.close()


def test_a_failing_component_releases_the_ones_before_it() -> None:
    with pytest.raises(errors.DomainError):
        app.App(
            config.Config(
                config.Spec(
                    alpha=alpha_config.Config(alpha_config.Spec(storage="disk")),
                    beta=beta_config.Config(beta_config.Spec(keys=())),
                )
            )
        )
