from pathlib import Path

from sigcheck.adapters import FilesystemSourceReader
from sigcheck.application import SigcheckService
from sigcheck.client import CheckRequest


def _check(root: Path) -> tuple[str, ...]:
    service = SigcheckService(FilesystemSourceReader())
    return service.check(CheckRequest(root=str(root))).findings


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def _conforming(root: Path) -> None:
    _write(
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
    assert _check(tmp_path) == ()


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
    findings = _check(tmp_path)
    assert any("parameter 'text' is not a ts.Request; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("does not return a ts.Response; a service method returns a ts.Response" in f for f in findings)


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
    findings = _check(tmp_path)
    assert any("takes 2 parameters; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("parameter 'request' is not a ts.Request; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("uses *args/**kwargs; a service method takes exactly one ts.Request" in f for f in findings)


def test_aggregate_constructor_violations_are_flagged(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/badroots.py",
        "import tesser.domain as ts\n"
        "from app.domain import ThingSpec\n"
        "class Primitive(ts.AggregateRoot):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Two(ts.AggregateRoot):\n"
        "    def __init__(self, a: ThingSpec, b: ThingSpec) -> None:\n"
        "        self.a = a\n"
        "class NoConstructor(ts.AggregateRoot):\n"
        "    pass\n",
    )
    findings = _check(tmp_path)
    assert any(
        "Primitive.__init__" in f
        and "parameter 'text' is not a ts.Spec; an aggregate constructor takes exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "Two.__init__" in f
        and "takes 2 parameters; an aggregate constructor takes exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "NoConstructor" in f
        and "defines no __init__; an aggregate constructs from exactly one ts.Spec" in f
        for f in findings
    )


def test_service_body_rules_are_flagged(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/busy.py",
        "import tesser.application as ts\n"
        "from app.client import AskRequest, AskResponse\n"
        "class BusyService(ts.ApplicationService):\n"
        "    def long(self, request: AskRequest) -> AskResponse:\n"
        + "".join(f"        step_{i} = request.text\n" for i in range(11))
        + "        return AskResponse(text=step_0)\n"
        "    def nested(self, request: AskRequest) -> AskResponse:\n"
        "        if request.ping():\n"
        "            if request.pong():\n"
        "                return AskResponse(text='')\n"
        "        return AskResponse(text='')\n"
        "    def compares(self, request: AskRequest) -> AskResponse:\n"
        "        if request.text == 'x':\n"
        "            return AskResponse(text='')\n"
        "        return AskResponse(text='')\n"
        "    def combines(self, request: AskRequest) -> AskResponse:\n"
        "        if request.ready() and request.good():\n"
        "            return AskResponse(text='')\n"
        "        return AskResponse(text='')\n",
    )
    findings = _check(tmp_path)
    assert any(
        "BusyService.long" in f
        and "body spans 12 source lines; a service method body is at most 10 source lines" in f
        for f in findings
    )
    assert any(
        "BusyService.nested" in f
        and "nests a conditional" in f
        and "a service method branches one level deep" in f
        for f in findings
    )
    assert any(
        "BusyService.compares" in f
        and "is not a single call; a service method satisfies a condition with one domain call" in f
        for f in findings
    )
    assert any(
        "BusyService.combines" in f
        and "is not a single call; a service method satisfies a condition with one domain call" in f
        for f in findings
    )


def test_service_delegation_is_flagged(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/helped.py",
        "import tesser.application as ts\n"
        "from app.client import AskRequest, AskResponse\n"
        "def shape(text: str) -> str:\n"
        "    return text\n"
        "class HelpedService(ts.ApplicationService):\n"
        "    def ask(self, request: AskRequest) -> AskResponse:\n"
        "        return self._prep(request)\n"
        "    def _prep(self, request: AskRequest) -> AskResponse:\n"
        "        return AskResponse(text=shape(request.text))\n",
    )
    findings = _check(tmp_path)
    assert any(
        "HelpedService.ask" in f
        and "delegates to self._prep" in f
        and "a service inlines its logic" in f
        for f in findings
    )
    assert any(
        "HelpedService._prep" in f
        and "delegates to shape" in f
        and "a service inlines its logic" in f
        for f in findings
    )


def test_elif_chain_is_one_level(tmp_path: Path) -> None:
    _conforming(tmp_path)
    _write(
        tmp_path,
        "app/chained.py",
        "import tesser.application as ts\n"
        "from app.client import AskRequest, AskResponse\n"
        "class ChainService(ts.ApplicationService):\n"
        "    def pick(self, request: AskRequest) -> AskResponse:\n"
        "        if request.ready():\n"
        "            return AskResponse(text='a')\n"
        "        elif request.good():\n"
        "            return AskResponse(text='b')\n"
        "        return AskResponse(text='c')\n",
    )
    findings = _check(tmp_path)
    assert not any("ChainService" in f and "a service method branches one level deep" in f for f in findings)


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
    findings = _check(tmp_path)
    assert any(
        "DerivedService.again" in f
        and "does not return a ts.Response; a service method returns a ts.Response" in f
        for f in findings
    )
