from __future__ import annotations

from pathlib import Path

import tessercheck.client.client as client
from bootstrap.bootstrap import new
from bootstrap.config import Config


def test_the_composed_app_exposes_a_working_check_client(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    app = new(Config())
    try:
        response = app.tessercheck.check(client.CheckRequest(root=str(tmp_path)))
        assert response.findings == ()
    finally:
        app.close()


def test_the_composed_app_reports_an_undeclared_tree(tmp_path: Path) -> None:
    app = new(Config())
    try:
        response = app.tessercheck.check(client.CheckRequest(root=str(tmp_path)))
        assert any("TB044" in finding for finding in response.findings)
    finally:
        app.close()


def test_the_composed_app_renders_a_rulebook_for_its_own_tree() -> None:
    root = Path(__file__).resolve().parents[1]
    app = new(Config())
    try:
        response = app.tessercheck.rulebook(client.RulebookRequest(root=str(root)))
        assert response.rendered.startswith("# Rules implemented in the spike")
    finally:
        app.close()


def test_closing_the_app_twice_is_harmless() -> None:
    app = new(Config())
    app.close()
    app.close()


def test_each_composition_hands_back_its_own_app() -> None:
    first = new(Config())
    second = new(Config())
    try:
        assert first is not second
        assert first.tessercheck is not second.tessercheck
    finally:
        first.close()
        second.close()
