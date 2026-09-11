from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import beta.application as application
import beta.application.ports as ports
import beta.client as client
import beta.domain as domain


@ts.fake
class FakeKeyRepository(ports.KeyRepository):

    def __init__(self, keys: set[str]) -> None:
        self._keys = keys

    async def has_key(self, has_key_request: ports.HasKeyRequest) -> ports.HasKeyResponse:
        held = ports.Held.YES if has_key_request.key in self._keys else ports.Held.NO
        return ports.HasKeyResponse(held=held)

    async def put_key(self, put_key_request: ports.PutKeyRequest) -> ports.PutKeyResponse:
        self._keys.add(put_key_request.key)
        return ports.PutKeyResponse(key=put_key_request.key)


@ts.fake
class FakeCommittedKeyStore(ports.KeyStore):

    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.transactions = 0

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.KeyRepository]:
        self.transactions += 1
        yield FakeKeyRepository(self.keys)


@ts.fake
class FakeUnavailableKeyStore(ports.KeyStore):

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.KeyRepository]:
        raise ports.StoreUnavailable("key store unavailable")
        yield FakeKeyRepository(set())


class TestBetaServiceOverACommittedTransaction:

    async def test_check_reports_what_the_store_holds(self) -> None:
        fake_committed_key_store = FakeCommittedKeyStore()
        fake_committed_key_store.keys.add("k")
        beta_service = application.BetaService(fake_committed_key_store)
        checked = await beta_service.check(client.CheckRequest(key="k"))
        missing = await beta_service.check(client.CheckRequest(key="x"))
        assert checked.held == "yes"
        assert missing.held == "no"

    async def test_hold_puts_the_key_in_one_transaction_and_answers_it(self) -> None:
        fake_committed_key_store = FakeCommittedKeyStore()
        hold_response = await application.BetaService(fake_committed_key_store).hold(client.HoldRequest(key="k"))
        assert hold_response.key == "k"
        assert fake_committed_key_store.keys == {"k"}
        assert fake_committed_key_store.transactions == 1


class TestBetaServiceOverAFailedTransaction:

    async def test_check_crosses_as_the_contexts_unavailable(self) -> None:
        beta_service = application.BetaService(FakeUnavailableKeyStore())
        with pytest.raises(client.Unavailable) as caught:
            await beta_service.check(client.CheckRequest(key="k"))
        assert caught.value.message == "the key store is unavailable"
        assert isinstance(caught.value.__cause__, ports.StoreUnavailable)

    async def test_hold_crosses_as_the_contexts_unavailable(self) -> None:
        beta_service = application.BetaService(FakeUnavailableKeyStore())
        with pytest.raises(client.Unavailable) as caught:
            await beta_service.hold(client.HoldRequest(key="k"))
        assert caught.value.message == "the key store is unavailable"
        assert isinstance(caught.value.__cause__, ports.StoreUnavailable)


class TestBetaServiceMappers:

    def test_a_key_maps_to_a_has_key_request(self) -> None:
        assert application.MapToHasKeyRequest(domain.Key("k")).key == "k"

    def test_a_key_maps_to_a_put_key_request(self) -> None:
        assert application.MapToPutKeyRequest(domain.Key("k")).key == "k"
