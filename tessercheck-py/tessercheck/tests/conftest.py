import ast
import inspect
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
    return (
        "examples/minimal",
        "examples/ports",
        "examples/errorspy",
        "examples/llmport",
        "examples/serdepy",
        "examples/asyncpg",
        "examples/durable-execution",
        "examples/python-app",
    )


def fixture_trees() -> tuple[str, ...]:
    return (
        "tessercheck-py/testdata/tb031/good_tree",
        "tessercheck-py/testdata/tb031/bad_tree",
    )


def sampled(paths: tuple[str, ...], most: int = 24) -> tuple[str, ...]:
    stride = max(1, len(paths) // most)
    return paths[::stride]


def findings_on(findings: tuple[str, ...], path: str) -> tuple[str, ...]:
    return tuple(finding for finding in findings if finding.startswith(path + ":"))
