from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks

@ts.helper
def _conforming() -> tuple[tuple[str, str, str | None, bool], ...]:  # tessercheck:ignore TB073
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
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
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


def test_an_ignore_suppresses_exactly_its_finding() -> None:
    findings = _findings(
        (("stray.py", "stray", "import os  # tessercheck:ignore TB040\n", False),)
    )
    assert not any("stray" in f for f in findings)


def test_a_scoped_ignore_leaves_other_codes_alone() -> None:
    findings = _findings(
        (("stray.py", "stray", "import os  # tessercheck:ignore TB050\n", False),)
    )
    assert any(
        "stray belongs to no governed package" in f and " TB040 " in f for f in findings
    )
    assert any(
        "stray.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )


def test_a_stale_ignore_is_itself_a_finding() -> None:
    findings = _findings(
        (
            (
                "app/domain/extra.py",
                "app.domain.extra",
                "import tesser.domain as ts  # tessercheck:ignore\n",
                False,
            ),
        )
    )
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )


def test_a_file_level_ignore_covers_the_whole_module() -> None:
    findings = _findings(
        (
            (
                "srv/host.py",
                "srv.host",
                "# tessercheck:ignore-file TB050\nimport os\n",
                False,
            ),
        )
    )
    assert not any("never imports tesser.srv" in f for f in findings)
    assert not any("TB090" in f and "srv/host.py" in f for f in findings)


def test_a_marker_suppresses_several_codes_space_or_comma_separated() -> None:
    findings = _findings(
        (
            ("stray.py", "stray", "import os  # tessercheck:ignore TB040 TB050\n", False),
            ("loose.py", "loose", "import os  # tessercheck:ignore TB040, TB050\n", False),
        )
    )
    assert not any("stray" in f for f in findings)
    assert not any("loose" in f for f in findings)


def test_a_file_level_ignore_requires_codes() -> None:
    findings = _findings(
        (("stray.py", "stray", "import os  # tessercheck:ignore-file\n", False),)
    )
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("stray.py:1: TB090" in f for f in findings)


def test_a_typo_or_junk_token_makes_the_marker_inert() -> None:
    findings = _findings(
        (
            ("stray.py", "stray", "import os  # tessercheck:ignored TB040\n", False),
            (
                "loose.py",
                "loose",
                "import os  # tessercheck:ignore TB040 permanent\n",
                False,
            ),
            ("bracket.py", "bracket", "import os  # tessercheck:ignore [TB040]\n", False),
        )
    )
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("loose belongs to no governed package" in f for f in findings)
    assert any("bracket belongs to no governed package" in f for f in findings)
    assert not any("stray.py" in f and "TB090" in f for f in findings)
    assert any("loose.py:1: TB090" in f for f in findings)
    assert any("bracket.py:1: TB090" in f for f in findings)


def test_a_bare_line_ignore_is_line_scoped() -> None:
    findings = _findings(
        (
            (
                "app/domain/extra.py",
                "app.domain.extra",
                "import os\nimport tesser.domain as ts  # tessercheck:ignore\n",
                False,
            ),
        )
    )
    assert any("app.domain.extra imports os" in f and " TB062 " in f for f in findings)
    assert any("app/domain/extra.py:2: TB090" in f for f in findings)


def test_tb090_itself_cannot_be_ignored() -> None:
    findings = _findings(
        (
            (
                "app/domain/extra.py",
                "app.domain.extra",
                "import tesser.domain as ts  # tessercheck:ignore-file TB090\n",
                False,
            ),
        )
    )
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )


def test_a_colliding_module_definition_is_a_finding_not_a_crash() -> None:
    findings = _findings(
        (
            ("col.py", "col", "import tesser.srv as ts\n", False),
            ("col/__init__.py", "col", "", True),
        )
    )
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert any(
        "col/__init__.py:1: TB043" in f and "a module has one definition" in f
        for f in findings
    )


def test_an_unparseable_module_is_a_finding_not_a_crash() -> None:
    findings = _findings((("broken.py", "broken", "def f(:\n", False),))
    assert any(
        "broken.py:1: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert any("app/domain/thing.py" not in f for f in findings)


def test_a_non_utf8_file_is_a_finding_not_a_crash() -> None:
    findings = _findings((("binary.py", "binary", None, False),))
    assert any(
        "binary.py:1: TB043" in f and "every checked module is readable UTF-8 Python" in f
        for f in findings
    )


def test_a_colliding_unparseable_file_reports_the_collision() -> None:
    findings = _findings(
        (
            ("col.py", "col", "def f(:\n", False),
            ("col/__init__.py", "col", "", True),
        )
    )
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert not any("every checked module parses" in f for f in findings)


def test_reader_findings_are_never_inline_suppressible() -> None:
    findings = _findings(
        (
            (
                "broken.py",
                "broken",
                "# tessercheck:ignore-file TB043\ndef f(:\n",
                False,
            ),
        )
    )
    assert any(
        "broken.py:2: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert not any("TB090" in f for f in findings)
