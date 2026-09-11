import ast
import inspect
import json
import textwrap
import collections.abc as abc
import pathlib

import tessercheck.adapters.repositories as repositories
import tessercheck.application as application
import tessercheck.application.ports as ports
import tessercheck.client as client


def check_tree(root: pathlib.Path) -> tuple[str, ...]:
    declaration = root / ".tesser-root"
    if not declaration.exists():
        declaration.write_text("app\n")
    return check_raw(root)


def check_raw(root: pathlib.Path) -> tuple[str, ...]:
    tessercheck_service = application.TessercheckService(repositories.FilesystemSourceReader(), repositories.FilesystemSourceWriter(), repositories.FilesystemRulebookSources())
    return tessercheck_service.check(client.CheckRequest(tree=str(root))).findings


def write_module(root: pathlib.Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def conforming_tree(root: pathlib.Path) -> None:
    write_module(
        root,
        "shop/domain/thing.py",
        "import tesser.domain as ts\n"
        "class ThingSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Thing(ts.AggregateRoot):\n"
        "    def __init__(self, spec: ThingSpec) -> None:\n"
        "        self.text = spec.text\n",
    )
    write_module(
        root,
        "shop/domain/test_thing.py",
        "def test_thing_exists() -> None:\n"
        "    assert True\n",
    )
    write_module(
        root,
        "shop/application/test_service.py",
        "def test_service_exists() -> None:\n"
        "    assert True\n",
    )
    write_module(
        root,
        "shop/client/client.py",
        "import tesser.context as ts\n"
        "class AskRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class AskResponse(ts.Response):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        root,
        "shop/application/service.py",
        "import tesser.application as ts\n"
        "import shop.client.client as client\n"
        "class AskService(ts.ApplicationService):\n"
        "    def ask(self, ask_request: client.AskRequest) -> client.AskResponse:\n"
        "        return client.AskResponse(text=ask_request.text)\n",
    )


def function_tree(func: abc.Callable[..., object]) -> ast.FunctionDef:  # tesser:debt TB022
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    return node


def returned_tokens(func: ast.FunctionDef) -> frozenset[str]:
    return frozenset(
        value.value
        for node in ast.walk(func)
        if isinstance(node, ast.Return) and node.value is not None
        for value in ast.walk(node.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


def check_file_raw(root: pathlib.Path, path: str) -> client.CheckFileResponse:
    tessercheck_service = application.TessercheckService(repositories.FilesystemSourceReader(), repositories.FilesystemSourceWriter(), repositories.FilesystemRulebookSources())
    return tessercheck_service.check_file(client.CheckFileRequest(tree=str(root), path=path))


def governed_paths(root: pathlib.Path) -> tuple[str, ...]:
    read_sources_response = repositories.FilesystemSourceReader().sources(
        ports.ReadSourcesRequest(tree=str(root))
    )
    return tuple(source.path for source in read_sources_response.sources)


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def example_trees() -> tuple[str, ...]:
    manifest = json.loads((repo_root() / "manifest.json").read_text(encoding="utf-8"))
    return tuple(
        sorted(tree for tree, kind in manifest.items() if kind == "app" and tree.startswith("examples/"))
    )


def fixture_trees() -> tuple[str, ...]:
    return (
        "tessercheck-py/testdata/tb031/good_tree",
        "tessercheck-py/testdata/tb031/bad_tree",
    )


def bounded_rebuilds(paths: tuple[str, ...], must: tuple[str, ...] = (), most: int = 16) -> tuple[str, ...]:
    stride = max(1, len(paths) // most)
    chosen = dict.fromkeys(must)
    for path in paths[::stride]:
        chosen[path] = None
    return tuple(chosen)


def findings_on(findings: tuple[str, ...], path: str) -> tuple[str, ...]:
    return tuple(finding for finding in findings if finding.startswith(path + ":"))


def inject_findings(root: pathlib.Path) -> tuple[str, ...]:
    paths = governed_paths(root)
    module = next(
        path for path in paths
        if not path.endswith("__init__.py")
        and not path.rsplit("/", 1)[-1].startswith("test_")
        and not path.endswith("conftest.py")
    )
    target = root / module
    target.write_text(target.read_text(encoding="utf-8") + "\n# a comment\nf = lambda x: x\n", encoding="utf-8")
    sibling = target.parent / ("test_" + target.name)
    if sibling.exists():
        sibling.unlink()
    test_module = next((path for path in paths if path.rsplit("/", 1)[-1].startswith("test_") and path != str(sibling.relative_to(root))), None)
    touched = [module]
    if test_module is not None:
        stray = root / test_module
        stray.write_text("import os\n" + stray.read_text(encoding="utf-8"), encoding="utf-8")
        touched.append(test_module)
    return tuple(touched)
