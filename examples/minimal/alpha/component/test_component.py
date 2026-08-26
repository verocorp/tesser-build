from __future__ import annotations

import pytest
import tesser.testing as ts

import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config
import beta.client.client as beta_client
import tesser.errors as errors


@ts.fake
class FakeBetaClient(beta_client.Client):

    def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held="yes")


def test_the_wired_client_adds_a_whole() -> None:
    wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaClient())
    added = wired.client.add(client.AddRequest(id="w", name="a", count=1))
    assert tuple(view.id for view in added.wholes) == ("w",)
    wired.close()


def test_an_unknown_backend_is_refused() -> None:
    with pytest.raises(errors.DomainError):
        component.Alpha(config.Config(config.Spec(storage="disk")), FakeBetaClient())
