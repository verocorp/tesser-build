from __future__ import annotations

import pytest

import specification.client as client
import specification.component as component
import tesser.errors as errors


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(storage="memory")
        config = component.Config(spec)
        assert config.storage == spec.storage


class TestSpecification:

    def test_the_wired_client_adds_a_story(self) -> None:
        specification = component.Specification(component.Config(component.Spec(storage="memory")))
        add_story_response = specification.client.add_story(
            client.AddStoryRequest(jtbd_id="j-root", given="g", when="w", then="t")
        )
        assert add_story_response.story_id == "j-root-s0"

    def test_an_unknown_storage_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            component.Specification(component.Config(component.Spec(storage="disk")))
        assert caught.value.code == "unknown_backend"
