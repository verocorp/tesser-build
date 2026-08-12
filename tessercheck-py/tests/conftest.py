from pathlib import Path

from tessercheck.adapters.repositories import FilesystemSourceReader
from tessercheck.application.service import TessercheckService
from tessercheck.client.client import CheckRequest


def check_tree(root: Path) -> tuple[str, ...]:
    service = TessercheckService(FilesystemSourceReader())
    return service.check(CheckRequest(root=str(root))).findings


def write_module(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def conforming_tree(root: Path) -> None:
    write_module(
        root,
        "app/domain/thing.py",
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
        "app/client/client.py",
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
        "app/application/service.py",
        "import tesser.application as ts\n"
        "import app.client.client as client\n"
        "class AskService(ts.ApplicationService):\n"
        "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
        "        return client.AskResponse(text=request.text)\n"
        "    def _helper(self, anything: int) -> int:\n"
        "        return anything\n",
    )
