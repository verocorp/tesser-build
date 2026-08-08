import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _rel in (("..", ".."), ("..", "..", "..")):
    _candidate = os.path.abspath(os.path.join(_root, *_rel, "tesser-py"))
    if os.path.isdir(_candidate):
        sys.path.insert(0, _candidate)
        break
else:
    raise RuntimeError(f"no tesser-py at ../../ or ../../../ from {_root}")

from pathlib import Path

from sigcheck.adapters.repositories import FilesystemSourceReader
from sigcheck.application.service import SigcheckService
from sigcheck.client.client import CheckRequest


def check_tree(root: Path) -> tuple[str, ...]:
    service = SigcheckService(FilesystemSourceReader())
    return service.check(CheckRequest(root=str(root))).findings


def write_module(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def conforming_tree(root: Path) -> None:
    write_module(
        root,
        "app/domain.py",
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
        "app/client.py",
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
        "app/application.py",
        "import tesser.application as ts\n"
        "import app.client as client\n"
        "class AskService(ts.ApplicationService):\n"
        "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
        "        return client.AskResponse(text=request.text)\n"
        "    def _helper(self, anything: int) -> int:\n"
        "        return anything\n",
    )
