from __future__ import annotations

import tessercheck.wiring.config as config
import tessercheck.wiring.wire as wire


def test_a_component_exposes_a_client() -> None:
    assert wire.Tessercheck(config.Config(config.Spec())).client is not None


def test_each_component_gets_its_own_client() -> None:
    first = wire.Tessercheck(config.Config(config.Spec()))
    second = wire.Tessercheck(config.Config(config.Spec()))

    assert first.client is not second.client


def test_a_component_closes_what_it_built() -> None:
    built = wire.Tessercheck(config.Config(config.Spec()))

    built.close()

    assert built.client is not None
