from __future__ import annotations

import pathlib

import pytest

import tessercheck.client as client
import tessercheck.component as component


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


def test_the_shipped_component_inspects_real_sources_through_its_client(tmp_path: pathlib.Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n")
    (tmp_path / "reports" / "client").mkdir(parents=True)
    (tmp_path / "reports" / "client" / "__init__.py").write_text("from reports.client.client import ReportsClient\n")
    (tmp_path / "srv").mkdir()
    (tmp_path / "srv" / "main.py").write_text("def run(app):\n    reports = app.reports\n    reports.fetch()\n")
    (tmp_path / "empty").mkdir()
    tessercheck = component.Tessercheck(component.Config(component.Spec()))
    try:
        inspect_tree_response = tessercheck.client.inspect_tree(client.InspectTreeRequest(tree=str(tmp_path)))
    finally:
        tessercheck.close()
    assert inspect_tree_response.contexts == ("reports",)
    assert inspect_tree_response.unclassified == ("empty",)
    assert [(source.path, source.reached_contexts, source.client_calls, source.top_level_calls)
            for source in inspect_tree_response.sources] == [
        ("reports/client/__init__.py", (), (), ()),
        ("srv/main.py", ("reports",), (3,), ()),
    ]


def test_the_public_inspection_refuses_an_unreadable_directory(tmp_path: pathlib.Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0)
    tessercheck = component.Tessercheck(component.Config(component.Spec()))
    try:
        with pytest.raises(client.TreeNotInspected) as raised:
            tessercheck.client.inspect_tree(client.InspectTreeRequest(tree=str(tmp_path)))
        assert raised.value.code == "inspection_unreadable"
        assert "locked" in raised.value.message
    finally:
        locked.chmod(0o700)
        tessercheck.close()
