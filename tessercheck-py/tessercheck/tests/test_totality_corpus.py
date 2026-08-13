from pathlib import Path

import tessercheck.tests.conftest as conftest

BAIT = "import app.domain.thing\nimport tesser.domain\nX = 1\n"

TEST_BAIT = "import app.domain.thing\ndef test_ok() -> None:\n    assert True\n"

CORPUS = (
    ("solo.py", BAIT),
    ("test_solo.py", TEST_BAIT),
    ("eval_solo.py", TEST_BAIT),
    ("weird/util.py", BAIT),
    ("weird/test_x.py", TEST_BAIT),
    ("weird/eval_x.py", TEST_BAIT),
    ("weird/conftest.py", BAIT),
    ("weird/__main__.py", BAIT),
    ("weird/deep/nested.py", BAIT),
    ("tests/util.py", BAIT),
    ("tests/sub/test_deep.py", TEST_BAIT),
    ("tests/__main__.py", BAIT),
    ("tests/eval_x.py", TEST_BAIT),
    ("srv/__main__.py", BAIT),
    ("srv/conftest.py", BAIT),
    ("srv/deep/handler.py", BAIT),
    ("bootstrap/__main__.py", BAIT),
    ("protocol/__main__.py", BAIT),
    ("protocol/conftest.py", BAIT),
    ("app/__main__.py", "import app.domain.thing\n"),
    ("app/domain/__main__.py", "import app.application.service\n"),
    ("app/adapters/gateways/__main__.py", "import app.domain.thing\n"),
    ("app/tests/__main__.py", BAIT),
    ("app/conftest.py", BAIT),
    ("app/adapters/conftest.py", BAIT),
    ("app/test_direct.py", TEST_BAIT),
    ("app/domain/sub/deep.py", "import app.application.service\n"),
    ("app/stray.py", BAIT),
    ("app/stray_pkg/mod.py", BAIT),
    ("app/domain/eval_bad.py", TEST_BAIT),
    ("tests.py", BAIT),
    ("srv.py", BAIT),
    ("app/tests.py", "import app.application.service\n"),
)


def test_no_module_shape_is_silent(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    names = []
    for rel, source in CORPUS:
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
