from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import beta.application.beta_service as beta_service
import beta.application.ports.key_repository as key_repository
import beta.client.client as client
import beta.domain.key as key
import tesser.errors as errors


@ts.fake
class FakeKeyRepository(key_repository.KeyRepository):

    def __init__(self, keys: set[str]) -> None:
        self._keys = keys

    async def has_key(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        held = key_repository.Held.YES if request.key in self._keys else key_repository.Held.NO
        return key_repository.HasKeyResponse(held=held)

    async def put_key(self, request: key_repository.PutKeyRequest) -> key_repository.PutKeyResponse:
        self._keys.add(request.key)
        return key_repository.PutKeyResponse(key=request.key)


@ts.fake
class FakeCommittedKeyStore(key_repository.KeyStore):

    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.transactions = 0

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[key_repository.KeyRepository]:
        self.transactions += 1
        yield FakeKeyRepository(self.keys)


@ts.fake
class FakeUnavailableKeyStore(key_repository.KeyStore):

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[key_repository.KeyRepository]:
        raise errors.InfraError("key store unavailable")
        yield FakeKeyRepository(set())


class TestBetaServiceOverACommittedTransaction:

    async def test_check_reports_what_the_store_holds(self) -> None:
        key_store = FakeCommittedKeyStore()
        key_store.keys.add("k")
        service = beta_service.BetaService(key_store)
        checked = await service.check(client.CheckRequest(key="k"))
        missing = await service.check(client.CheckRequest(key="x"))
        assert checked.held == "yes"
        assert missing.held == "no"

    async def test_hold_puts_the_key_in_one_transaction_and_answers_it(self) -> None:
        key_store = FakeCommittedKeyStore()
        held = await beta_service.BetaService(key_store).hold(client.HoldRequest(key="k"))
        assert held.key == "k"
        assert key_store.keys == {"k"}
        assert key_store.transactions == 1


class TestBetaServiceOverAFailedTransaction:

    async def test_check_surfaces_the_failure(self) -> None:
        service = beta_service.BetaService(FakeUnavailableKeyStore())
        with pytest.raises(errors.InfraError):
            await service.check(client.CheckRequest(key="k"))

    async def test_hold_surfaces_the_failure(self) -> None:
        service = beta_service.BetaService(FakeUnavailableKeyStore())
        with pytest.raises(errors.InfraError):
            await service.hold(client.HoldRequest(key="k"))


class TestBetaServiceMappers:

    def test_a_key_maps_to_a_has_key_request(self) -> None:
        assert beta_service.MapToHasKeyRequest(key.Key("k")).key == "k"

    def test_a_key_maps_to_a_put_key_request(self) -> None:
        assert beta_service.MapToPutKeyRequest(key.Key("k")).key == "k"
