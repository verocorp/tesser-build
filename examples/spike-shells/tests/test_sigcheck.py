from pathlib import Path

from sigcheck import check


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def _conforming(root: Path) -> None:
    _write(
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
    _write(
        root,
        "app/application.py",
        "import tesser.application as ts\n"
        "from app.client import AskRequest, AskResponse\n"
        "class AskService(ts.ApplicationService):\n"
        "    def ask(self, request: AskRequest) -> AskResponse:\n"
        "        return AskResponse(text=request.text)\n"
        "    def _helper(self, anything: int) -> int:\n"
        "        return anything\n",
    )


def test_conforming_tree_is_clean(tmp_path: Path) -> None:
    _conforming(tmp_path)
    assert check(tmp_path) == []


def test_primitive_parameter_and_return_are_flagged(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/bad.py",
        "import tesser.application as ts\n"
        "class BadService(ts.ApplicationService):\n"
        "    def ask(self, text: str) -> str:\n"
        "        return text\n",
    )
    findings = check(tmp_path)
    assert any("parameter 'text' is not a ts.Request" in f for f in findings)
    assert any("does not return a ts.Response" in f for f in findings)


def test_arity_and_missing_annotations_are_flagged(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/bad.py",
        "import tesser.application as ts\n"
        "from app.client import AskRequest, AskResponse\n"
        "class BadService(ts.ApplicationService):\n"
        "    def two(self, a: AskRequest, b: AskRequest) -> AskResponse:\n"
        "        return AskResponse(text='')\n"
        "    def bare(self, request) -> AskResponse:\n"
        "        return AskResponse(text='')\n"
        "    def spread(self, *args: object) -> AskResponse:\n"
        "        return AskResponse(text='')\n",
    )
    findings = check(tmp_path)
    assert any("takes 2 parameters" in f for f in findings)
    assert any("parameter 'request' is not a ts.Request" in f for f in findings)
    assert any("uses *args/**kwargs" in f for f in findings)


def test_indirect_subclass_still_classifies(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/derived.py",
        "from app.application import AskService\n"
        "from app.client import AskRequest\n"
        "class DerivedService(AskService):\n"
        "    def again(self, request: AskRequest) -> AskRequest:\n"
        "        return request\n",
    )
    findings = check(tmp_path)
    assert any("DerivedService.again" in f and "does not return a ts.Response" in f for f in findings)
