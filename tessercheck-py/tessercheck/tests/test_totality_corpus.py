import pathlib

import tessercheck.domain.checks as checks
import tessercheck.tests.conftest as conftest


def test_no_module_shape_is_silent(tmp_path: pathlib.Path) -> None:
    bait = "import shop.domain.thing\nimport tesser.domain\nX = 1\n"
    test_bait = "import shop.domain.thing\ndef test_ok() -> None:\n    assert True\n"
    corpus = (
        ("solo.py", bait),
        ("conftest.py", bait),
        ("test_solo.py", test_bait),
        ("eval_solo.py", test_bait),
        ("weird/util.py", bait),
        ("weird/test_x.py", test_bait),
        ("weird/eval_x.py", test_bait),
        ("weird/conftest.py", bait),
        ("weird/__main__.py", bait),
        ("weird/deep/nested.py", bait),
        ("tests/util.py", bait),
        ("tests/sub/test_deep.py", test_bait),
        ("tests/__main__.py", bait),
        ("tests/eval_x.py", test_bait),
        ("srv/__main__.py", bait),
        ("srv/conftest.py", bait),
        ("srv/deep/handler.py", bait),
        ("app/__main__.py", bait),
        ("protocol/__main__.py", bait),
        ("protocol/conftest.py", bait),
        ("app/__main__.py", "import shop.domain.thing\n"),
        ("shop/domain/__main__.py", "import shop.application.service\n"),
        ("shop/adapters/gateways/__main__.py", "import shop.domain.thing\n"),
        ("shop/application/ports/__main__.py", "import shop.domain.thing\n"),
        ("shop/application/ports/sub/deep.py", "import shop.domain.thing\n"),
        ("shop/application/ports/test_support.py", test_bait),
        ("shop/application/client/actions.py", "import shop.domain.thing\n"),
        ("shop/application/client/__main__.py", "import shop.domain.thing\n"),
        ("shop/application/client/test_actions.py", test_bait),
        ("shop/application/client.py", "import shop.domain.thing\n"),
        ("shop/application/orchestrators/flow.py", "import shop.adapters.gateways.thing\n"),
        ("shop/application/orchestrators/__main__.py", "import shop.adapters.gateways.thing\n"),
        ("shop/application/orchestrators.py", "import shop.adapters.gateways.thing\n"),
        ("shop/tests/__main__.py", bait),
        ("app/conftest.py", bait),
        ("shop/adapters/conftest.py", bait),
        ("app/test_direct.py", test_bait),
        ("shop/domain/sub/deep.py", "import shop.application.service\n"),
        ("shop/stray.py", bait),
        ("shop/stray_pkg/mod.py", bait),
        ("shop/domain/eval_bad.py", test_bait),
        ("tests.py", bait),
        ("srv.py", bait),
        ("app.py", bait),
        ("shop.py", bait),
        ("protocol.py", bait),
        ("shop/tests.py", "import shop.application.service\n"),
        ("shop/application/ports.py", "import shop.domain.thing\n"),
        ("kernel.py", bait),
        ("kernel/money_bait.py", bait),
        ("kernel/test_money.py", test_bait),
        ("kernel/conftest.py", bait),
        ("__main__.py", bait),
        ("weird/__init__.py", bait),
        ("srv/deep/__init__.py", bait),
        ("shop/stray_pkg/__init__.py", bait),
        ("tests/test_utils/__init__.py", bait),
        ("shop/domain/eval_pkg/__init__.py", bait),
        ("shop/adapters/conftest/__init__.py", bait),
    )
    conftest.conforming_tree(tmp_path)
    for rel, source in corpus:
        conftest.write_module(tmp_path, rel, source)
    findings = conftest.check_tree(tmp_path)
    silent = [
        rel
        for rel, _ in corpus
        if not any(f.startswith(rel + ":") for f in findings)
    ]
    assert silent == [], (
        "these module shapes produced zero findings despite carrying an illegal "
        f"import — a location the walk does not govern: {silent}"
    )
    covered = frozenset(
        str(checks.Placement(checks.PlacementSpec(rel[:-3].replace("/", "."), False, ("shop",))))
        for rel, _ in corpus
        if not rel.endswith("__init__.py")
    )
    returned = conftest.returned_tokens(conftest.function_tree(checks.Placement.__init__))
    assert returned, "no placement tokens extracted from Placement.__init__; the totality below would pass on an empty set"
    package_only = frozenset(
        {
            "shell-init",
            "protocol-init",
            "role-init",
            "context-tests-init",
            "role-file",
            "ports-init",
            "kernel-init",
            "app-client-init",
            "orchestrators-init",
        }
    )
    uncovered = returned - package_only - covered
    assert uncovered == frozenset(), (
        f"Placement tokens with no corpus shape exercising them end-to-end: {sorted(uncovered)}"
    )
