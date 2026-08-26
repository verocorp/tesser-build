from __future__ import annotations

import tesser.application as ts

import beta.application.ports.key_store as key_store
import beta.client.client as client
import beta.domain.key as key


class BetaService(ts.ApplicationService):

    def __init__(self, keys: key_store.KeyStore) -> None:
        self._keys = keys

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        checked_key = key.Key(request.key)
        checked_key_text = str(checked_key)
        answer = self._keys.has(key_store.HasKeyRequest(key=checked_key_text))
        return client.CheckResponse(held=answer.held.value)
