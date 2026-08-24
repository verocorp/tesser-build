import ast
import inspect
import textwrap
import collections.abc as abc
import pathlib

import tessercheck.adapters.repositories.rulebook_sources as rulebook_sources
import tessercheck.adapters.repositories.source_reader as source_reader
import tessercheck.application.service as application_service
import tessercheck.client.client as client


def check_tree(root: pathlib.Path) -> tuple[str, ...]:
    declaration = root / ".tesser-root"
    if not declaration.exists():
        declaration.write_text("app\n")
    return check_raw(root)


def check_raw(root: pathlib.Path) -> tuple[str, ...]:
    service = application_service.TessercheckService(source_reader.FilesystemSourceReader(), rulebook_sources.FilesystemRulebookSources())
    return service.check(client.CheckRequest(tree=str(root))).findings


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
        "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
        "        return client.AskResponse(text=request.text)\n",
    )


def function_tree(func: abc.Callable[..., object]) -> ast.FunctionDef:
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
