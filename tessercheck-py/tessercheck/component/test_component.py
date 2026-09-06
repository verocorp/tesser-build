from __future__ import annotations

import tessercheck.component.component as component


def test_a_config_constructs_from_its_spec() -> None:
    assert isinstance(component.Config(component.Spec()), component.Config)


def test_each_config_is_its_own() -> None:
    assert component.Config(component.Spec()) is not component.Config(component.Spec())


def test_a_component_exposes_a_client() -> None:
    assert component.Tessercheck(component.Config(component.Spec())).client is not None


def test_each_component_gets_its_own_client() -> None:
    first = component.Tessercheck(component.Config(component.Spec()))
    second = component.Tessercheck(component.Config(component.Spec()))

    assert first.client is not second.client


def test_a_component_closes_what_it_built() -> None:
    tessercheck = component.Tessercheck(component.Config(component.Spec()))

    tessercheck.close()

    assert tessercheck.client is not None


def test_a_component_takes_the_config_it_is_given() -> None:
    tessercheck = component.Tessercheck(component.Config(component.Spec()))

    assert tessercheck.client is not None
