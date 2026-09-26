from __future__ import annotations

import pytest
import tesser.testing as ts
import tesser.errors as errors

import tessercheck.domain as domain


@ts.helper
def tree_inspection_spec(
    sources: tuple[tuple[str, str | None], ...] = (),
    directories: tuple[str, ...] = (),
    declared: bool = True,
    unreadable_directories: tuple[str, ...] = (),
) -> domain.TreeInspectionSpec:
    return domain.TreeInspectionSpec(
        sources=sources,
        directories=directories,
        declared=declared,
        unreadable_directories=unreadable_directories,
    )


@pytest.mark.parametrize(
    ("sources", "directories", "contexts", "unclassified"),
    [
        ((("billing/__init__.py", ""),), ("billing",), (), ("billing",)),
        (
            (("billing/client.py", "class Client: pass\n"),),
            ("billing",),
            ("billing",),
            (),
        ),
        (
            (("billing/client.py", "class SomethingElse: pass\n"),),
            ("billing",),
            (),
            ("billing",),
        ),
        (
            (("billing/client/__init__.py", "from client.iface import Client\n"),),
            ("billing", "billing/client"),
            ("billing",),
            (),
        ),
        (
            (("billing/client.py", "class BillingClient: pass\n"),),
            ("billing", "web", "web/admin", "web/ops", "app", "tests", ".hidden"),
            ("billing",),
            (),
        ),
        ((), ("empty",), (), ("empty",)),
    ],
)
def test_inventory_classifies_clients_and_keeps_clientless_directories_visible(
    sources: tuple[tuple[str, str | None], ...],
    directories: tuple[str, ...],
    contexts: tuple[str, ...],
    unclassified: tuple[str, ...],
) -> None:
    tree_inspection = domain.TreeInspection(
        tree_inspection_spec(sources=sources, directories=directories)
    )
    assert tuple(tree_inspection.contexts()) == contexts
    assert tuple(tree_inspection.unclassified()) == unclassified
    assert tuple(tree_inspection.directories()) == tuple(sorted(set(directories)))


@pytest.mark.parametrize(
    ("source", "reached", "called"),
    [
        (
            "def f(app):\n    return app.reports.links_by_verdict()\n",
            ("reports",),
            (2,),
        ),
        (
            "def f(app):\n    reports = app.reports\n    return reports.links_by_verdict()\n",
            ("reports",),
            (3,),
        ),
        ("def f(app):\n    return ReportsHandler(app.reports)\n", ("reports",), ()),
        ("def f(cfg):\n    return cfg.reports\n", (), ()),
        ("def f(config):\n    return config.reports\n", (), ()),
        (
            "reports = app.reports\nreports = unrelated\nreports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\nreports = reports.fetch()\nreports.fetch()\n",
            ("reports",),
            (2,),
        ),
        ("reports = app.reports\ndel reports\nreports.fetch()\n", ("reports",), ()),
        ("reports = app.reports\nother = reports\nother.fetch()\n", ("reports",), (3,)),
        (
            "def first(app):\n    reports = app.reports\ndef second():\n    reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\ndef f(reports):\n    reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\ndef f():\n    reports.fetch()\n    reports = unrelated\n",
            ("reports",),
            (),
        ),
        (
            "def outer(app):\n    reports = app.reports\n    def inner():\n        reports.fetch()\n",
            ("reports",),
            (4,),
        ),
        (
            "def outer(app):\n    reports = app.reports\n    def inner():\n        reports = unrelated\n"
            "        reports.fetch()\n    reports.fetch()\n",
            ("reports",),
            (6,),
        ),
        (
            "class C:\n    reports = app.reports\n    def f(self):\n        reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\nfrom elsewhere import reports\nreports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\nfor reports in others:\n    reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\nwith unrelated() as reports:\n    reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\n[reports.fetch() for reports in items]\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\ndef f():\n    [reports for reports in items]\n    reports.fetch()\n",
            ("reports",),
            (4,),
        ),
        (
            "def f(app):\n    reports = app.reports\n    def inner():\n        nonlocal reports\n"
            "        reports.fetch()\n        reports = unrelated\n",
            ("reports",),
            (5,),
        ),
        (
            "reports = app.reports\ndef f():\n    global reports\n    reports.fetch()\n    reports = unrelated\n",
            ("reports",),
            (4,),
        ),
        (
            "reports = app.reports\n[reports.fetch() for other in reports.fetch()]\n",
            ("reports",),
            (2,),
        ),
        (
            "reports = app.reports\ntry:\n    work()\nexcept Exception as reports:\n    reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\ndef f():\n    reports.fetch()\n    try:\n        work()\n"
            "    except Exception as reports:\n        pass\n",
            ("reports",),
            (),
        ),
        (
            "reports = app.reports\nmatch item:\n    case {'value': reports}:\n        reports.fetch()\n",
            ("reports",),
            (),
        ),
        (
            "class C:\n    reports = app.reports\n    values = [reports.fetch() for item in items]\n",
            ("reports",),
            (),
        ),
    ],
)
def test_host_access_reports_direct_and_lexically_scoped_alias_calls(
    source: str, reached: tuple[str, ...], called: tuple[int, ...]
) -> None:
    tree_inspection = domain.TreeInspection(
        tree_inspection_spec(
            sources=(
                ("reports/client.py", "class ReportsClient: pass\n"),
                ("srv/main.py", source),
            ),
            directories=("reports", "srv"),
        )
    )
    module_inspection = tree_inspection.modules()[1]
    assert str(module_inspection.path()) == "srv/main.py"
    assert tuple(module_inspection.reached()) == reached
    assert tuple(module_inspection.calls()) == called


@pytest.mark.parametrize(
    ("source", "lines"),
    [
        ("configure_logging()\n", (1,)),
        ("x = configure_logging()\n", ()),
        ("def f():\n    configure_logging()\n", ()),
        ("@configure_logging()\ndef f(): pass\n", ()),
        ("class C:\n    configure_logging()\n", ()),
    ],
)
def test_top_level_expression_calls_are_not_a_claim_to_detect_all_import_effects(
    source: str, lines: tuple[int, ...]
) -> None:
    tree_inspection = domain.TreeInspection(
        tree_inspection_spec(sources=(("module.py", source),))
    )
    assert tuple(tree_inspection.modules()[0].top_level_calls()) == lines


@pytest.mark.parametrize(
    ("source", "exported"),
    [
        ("from a import Config as Config\n", ("Config",)),
        ("from a import Config\n", ()),
        ('example = "Config as Config"\n', ()),
        ("from a import Other as Config\n", ()),
    ],
)
def test_config_export_facts_report_the_explicit_export_not_incidental_text(
    source: str, exported: tuple[str, ...]
) -> None:
    tree_inspection = domain.TreeInspection(
        tree_inspection_spec(sources=(("shop/component/__init__.py", source),))
    )
    assert tuple(tree_inspection.modules()[0].exports()) == exported


@pytest.mark.parametrize(
    ("sources", "declared", "code"),
    [
        ((("broken.py", "class"),), True, "inspection_syntax"),
        ((("unreadable.py", None),), True, "inspection_unreadable"),
        ((), False, "inspection_undeclared"),
    ],
)
def test_incomplete_inputs_are_refused_instead_of_reporting_an_empty_success(
    sources: tuple[tuple[str, str | None], ...], declared: bool, code: str
) -> None:
    with pytest.raises(errors.DomainError) as raised:
        domain.TreeInspection(tree_inspection_spec(sources=sources, declared=declared))
    assert raised.value.code == code


def test_tree_inspection_equality_covers_inventory_and_module_facts() -> None:
    tree_inspection = domain.TreeInspection(
        tree_inspection_spec(
            sources=(
                ("reports/client.py", "class ReportsClient: pass\n"),
                ("srv/main.py", "app.reports.fetch()\n"),
            ),
            directories=("reports", "srv"),
        )
    )
    assert tree_inspection == domain.TreeInspection(
        tree_inspection_spec(
            sources=(
                ("srv/main.py", "app.reports.fetch()\n"),
                ("reports/client.py", "class ReportsClient: pass\n"),
            ),
            directories=("srv", "reports"),
        )
    )
    assert tree_inspection != domain.TreeInspection(
        tree_inspection_spec(
            sources=(
                ("reports/client.py", "class ReportsClient: pass\n"),
                ("srv/main.py", "app.reports\n"),
            ),
            directories=("reports", "srv"),
        )
    )
    assert tree_inspection != domain.TreeInspection(
        tree_inspection_spec(directories=("empty",))
    )


def test_module_inspection_equality_covers_access_and_top_level_calls() -> None:
    tree_inspection = domain.TreeInspection(
        tree_inspection_spec(sources=(("module.py", "call()\n"),))
    )
    assert (
        tree_inspection.modules()[0]
        == domain.TreeInspection(
            tree_inspection_spec(sources=(("module.py", "call()\n"),))
        ).modules()[0]
    )
    assert (
        tree_inspection.modules()[0]
        != domain.TreeInspection(
            tree_inspection_spec(sources=(("module.py", "value = call()\n"),))
        ).modules()[0]
    )
