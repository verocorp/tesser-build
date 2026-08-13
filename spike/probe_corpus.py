import pathlib
import subprocess
import sys
import tempfile

WORKTREE = pathlib.Path("/home/ubuntu/workspace/verocorp/tesser-build/.claude/worktrees/import-totality")

BAIT = "import app.domain.thing\nimport tesser.domain\nX = 1\n"
TEST_BAIT = "import app.domain.thing\ndef test_ok() -> None:\n    assert True\n"

# Every probe carries bait imports that are illegal from almost anywhere.
# A probe is GOVERNED if the analyzer emits at least one finding naming it.
# Shapes marked expect="silent-ok" are locations where the bait is genuinely
# legal (so silence is correct); everything else silent is a leak.
PROBES = [
    # (path, source, note)
    ("solo.py", BAIT, "root module, no ignore-file"),
    ("test_solo.py", TEST_BAIT, "root-level test module"),
    ("eval_solo.py", TEST_BAIT, "root-level eval module"),
    ("conftest_extra.py", BAIT, "root module named like a conftest cousin"),
    ("weird/util.py", BAIT, "module in undeclared package"),
    ("weird/test_x.py", TEST_BAIT, "test in undeclared package"),
    ("weird/eval_x.py", TEST_BAIT, "eval in undeclared package"),
    ("weird/conftest.py", BAIT, "conftest in undeclared package"),
    ("weird/__main__.py", BAIT, "__main__ in undeclared package"),
    ("weird/deep/nested.py", BAIT, "deep module in undeclared package"),
    ("tests/util.py", BAIT, "helper in root tests package"),
    ("tests/sub/test_deep.py", TEST_BAIT, "test nested below root tests"),
    ("tests/__main__.py", BAIT, "__main__ in root tests package"),
    ("tests/eval_x.py", TEST_BAIT, "eval in root tests package"),
    ("srv/__main__.py", BAIT, "__main__ in srv"),
    ("srv/conftest.py", BAIT, "conftest in srv"),
    ("srv/deep/handler.py", BAIT, "deep srv module"),
    ("bootstrap/__main__.py", BAIT, "__main__ in bootstrap"),
    ("protocol/__main__.py", BAIT, "__main__ in protocol"),
    ("protocol/conftest.py", BAIT, "conftest in protocol"),
    ("app/__main__.py", "import app.domain.thing\n", "context __main__ importing domain"),
    ("app/domain/__main__.py", "import app.application.service\n", "role-depth __main__"),
    ("app/adapters/gateways/__main__.py", "import app.domain.thing\n", "kind-depth __main__"),
    ("app/tests/__main__.py", BAIT, "context-tests __main__"),
    ("app/conftest.py", BAIT, "context-root conftest"),
    ("app/adapters/conftest.py", BAIT, "role-depth conftest"),
    ("app/test_direct.py", TEST_BAIT, "test at context root"),
    ("app/domain/sub/deep.py", "import app.application.service\n", "module nested below a role module dir"),
    ("app/stray.py", BAIT, "non-role module in a context"),
    ("app/stray_pkg/mod.py", BAIT, "non-role package in a context"),
    ("app/domain/eval_bad.py", TEST_BAIT, "eval in domain"),
    ("tests.py", BAIT, "MODULE named tests at root"),
    ("srv.py", BAIT, "MODULE named srv at root"),
    ("app/tests.py", "import app.application.service\n", "MODULE named tests in a context"),
    ("bench_root.py", BAIT, "FUTURE: root benchmark module"),
    ("app/domain/bench_thing.py", "import app.application.service\nX = 1\n", "FUTURE: benchmark in domain"),
    ("tests/bench_deep.py", BAIT, "FUTURE: benchmark in root tests"),
]


def build_tree(root: pathlib.Path) -> None:
    (root / "app/domain").mkdir(parents=True)
    (root / "app/client").mkdir(parents=True)
    (root / "app/application").mkdir(parents=True)
    for init in ("app", "app/domain", "app/client", "app/application"):
        (root / init / "__init__.py").write_text("")
    (root / "app/domain/thing.py").write_text(
        "import tesser.domain as ts\n"
        "class ThingSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Thing(ts.AggregateRoot):\n"
        "    def __init__(self, spec: ThingSpec) -> None:\n"
        "        self.text = spec.text\n"
    )
    (root / "app/client/client.py").write_text(
        "import tesser.context as ts\n"
        "class AskRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
    )
    (root / "app/application/service.py").write_text(
        "import tesser.application as ts\n"
        "import app.client.client as client\n"
        "class AskService(ts.ApplicationService):\n"
        "    def ask(self, request: client.AskRequest) -> client.AskRequest:\n"
        "        return request\n"
    )


def main() -> None:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="totality-probe-"))
    build_tree(tmp)
    module_names = []
    for rel, source, note in PROBES:
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        for parent in path.relative_to(tmp).parents:
            if str(parent) not in (".", "") and parent.name in ("sub", "deep", "stray_pkg", "tests", "weird"):
                init = tmp / parent / "__init__.py"
                if not init.exists() and (tmp / parent).is_dir():
                    init.write_text("")
        path.write_text(source)
        module_names.append((rel[:-3].replace("/", "."), rel, note))
    proc = subprocess.run(
        [sys.executable, "-m", "tessercheck", str(tmp)],
        capture_output=True,
        text=True,
        cwd=str(WORKTREE / "tessercheck-py"),
        env={"PYTHONPATH": f"{WORKTREE}/tessercheck-py:{WORKTREE}/tesser-py", "PATH": "/usr/bin:/bin"},
    )
    findings = proc.stdout.splitlines()
    silent = []
    governed = 0
    for name, rel, note in module_names:
        hits = [f for f in findings if f" {name} " in f or f.startswith(rel + ":")]
        if hits:
            governed += 1
        else:
            silent.append((rel, note))
    print(f"governed: {governed}/{len(module_names)}   findings total: {len(findings)}")
    for rel, note in silent:
        print(f"  SILENT: {rel}  ({note})")


if __name__ == "__main__":
    main()
