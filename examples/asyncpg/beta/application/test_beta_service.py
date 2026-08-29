from __future__ import annotations

import beta.application.beta_service as beta_service
import beta.domain.key as key


class TestBetaServiceMappers:

    def test_a_key_maps_to_a_has_key_request(self) -> None:
        assert beta_service.MapToHasKeyRequest(key.Key("k")).key == "k"

    def test_a_key_maps_to_a_put_key_request(self) -> None:
        assert beta_service.MapToPutKeyRequest(key.Key("k")).key == "k"
