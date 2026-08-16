from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks


@ts.helper
def _spec(
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
    exports: tuple[str, ...] = ("tesser",),
    base: tuple[tuple[str, str, str | None, bool], ...] = (
        ("tesser/__init__.py", "tesser", "", True),
        ("tesser/domain/__init__.py", "tesser.domain", "", True),
        (
            "tesser/domain/valueobject.py",
            "tesser.domain.valueobject",
            "class ValueObject:\n"
            "    def __eq__(self, other: object) -> bool:\n"
            "        return self.__dict__ == other.__dict__\n",
            False,
        ),
    ),
) -> checks.CodebaseSpec:
    return checks.CodebaseSpec(
        sources=base + sources,
        declared="app",
        nested=(),
        symlinked=(),
        exports=exports,
    )


def test_the_shells_tree_is_clean_and_not_context_shaped() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec()).violations()
    )
    assert findings == (), findings


def test_a_tesser_init_only_reexports_from_the_distribution() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "tesser/testing/__init__.py",
                    "tesser.testing",
                    "from tesser.declared import fake as fake\n"
                    "from . import declared as declared\n"
                    "import subprocess\n"
                    "X = 1\n",
                    True,
                ),
                ("tesser/declared.py", "tesser.declared", "", False),
            ),
        )).violations()
    )
    assert any(
        "tesser.testing imports subprocess; "
        "a tesser __init__ only re-exports from the distribution" in f
        for f in findings
    ), findings
    assert any(
        "tesser.testing __init__ declares code; "
        "a tesser __init__ only re-exports from the distribution" in f
        for f in findings
    ), findings
    assert not any("imports tesser.declared" in f for f in findings), findings
    assert not any("tesser.testing.declared" in f for f in findings), findings


def test_the_distribution_holds_only_consumer_namespaces() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(("tesser/extras.py", "tesser.extras", "X = 1\n", False),),
        )).violations()
    )
    assert any(
        "tesser.extras is not a consumer namespace; the tesser "
        "distribution holds only the namespaces its consumers import" in f
        for f in findings
    ), findings


def test_a_shell_module_stays_on_the_shell_stdlib() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "tesser/srv/host.py",
                    "tesser.srv.host",
                    "import subprocess\n"
                    "from typing import Protocol\n"
                    "from tesser.domain.valueobject import ValueObject\n"
                    "class Host(Protocol):\n"
                    "    ...\n",
                    False,
                ),
                ("tesser/srv/__init__.py", "tesser.srv", "", True),
            ),
        )).violations()
    )
    assert any(
        "tesser.srv.host imports subprocess; a shell module imports "
        "only the tesser distribution and the shell stdlib" in f
        for f in findings
    ), findings
    assert not any("imports typing" in f for f in findings), findings
    assert not any("imports tesser.domain" in f for f in findings), findings


def test_the_shells_tests_probe_freely_with_any_tesser_import() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "tests/test_shells.py",
                    "tests.test_shells",
                    "import tesser.adapters\n"
                    "import tesser.domain\n"
                    "class Probe(tesser.domain.ValueObject):\n"
                    "    pass\n"
                    "def test_probe() -> None:\n"
                    "    assert Probe() == Probe()\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert findings == (), findings


def test_the_shells_tests_keep_function_totality() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "tests/test_shells.py",
                    "tests.test_shells",
                    "import tesser.domain\n"
                    "def helper() -> int:\n"
                    "    return 1\n"
                    "print('loose')\n"
                    "def test_ok() -> None:\n"
                    "    assert True\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "is neither a test nor a declared helper; a test module holds "
        "tests, @ts.helper builders, and @ts.fake doubles" in f
        for f in findings
    ), findings
    assert any(
        "a test module holds only imports, tests, helpers, and fakes" in f
        for f in findings
    ), findings


def test_a_tree_exporting_tesser_holds_nothing_else() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "billing/domain/money.py",
                    "billing.domain.money",
                    "import tesser.domain as ts\n"
                    "class MoneySpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "a tree exporting tesser is the distribution itself — "
        "its top level is tesser and tests, nothing else" in f
        for f in findings
    ), findings


def test_a_stray_subpackage_in_the_distribution_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "tesser/evil/__init__.py",
                    "tesser.evil",
                    "from tesser.domain.valueobject import ValueObject as ValueObject\n",
                    True,
                ),
            ),
        )).violations()
    )
    assert any(
        "tesser.evil is not a consumer namespace; the tesser "
        "distribution holds only the namespaces its consumers import" in f
        for f in findings
    ), findings


def test_a_conftest_leaf_counts_tesser_edges_in_the_exporting_tree() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "conftest.py",
                    "conftest",
                    "import tesser.domain.valueobject\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "conftest imports tesser.domain.valueobject; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    ), findings
