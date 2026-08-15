from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks

@ts.helper
def _conforming() -> tuple[tuple[str, str, str, bool], ...]:  # tessercheck:ignore TB073
    return (
        (
            "app/domain/thing.py",
            "app.domain.thing",
            "import tesser.domain as ts\n"
            "class ThingSpec(ts.Spec):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class Thing(ts.AggregateRoot):\n"
            "    def __init__(self, spec: ThingSpec) -> None:\n"
            "        self.text = spec.text\n",
            False,
        ),
        (
            "app/client/client.py",
            "app.client.client",
            "import tesser.context as ts\n"
            "class AskRequest(ts.Request):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class AskResponse(ts.Response):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n",
            False,
        ),
        (
            "app/application/service.py",
            "app.application.service",
            "import tesser.application as ts\n"
            "import app.client.client as client\n"
            "class AskService(ts.ApplicationService):\n"
            "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
            "        return client.AskResponse(text=request.text)\n"
            "    def _helper(self, anything: int) -> int:\n"
            "        return anything\n",
            False,
        ),
    )


@ts.helper
def _findings(  # tessercheck:ignore TB073
    sources: tuple[tuple[str, str, str, bool], ...] = (),
    conforming: bool = True,
) -> tuple[str, ...]:
    spec = checks.CodebaseSpec(
        sources=(_conforming() + sources) if conforming else sources,
        declared="app",
        nested=(),
        symlinked=(),
    )
    return tuple(
        f"{violation.path()}:{int(violation.line())}: "
        f"{violation.code()} {violation.text()}"
        for violation in checks.Codebase(spec).violations()
    )


def test_a_conforming_spec_is_clean() -> None:
    assert _findings() == ()


def test_placement_totality_is_flagged() -> None:
    findings = _findings(
        (
            (
                "plain/domain/thing.py",
                "plain.domain.thing",
                "import tesser.domain as ts\n"
                "import tesser.context as tc\n"
                "class Loose:\n"
                "    pass\n"
                "class Ask(tc.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "def stray() -> None:\n"
                "    return None\n"
                "LIMIT = 3\n"
                "print('hi')\n",
                False,
            ),
        )
    )
    assert any(
        "plain.domain.thing.Loose" in f
        and "every context class declares its block" in f
        for f in findings
    )
    assert any(
        "plain.domain.thing.Ask" in f and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "plain.domain.thing.stray" in f
        and "a module function declares itself with @ts.function" in f
        for f in findings
    )
    assert any("a module constant is Final" in f for f in findings)
    assert any(
        "a context module holds only imports, classes, declared functions, and "
        "Final constants" in f
        for f in findings
    )
    assert any(
        "imports tesser.context" in f
        and "a role module imports only its own tesser package" in f
        for f in findings
    )


def test_declared_function_and_final_constant_pass() -> None:
    findings = _findings(
        (
            ("app/domain2.py", "app.domain2", "", False),
            (
                "plain/domain/thing.py",
                "plain.domain.thing",
                "from typing import Final\n"
                "import tesser.domain as ts\n"
                "LIMIT: Final[int] = 3\n"
                "@ts.function\n"
                "def declared() -> None:\n"
                "    return None\n",
                False,
            ),
        )
    )
    assert not any("plain.domain.thing" in f for f in findings)


def test_homeless_modules_are_flagged() -> None:
    findings = _findings(
        (
            ("loose.py", "loose", "def anything() -> None:\n    return None\n", False),
            (
                "stray/util.py",
                "stray.util",
                "def anything() -> None:\n    return None\n",
                False,
            ),
        )
    )
    assert any(
        "loose belongs to no governed package; every module belongs to a context, "
        "srv, bootstrap, tests, or the protocol package" in f
        for f in findings
    )
    assert any(
        "stray.util belongs to no governed package" in f for f in findings
    )
