from pathlib import Path

import tessercheck.tests.conftest as conftest


def test_no_module_shape_is_silent(tmp_path: Path) -> None:
    bait = "import app.domain.thing\nimport tesser.domain\nX = 1\n"
    test_bait = "import app.domain.thing\ndef test_ok() -> None:\n    assert True\n"
    corpus = (
        ("solo.py", bait),
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
        ("bootstrap/__main__.py", bait),
        ("protocol/__main__.py", bait),
        ("protocol/conftest.py", bait),
        ("app/__main__.py", "import app.domain.thing\n"),
        ("app/domain/__main__.py", "import app.application.service\n"),
        ("app/adapters/gateways/__main__.py", "import app.domain.thing\n"),
        ("app/tests/__main__.py", bait),
        ("app/conftest.py", bait),
        ("app/adapters/conftest.py", bait),
        ("app/test_direct.py", test_bait),
        ("app/domain/sub/deep.py", "import app.application.service\n"),
        ("app/stray.py", bait),
        ("app/stray_pkg/mod.py", bait),
        ("app/domain/eval_bad.py", test_bait),
        ("tests.py", bait),
        ("srv.py", bait),
        ("app/tests.py", "import app.application.service\n"),
    )
    conftest.conforming_tree(tmp_path)
    names = []
    for rel, source in corpus:
        conftest.write_module(tmp_path, rel, source)
        names.append((rel, rel[:-3].replace("/", ".")))
    findings = conftest.check_tree(tmp_path)
    silent = [
        rel
        for rel, name in names
        if not any(f" {name} " in f or f.startswith(rel + ":") for f in findings)
    ]
    assert silent == [], (
        "these module shapes produced zero findings despite carrying an illegal "
        f"import — a location the walk does not govern: {silent}"
    )
