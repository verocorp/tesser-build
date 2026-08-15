from pathlib import Path

import pytest

import tessercheck.domain.checks as domain
import tessercheck.tests.conftest as conftest

def test_every_declared_block_has_a_name_and_a_home() -> None:
    blocks = set(domain.TESSER_BASE_BLOCKS.values())
    assert set(domain.KIND_NAME) == blocks
    assert set(domain.KIND_ROLE) == blocks - domain.SRV_KINDS

def test_every_kind_row_names_a_real_tesser_export() -> None:
    root = Path(__file__).resolve().parents[3] / "tesser-py"
    rows = list(domain.TESSER_BASE_BLOCKS) + list(domain.TESSER_DECORATORS)
    for package, name in rows:
        exports = (root / package.replace(".", "/") / "__init__.py").read_text()
        assert f" {name} as {name}" in exports

def test_conforming_tree_is_clean(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    assert conftest.check_tree(tmp_path) == ()

def test_primitive_parameter_and_return_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/bad.py",
        "import tesser.application as ts\n"
        "class BadService(ts.ApplicationService):\n"
        "    def ask(self, text: str) -> str:\n"
        "        return text\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("parameter 'text' is not a ts.Request; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("does not return a ts.Response; a service method returns a ts.Response" in f for f in findings)

def test_arity_and_missing_annotations_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/bad.py",
        "import tesser.application as ts\n"
        "from app.client.client import AskRequest, AskResponse\n"
        "class BadService(ts.ApplicationService):\n"
        "    def two(self, a: AskRequest, b: AskRequest) -> AskResponse:\n"
        "        return AskResponse(text='')\n"
        "    def bare(self, request) -> AskResponse:\n"
        "        return AskResponse(text='')\n"
        "    def spread(self, *args: object) -> AskResponse:\n"
        "        return AskResponse(text='')\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("takes 2 parameters; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("parameter 'request' is not a ts.Request; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("uses *args/**kwargs; a service method takes exactly one ts.Request" in f for f in findings)

def test_aggregate_constructor_violations_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/badroots.py",
        "import tesser.domain as ts\n"
        "from app.domain.thing import ThingSpec\n"
        "class Primitive(ts.AggregateRoot):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Two(ts.AggregateRoot):\n"
        "    def __init__(self, a: ThingSpec, b: ThingSpec) -> None:\n"
        "        self.a = a\n"
        "class NoConstructor(ts.AggregateRoot):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "Primitive.__init__" in f
        and "parameter 'text' is not a ts.Spec; a domain constructor takes exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "Two.__init__" in f
        and "takes 2 parameters; a domain constructor takes exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "NoConstructor" in f
        and "defines no __init__; an aggregate constructs from exactly one ts.Spec" in f
        for f in findings
    )

def test_service_body_rules_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/busy.py",
        "import tesser.application as ts\n"
        "from app.client.client import AskRequest, AskResponse\n"
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
    findings = conftest.check_tree(tmp_path)
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
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/helped.py",
        "import tesser.application as ts\n"
        "from app.client.client import AskRequest, AskResponse\n"
        "def shape(text: str) -> str:\n"
        "    return text\n"
        "class HelpedService(ts.ApplicationService):\n"
        "    def ask(self, request: AskRequest) -> AskResponse:\n"
        "        return self._prep(request)\n"
        "    def _prep(self, request: AskRequest) -> AskResponse:\n"
        "        return AskResponse(text=shape(request.text))\n",
    )
    findings = conftest.check_tree(tmp_path)
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
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/chained.py",
        "import tesser.application as ts\n"
        "from app.client.client import AskRequest, AskResponse\n"
        "class ChainService(ts.ApplicationService):\n"
        "    def pick(self, request: AskRequest) -> AskResponse:\n"
        "        if request.ready():\n"
        "            return AskResponse(text='a')\n"
        "        elif request.good():\n"
        "            return AskResponse(text='b')\n"
        "        return AskResponse(text='c')\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("ChainService" in f and "a service method branches one level deep" in f for f in findings)

def test_indirect_subclass_still_classifies(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/derived.py",
        "from app.application.service import AskService\n"
        "from app.client.client import AskRequest\n"
        "class DerivedService(AskService):\n"
        "    def again(self, request: AskRequest) -> AskRequest:\n"
        "        return request\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "DerivedService.again" in f
        and "does not return a ts.Response; a service method returns a ts.Response" in f
        for f in findings
    )

def test_placement_totality_is_flagged(tmp_path: Path) -> None:
    conftest.write_module(
        tmp_path,
        "plain/domain/thing.py",
        "import tesser.domain as ts\n"
        "import tesser.context as tc\n"
        "class Loose:\n"
        "    pass\n"
        "class Ask(tc.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "def stray() -> None:\n"
        "    return None\n"
        "LIMIT = 3\n"
        "print('hi')\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("plain.domain.thing.Loose" in f and "every context class declares its block" in f for f in findings)
    assert any("plain.domain.thing.Ask" in f and "a kind lives only in its role module" in f for f in findings)
    assert any("plain.domain.thing.stray" in f and "a module function declares itself with @ts.function" in f for f in findings)
    assert any("a module constant is Final" in f for f in findings)
    assert any(
        "a context module holds only imports, classes, declared functions, and Final constants" in f
        for f in findings
    )
    assert any(
        "imports tesser.context" in f and "a role module imports only its own tesser package" in f
        for f in findings
    )

def test_declared_function_and_final_constant_pass(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain2.py",
        "",
    )
    conftest.write_module(
        tmp_path,
        "plain/domain/thing.py",
        "from typing import Final\n"
        "import tesser.domain as ts\n"
        "LIMIT: Final[int] = 3\n"
        "@ts.function\n"
        "def declared() -> None:\n"
        "    return None\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("plain.domain.thing" in f and "@ts.function" in f for f in findings)
    assert not any("plain.domain.thing" in f and "a module constant is Final" in f for f in findings)

def test_non_context_module_and_nonempty_init_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/util.py", "def anything() -> None:\n    return None\n")
    conftest.write_module(tmp_path, "app/__init__.py", "X = 1\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.util" in f
        and "a context holds only domain, application, client, adapters, wiring, and tests modules" in f
        for f in findings
    )
    assert any("app" in f and "a context __init__ is empty" in f for f in findings)

def test_import_matrix_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "two/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as app_client\n"
        "class Bridge(ts.Gateway):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "two/domain/thing.py",
        "import tesser.domain as ts\n"
        "import two.client.client\n"
        "class TwoSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "two/application/service.py",
        "import tesser.application as ts\n"
        "import app.domain.thing\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "two.domain.thing" in f
        and "the same-context matrix is a role to itself, application to domain and client, adapters to application/ports, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert any(
        "two.application.service" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )
    assert not any("two.adapters.gateways" in f and "imports app.client.client" in f for f in findings)

def test_test_module_totality_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/test_junk.py",
        "import tesser.testing as th\n"
        "def build() -> None:\n"
        "    return None\n"
        "class Junk:\n"
        "    pass\n"
        "@th.fake\n"
        "class FakeNothing:\n"
        "    pass\n"
        "COUNT = 2\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "test_junk.build" in f and "a test module holds tests, @ts.helper builders, and @ts.fake doubles" in f
        for f in findings
    )
    assert any("test_junk.Junk" in f and "a test double declares itself with @ts.fake" in f for f in findings)
    assert any("test_junk.FakeNothing" in f and "a fake implements the port or client it doubles" in f for f in findings)
    assert any(
        "test_junk" in f and "a test module holds only imports, tests, helpers, and fakes" in f
        for f in findings
    )

def test_helper_rules_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/test_helpers.py",
        "import tesser.testing as th\n"
        "from app.domain.thing import Thing, ThingSpec\n"
        "@th.helper\n"
        "def bad_builder(thing: Thing, count: int) -> Thing:\n"
        "    if count:\n"
        "        return thing\n"
        "    return thing\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "bad_builder" in f and "parameter 'thing' is not a primitive; a helper takes only defaulted primitives" in f
        for f in findings
    )
    assert any(
        "bad_builder" in f and "parameter 'count' has no default; a helper takes only defaulted primitives" in f
        for f in findings
    )
    assert any("bad_builder" in f and "does not return a ts.Spec; a helper builds a spec" in f for f in findings)
    assert any("bad_builder" in f and "has control flow" in f and "a helper only constructs" in f for f in findings)

def test_service_dependencies_must_be_ports(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/extra.py",
        "import tesser.application as ts\n"
        "from app.client.client import AskRequest, AskResponse\n"
        "class NeedyService(ts.ApplicationService):\n"
        "    def __init__(self, db: str) -> None:\n"
        "        self._db = db\n"
        "    def ask(self, request: AskRequest) -> AskResponse:\n"
        "        return AskResponse(text=request.text)\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "NeedyService.__init__" in f and "parameter 'db' is not a ts.Port; a service depends only on ports" in f
        for f in findings
    )

def test_client_method_rules_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/extra2.py",
        "from typing import Protocol\n"
        "import tesser.context as tc\n"
        "class BadClient(tc.Client, Protocol):\n"
        "    def ask(self, text: str) -> str: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "BadClient.ask" in f and "parameter 'text' is not a ts.Request; a client method takes exactly one ts.Request" in f
        for f in findings
    )
    assert any(
        "BadClient.ask" in f and "does not return a ts.Response; a client method returns a ts.Response" in f
        for f in findings
    )

def test_records_never_carry_domain_objects(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/extra3.py",
        "from typing import Protocol\n"
        "import tesser.adapters as ta\n"
        "import tesser.application as tap\n"
        "from app.domain.thing import Thing\n"
        "class LoadingRepo(ta.Repository):\n"
        "    def load(self, key: str) -> Thing: ...\n"
        "class LoadingPort(tap.Port, Protocol):\n"
        "    def fetch(self) -> Thing: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "LoadingRepo.load" in f and "an adapter speaks records, never domain objects" in f
        for f in findings
    )
    assert any(
        "LoadingPort.fetch" in f and "a port speaks records, never domain objects" in f
        for f in findings
    )

def test_domain_field_rules_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/extra4.py",
        "import tesser.domain as ts\n"
        "import tesser.context as tc\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amounts: dict) -> None:\n"
        "        object.__setattr__(self, '_amounts', amounts)\n"
        "class BagSpec(ts.Spec):\n"
        "    def __init__(self, mapping: dict) -> None:\n"
        "        self.mapping = mapping\n"
        "    def polish(self) -> None:\n"
        "        return None\n"
        "class Item(ts.Entity):\n"
        "    pass\n"
        "class WireRequest(tc.Request):\n"
        "    def __init__(self, items: list) -> None:\n"
        "        self.items = items\n"
        "    def validate(self) -> None:\n"
        "        return None\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "Money.__init__" in f and "a value object constructs from primitives and value objects" in f
        for f in findings
    )
    assert any(
        "BagSpec.__init__" in f and "a spec field is a primitive, a value object, or a child spec" in f
        for f in findings
    )
    assert any("BagSpec.polish" in f and "a spec only carries construction data" in f for f in findings)
    assert any("Item" in f and "an entity constructs from exactly one ts.Spec" in f for f in findings)
    assert any(
        "WireRequest.__init__" in f and "a DTO field is a primitive or another DTO" in f
        for f in findings
    )
    assert any("WireRequest.validate" in f and "a DTO carries data and nothing else" in f for f in findings)

def test_an_eval_lives_only_in_a_gateway(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    body = "import tesser.testing as ts\ndef test_model_picks_a_tool() -> None:\n    assert True\n"
    conftest.write_module(tmp_path, "app/adapters/eval_flat.py", body)
    conftest.write_module(tmp_path, "app/tests/__init__.py", "")
    conftest.write_module(tmp_path, "app/tests/eval_tier.py", body)
    conftest.write_module(tmp_path, "app/domain/eval_role.py", body)
    findings = conftest.check_tree(tmp_path)
    for outside in ("app.adapters.eval_flat", "app.tests.eval_tier", "app.domain.eval_role"):
        assert any(
            f"{outside} is an eval outside a gateway; an eval lives only in a gateway, "
            "the one place a sampled real-model call is honest" in f
            for f in findings
        ), outside

    conftest.write_module(tmp_path, "app/adapters/gateways/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/gateways/eval_llm.py", body)
    conftest.write_module(tmp_path, "app/adapters/gateways/llm/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/gateways/llm/evals/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/gateways/llm/evals/eval_tools.py", body)
    housed = conftest.check_tree(tmp_path)
    assert not any("eval_llm is an eval outside a gateway" in f for f in housed)
    assert not any("eval_tools is an eval outside a gateway" in f for f in housed)

def test_a_handler_sibling_fakes_only_the_client(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/handlers/http.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as client\n"
        "class Handler(ts.Handler):\n"
        "    def __init__(self, c: client.Client) -> None:\n"
        "        self._c = c\n",
    )
    conftest.write_module(tmp_path, "app/adapters/handlers/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/adapters/handlers/test_http.py",
        "import tesser.testing as ts\n"
        "import app.adapters.handlers.http as http\n"
        "import app.client.client as client\n"
        "import app.application.service as application\n"
        "import app.adapters.gateways as gateways\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/__init__.py",
        "",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.handlers.test_http imports app.application.service, but a test "
        "placed in handlers reaches only adapters.handlers, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "app.adapters.handlers.test_http imports app.adapters.gateways, but a test "
        "placed in handlers reaches only adapters.handlers, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_http:2" in f for f in findings)
    assert not any("test_http:3" in f for f in findings)

def test_a_srv_test_reaches_a_context_only_through_its_handlers(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/handlers/http.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as client\n"
        "class Handler(ts.Handler):\n"
        "    def __init__(self, c: client.Client) -> None:\n"
        "        self._c = c\n",
    )
    conftest.write_module(tmp_path, "app/adapters/handlers/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "srv/test_router.py",
        "import tesser.testing as ts\n"
        "import app.adapters.handlers.http as http\n"
        "import app.application.service as application\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "srv.test_router imports app.application.service, but a test placed in "
        "srv reaches a context only through its handlers; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_router:2" in f for f in findings)

def test_a_test_reaches_only_what_its_placement_allows(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "far/domain/test_thing.py",
        "import tesser.testing as ts\n"
        "import far.client.client as client\n"
        "import app.client.client as foreign\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "far/domain/thing.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    conftest.write_module(
        tmp_path,
        "far/client/client.py",
        "import tesser.context as ts\n"
        "class Client(ts.Client):\n"
        "    ...\n",
    )
    conftest.write_module(tmp_path, "far/domain/__init__.py", "")
    conftest.write_module(tmp_path, "far/client/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "far.domain.test_thing imports far.client.client, but a test placed in domain "
        "reaches only domain of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "far.domain.test_thing imports app.client.client, but a test placed in domain "
        "reaches no neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )

def test_a_repository_sibling_test_reaches_its_kind_and_application_only(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/repositories/words.py",
        "import tesser.adapters as ts\n"
        "class WordsRepository(ts.Repository):\n"
        "    def __init__(self) -> None:\n"
        "        self._rows: dict[str, str] = {}\n",
    )
    conftest.write_module(tmp_path, "app/adapters/repositories/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/adapters/repositories/test_words.py",
        "import app.adapters.repositories.words as words\n"
        "import app.application.ports.words as words_port\n"
        "import app.domain.thing as thing\n"
        "import far.client.client as farclient\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "far/client/client.py",
        "import tesser.context as ts\n"
        "class Ping(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(tmp_path, "far/client/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "far/domain/thing.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    conftest.write_module(tmp_path, "far/domain/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.repositories.test_words imports app.domain.thing, but a test placed "
        "in repositories reaches only adapters.repositories, application.ports of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "app.adapters.repositories.test_words imports far.client.client, but a test placed "
        "in repositories reaches no neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_words.py:1:" in f for f in findings)
    assert not any("test_words.py:2:" in f for f in findings)

def test_a_wiring_sibling_test_mirrors_production_wiring_reach(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/wiring/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/wiring/test_wire.py",
        "import app.application.service as service\n"
        "import far.client.client as farclient\n"
        "import app.domain.thing as thing\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "far/client/client.py",
        "import tesser.context as ts\n"
        "class Ping(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(tmp_path, "far/client/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "far/domain/thing.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    conftest.write_module(tmp_path, "far/domain/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.wiring.test_wire imports app.domain.thing, but a test placed in wiring "
        "reaches only wiring, application, adapters, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_wire.py:1:" in f for f in findings)
    assert not any("test_wire.py:2:" in f for f in findings)

def test_a_client_sibling_test_reaches_only_its_own_client(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/client/test_client.py",
        "import app.client.client as client\n"
        "import app.domain.thing as thing\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.client.test_client imports app.domain.thing, but a test placed in client "
        "reaches only client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_client.py:1:" in f for f in findings)

def test_a_bootstrap_test_reaches_a_context_like_production_bootstrap(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "bootstrap/test_boot.py",
        "import app.client.client as client\n"
        "import app.domain.thing as thing\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(tmp_path, "bootstrap/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "bootstrap.test_boot imports app.domain.thing, but a test placed in "
        "bootstrap reaches a context only through its wiring, client, and adapters; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_boot.py:1:" in f for f in findings)

def test_a_protocol_test_reaches_no_context(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "protocol/test_proto.py",
        "import app.client.client as client\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(tmp_path, "protocol/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "protocol.test_proto imports app.client.client, but a test placed in "
        "protocol reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )

def test_a_test_that_resolves_to_no_tier_is_itself_a_finding(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/test_flat.py",
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/blobs/test_blob.py",
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(tmp_path, "app/adapters/blobs/__init__.py", "")
    conftest.write_module(tmp_path, "app/adapters/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.test_flat resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )
    assert any(
        "app.adapters.blobs.test_blob resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )

def test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application(
    tmp_path: Path,
) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "near/tests/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "near/domain/thing.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    conftest.write_module(
        tmp_path,
        "near/client/client.py",
        "import tesser.context as ts\n"
        "class Client(ts.Client):\n"
        "    ...\n",
    )
    conftest.write_module(tmp_path, "near/domain/__init__.py", "")
    conftest.write_module(tmp_path, "near/client/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "near/tests/test_wiring.py",
        "import tesser.testing as ts\n"
        "import near.domain.thing as thing\n"
        "import app.application.service as neighbour\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    assert not any("near.tests.test_wiring" in f for f in conftest.check_tree(tmp_path))

    conftest.write_module(tmp_path, "near/tests/__init__.py", "X = 1\n")
    assert any(
        "near.tests __init__ declares code; a context tests __init__ is empty" in f
        for f in conftest.check_tree(tmp_path)
    )

    conftest.write_module(tmp_path, "near/tests/__init__.py", "")
    conftest.write_module(tmp_path, "near/tests/helpers.py", "VALUE = 1\n")
    assert any(
        "near.tests.helpers is neither a test module nor conftest; "
        "a context tests package holds only test modules and conftest" in f
        for f in conftest.check_tree(tmp_path)
    )

def test_a_role_must_be_a_package(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "flat/domain.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    conftest.write_module(
        tmp_path,
        "flat/client/client.py",
        "import tesser.context as ts\n"
        "class Client(ts.Client):\n"
        "    ...\n",
    )
    conftest.write_module(tmp_path, "flat/client/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "flat.domain is a role module; a role is a package, never a module" in f
        for f in findings
    )
    assert not any("flat.client" in f for f in findings)

def test_a_role_may_be_a_package(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "deep/domain/__init__.py",
        "from deep.domain.money import Money\n",
    )
    conftest.write_module(
        tmp_path,
        "deep/domain/money.py",
        "import tesser.domain as ts\n"
        "import deep.domain.currency as currency\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str, unit: currency.Currency) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n"
        "        object.__setattr__(self, '_unit', unit)\n",
    )
    conftest.write_module(
        tmp_path,
        "deep/domain/currency.py",
        "import tesser.domain as ts\n"
        "class Currency(ts.ValueObject):\n"
        "    def __init__(self, code: str) -> None:\n"
        "        object.__setattr__(self, '_code', code)\n",
    )
    conftest.write_module(
        tmp_path,
        "deep/domain/svc.py",
        "import tesser.application as ts\n"
        "class SneakyService(ts.ApplicationService):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("deep.domain.money" in f and "not a context module" in f for f in findings)
    assert not any("deep.domain.money" in f and "the same-context matrix" in f for f in findings)
    assert any(
        "deep.domain.svc.SneakyService" in f and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "deep.domain.svc" in f and "imports tesser.application" in f
        and "a role module imports only its own tesser package" in f
        for f in findings
    )

def test_wiring_is_a_role(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "app/wiring/wire.py",
        "import tesser.context as ts\n"
        "import app.application.service as application\n"
        "import app.client.client as client\n"
        "import two.client.client as two_client\n"
        "import two.domain.thing\n"
        "class AskWiring(ts.Wiring):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app.wiring.wire" in f and "not a context module" in f for f in findings)
    assert not any("app.wiring.wire" in f and "imports app.application.service" in f for f in findings)
    assert not any("app.wiring.wire" in f and "imports two.client.client" in f for f in findings)
    assert not any("app.wiring.wire.AskWiring" in f and "a kind lives only in its role module" in f for f in findings)
    assert any(
        "app.wiring.wire" in f and "imports two.domain.thing" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )

def test_srv_and_bootstrap_import_rows(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "two/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class Bridge(ts.Gateway):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/http.py",
        "import app.application.service\n"
        "import app.adapters.gateways as app_adapters\n"
        "import two.adapters.gateways\n"
        "import bootstrap.wire\n",
    )
    conftest.write_module(
        tmp_path,
        "bootstrap/wire.py",
        "import app.domain.thing\n"
        "import app.wiring.wire as wiring\n"
        "import app.client.client as app_client\n"
        "import srv.http\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "srv.http" in f and "imports app.application.service" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert any(
        "srv.http" in f and "imports two.adapters.gateways" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.http" in f and "imports app.adapters.gateways" in f for f in findings)
    assert not any("srv.http" in f and "imports bootstrap.wire" in f for f in findings)
    assert any(
        "bootstrap.wire" in f and "imports app.domain.thing" in f
        and "bootstrap builds from wiring, clients, and adapters, never domain or application" in f
        for f in findings
    )
    assert not any("bootstrap.wire" in f and "imports app.wiring.wire" in f for f in findings)
    assert not any("bootstrap.wire" in f and "imports app.client.client" in f for f in findings)
    assert any(
        "bootstrap.wire" in f and "imports srv.http" in f
        and "the composition root never imports a host" in f
        for f in findings
    )

def test_only_a_handler_imports_its_own_client(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as app_client\n"
        "class HttpHandler(ts.Handler):\n"
        "    def ask(self, body: str) -> str:\n"
        "        return app_client.AskRequest(text=body).text\n",
    )
    conftest.write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "two/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import two.client.client\n"
        "class SneakyGateway(ts.Gateway):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app.adapters.gateways" in f and "imports app.client.client" in f for f in findings)
    assert any(
        "two.adapters.gateways" in f and "imports two.client.client" in f
        and "only a handler imports its own context's client" in f
        for f in findings
    )

def test_only_a_gateway_reaches_a_foreign_client(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import two.client.client\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways" in f and "imports two.client.client" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )

def test_role_module_tesser_import_is_exactly_once_as_ts(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "lone/domain/thing.py",
        "class Bare:\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "noalias/domain/thing.py",
        "import tesser.domain as td\n"
        "class ThingSpec(td.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "fromform/domain/thing.py",
        "from tesser.domain import Spec\n"
        "class OtherSpec(Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "dup/domain/thing.py",
        "import tesser.domain as ts\n"
        "import tesser.domain as ts\n"
        "class DupSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "lone.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "noalias.domain.thing imports tesser.domain without the ts alias; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "fromform.domain.thing imports names from tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "dup.domain.thing imports tesser.domain again; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )

def test_reexport_only_role_init_needs_no_tesser_import(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "deep/domain/__init__.py",
        "from deep.domain.money import Money\n",
    )
    conftest.write_module(
        tmp_path,
        "deep/domain/money.py",
        "import tesser.domain as ts\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("deep.domain" in f and "exactly once, as ts" in f for f in findings)

def test_test_module_tesser_import_rules(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/test_imports.py",
        "import tesser.domain as ts\n"
        "import tesser.testing as th\n"
        "import tesser.testing as ts2\n"
        "def test_nothing() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "app/test_fromform.py",
        "from tesser.testing import fake\n"
        "def test_nothing() -> None:\n"
        "    assert fake is not None\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.test_imports imports tesser.domain; a test module imports only tesser.testing" in f
        for f in findings
    )
    assert any(
        "app.test_imports imports tesser.testing without the ts alias; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )
    assert any(
        "app.test_imports imports tesser.testing again; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )
    assert any(
        "app.test_fromform imports names from tesser.testing; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )

def test_homeless_modules_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "loose.py", "def anything() -> None:\n    return None\n")
    conftest.write_module(tmp_path, "stray/util.py", "def anything() -> None:\n    return None\n")
    conftest.write_module(tmp_path, "rules.py", "def anything() -> None:\n    return None\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "loose belongs to no governed package; "
        "every module belongs to a context, srv, bootstrap, tests, or the protocol package" in f
        for f in findings
    )
    assert any(
        "stray.util belongs to no governed package; "
        "every module belongs to a context, srv, bootstrap, tests, or the protocol package" in f
        for f in findings
    )
    assert any("rules belongs to no governed package" in f for f in findings)

def test_tests_package_totality_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "tests/__init__.py", "X = 1\n")
    conftest.write_module(tmp_path, "tests/util.py", "def anything() -> None:\n    return None\n")
    conftest.write_module(tmp_path, "tests/test_ok.py", "def test_ok() -> None:\n    assert True\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "tests __init__ declares code; "
        "a tests package holds only test modules and conftest" in f
        for f in findings
    )
    assert any(
        "tests.util is neither a test module nor conftest; "
        "a tests package holds only test modules and conftest" in f
        for f in findings
    )
    assert not any("tests.test_ok" in f and "a tests package holds" in f for f in findings)

def test_role_init_only_reexports_its_own_role(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "pkg/domain/__init__.py",
        "import tesser.domain as ts\n"
        "from pkg.domain.vo import Tag\n"
        "LIMIT = 3\n",
    )
    conftest.write_module(
        tmp_path,
        "pkg/domain/vo.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "pkg.domain imports tesser.domain; a role __init__ only re-exports from its own role" in f
        for f in findings
    )
    assert any(
        "pkg.domain __init__ declares code; "
        "a role __init__ only re-exports from its own role" in f
        for f in findings
    )
    assert not any("imports pkg.domain.vo" in f for f in findings)
    assert any(
        "pkg.domain imports names from pkg.domain.vo; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )

def test_a_role_init_may_import_a_module_but_never_a_class(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "mod/domain/vo.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    conftest.write_module(tmp_path, "mod/domain/__init__.py", "import mod.domain.vo as vo\n")
    conftest.write_module(
        tmp_path,
        "mod/client/client.py",
        "import tesser.context as ts\n"
        "class AskRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(tmp_path, "mod/client/__init__.py", "")
    assert not any("mod.domain:" in f for f in conftest.check_tree(tmp_path))

    conftest.write_module(tmp_path, "mod/domain/__init__.py", "from mod.domain.vo import Tag\n")
    assert any(
        "mod.domain imports names from mod.domain.vo; "
        "a context module is imported as an aliased module, never its members" in f
        for f in conftest.check_tree(tmp_path)
    )

def test_srv_and_bootstrap_statement_totality(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "srv/box.py",
        "import tesser.srv as ts\n"
        "import tesser.domain as td\n"
        "@ts.function\n"
        "def fine() -> None:\n"
        "    return None\n"
        "def stray() -> None:\n"
        "    return None\n"
        "class Box:\n"
        "    pass\n"
        "class Server(ts.Host):\n"
        "    pass\n"
        "LIMIT = 3\n"
        "print('hi')\n",
    )
    conftest.write_module(
        tmp_path,
        "bootstrap/wire.py",
        "def build() -> None:\n"
        "    return None\n"
        "class App:\n"
        "    pass\n"
        "LIMIT = 3\n"
        "print('hi')\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "srv.box imports tesser.domain; a srv module imports only tesser.srv" in f
        for f in findings
    )
    assert any(
        "srv.box.stray" in f
        and "a srv function declares itself with @ts.function" in f
        for f in findings
    )
    assert not any("srv.box.fine" in f for f in findings)
    assert any(
        "srv.box.Box" in f and "declares no ts.* base; a srv class declares its block" in f
        for f in findings
    )
    assert not any("srv.box.Server" in f for f in findings)
    assert any(
        "srv.box" in f and "declares a module constant without Final; a srv constant is Final" in f
        for f in findings
    )
    assert any(
        "srv.box" in f and "has a loose module-level statement; a srv module holds only imports, "
        "declared classes and functions, and Final constants" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire never imports tesser.context; "
        "a bootstrap module imports tesser.context exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire.build" in f
        and "a bootstrap function declares itself with @ts.function" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire.App" in f
        and "is a class; a bootstrap module holds only imports, declared functions, "
        "and Final constants" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire" in f
        and "declares a module constant without Final; a bootstrap constant is Final" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire" in f
        and "has a loose module-level statement; a bootstrap module holds only imports, "
        "declared functions, and Final constants" in f
        for f in findings
    )

def test_pure_core_stdlib_allowlist(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "io1/domain/thing.py",
        "import os\n"
        "import datetime\n"
        "import tesser.domain as ts\n"
        "class StampSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "io1/client/client.py",
        "from __future__ import annotations\n"
        "import datetime\n"
        "import tesser.context as ts\n"
        "class StampRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "io1/adapters/gateways.py",
        "from pathlib import Path\n"
        "import tesser.adapters as ts\n"
        "class DiskRepository(ts.Repository):\n"
        "    def load(self, key: str) -> str: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "io1.domain.thing imports os; domain, client, and application "
        "import only their context, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("io1.domain.thing imports datetime" in f for f in findings)
    assert any(
        "io1.client.client imports datetime; domain, client, and application "
        "import only their context, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("imports __future__" in f for f in findings)
    assert not any("io1.adapters.gateways" in f and "the pure stdlib" in f for f in findings)

def test_context_module_import_form(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "form/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "form/application/service.py",
        "import tesser.application as ts\n"
        "from form.client.client import PingRequest\n",
    )
    conftest.write_module(
        tmp_path,
        "form/wiring/wire.py",
        "import tesser.context as ts\n"
        "import form.application.service\n"
        "class PingWiring(ts.Wiring):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "form.application.service imports names from form.client.client; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "form.wiring.wire imports form.application.service without an alias; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )

def test_relative_imports_resolve_against_the_package(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "rel/domain/__init__.py",
        "from .money import Money\n",
    )
    conftest.write_module(
        tmp_path,
        "rel/domain/money.py",
        "import tesser.domain as ts\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n",
    )
    conftest.write_module(
        tmp_path,
        "rel/client/client.py",
        "import tesser.context as ts\n"
        "class RelRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "rel/wiring/wire.py",
        "import tesser.context as ts\n"
        "from ..client.client import RelRequest\n"
        "class RelWiring(ts.Wiring):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "rel/adapters/repo.py",
        "import tesser.adapters as ts\n"
        "from ..domain.money import Money\n"
        "class LoadingRepo(ts.Repository):\n"
        "    def load(self, key: str) -> Money: ...\n",
    )
    conftest.write_module(
        tmp_path,
        "rel/adapters/beyond.py",
        "import tesser.adapters as ts\n"
        "from ...domain.money import Money\n"
        "class BeyondRepo(ts.Repository):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("rel.domain" in f and "a role __init__ only re-exports from its own role" in f for f in findings)
    assert any(
        "rel.adapters.beyond imports ...domain.money beyond the package root; "
        "a relative import resolves inside the tree" in f
        for f in findings
    )
    assert any(
        "rel.wiring.wire imports names from rel.client.client; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "rel.adapters.repo imports rel.domain.money; the same-context matrix" in f
        for f in findings
    )
    assert any(
        "LoadingRepo.load" in f and "an adapter speaks records, never domain objects" in f
        for f in findings
    )

def test_nested_imports_neither_classify_nor_satisfy_presence(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "lazy/domain/thing.py",
        "class HiddenSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        import tesser.domain as ts\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "lazy2/domain/thing.py",
        "import tesser.domain as ts\n"
        "class LazySpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        import os\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "lazy3/domain/thing.py",
        "import tesser.domain as ts\n"
        "class GoodSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        import tesser.context as tc\n"
        "        self.text = text\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "lazy.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "lazy.domain.thing.HiddenSpec" in f and "declares no ts.* base" in f for f in findings
    )
    assert any(
        "lazy2.domain.thing imports os; domain, client, and application "
        "import only their context, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert any(
        "lazy3.domain.thing imports tesser.context inside a function; "
        "a tesser import is module-level" in f
        for f in findings
    )

def test_srv_and_bootstrap_tesser_form_modes(tmp_path: Path) -> None:
    conftest.write_module(
        tmp_path,
        "srv/dup.py",
        "import tesser.srv as ts\n"
        "import tesser.srv as ts\n"
        "@ts.function\n"
        "def go() -> None:\n"
        "    return None\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/alias.py",
        "import tesser.srv as tc\n"
        "@tc.function\n"
        "def go() -> None:\n"
        "    return None\n",
    )
    conftest.write_module(
        tmp_path,
        "bootstrap/fromform.py",
        "from tesser.context import function\n"
        "@function\n"
        "def go() -> None:\n"
        "    return None\n",
    )
    conftest.write_module(
        tmp_path,
        "bootstrap/wrongpkg.py",
        "import tesser.context as ts\n"
        "import tesser.domain as td\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/consts.py",
        "from typing import Final\n"
        "LIMIT: Final[int] = 3\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/annconst.py",
        "LIMIT: int = 3\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/tfinal.py",
        "import tesser.srv as ts\n"
        "import typing\n"
        "LIMIT: typing.Final[int] = 3\n",
    )
    conftest.write_module(tmp_path, "srv/__init__.py", "X = 1\n")
    conftest.write_module(tmp_path, "bootstrap/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "konst/domain/thing.py",
        "from typing import Final\n"
        "LIMIT: Final[int] = 3\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "srv.dup imports tesser.srv again; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv.alias imports tesser.srv without the ts alias; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "bootstrap.fromform imports names from tesser.context; "
        "a bootstrap module imports tesser.context exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "bootstrap.wrongpkg imports tesser.domain; "
        "a bootstrap module imports only tesser.context" in f
        for f in findings
    )
    assert any(
        "srv.consts never imports tesser.srv; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv.annconst declares a module constant without Final; "
        "a srv constant is Final" in f
        for f in findings
    )
    assert not any("srv.tfinal" in f for f in findings)
    assert any(
        "konst.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv __init__ declares code; a srv or bootstrap __init__ is empty" in f
        for f in findings
    )
    assert not any("bootstrap __init__ declares code" in f for f in findings)

def test_protocol_module_totality_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "protocol/box.py",
        "import tesser.srv as ts\n"
        "import json\n"
        "import app.client.client\n"
        "import srv.host\n"
        "from typing import Final, Protocol\n"
        "class BoxRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        super().__init__(text=text)\n"
        "    text: str\n"
        "class BoxResponse(ts.Response):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        super().__init__(text=text)\n"
        "    text: str\n"
        "class BoxLabel(ts.Record):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        super().__init__(text=text)\n"
        "    text: str\n"
        "class Endpoint(ts.Port, Protocol):\n"
        "    def __call__(self, request: BoxRequest) -> BoxResponse: ...\n"
        "class Loose:\n"
        "    pass\n"
        "class Server(ts.Host):\n"
        "    pass\n"
        "@ts.function\n"
        "def fine() -> None:\n"
        "    return None\n"
        "@ts.function\n"
        "def lazy() -> None:\n"
        "    import tesser.domain\n"
        "def stray() -> None:\n"
        "    return None\n"
        "LIMIT: Final[int] = 3\n"
        "ANNBARE: int = 3\n"
        "BARE = 3\n"
        "print('hi')\n",
    )
    conftest.write_module(tmp_path, "srv/host.py", "import tesser.srv as ts\n")
    findings = conftest.check_tree(tmp_path)
    assert not any("protocol.box.BoxRequest" in f for f in findings)
    assert not any("protocol.box.BoxResponse" in f for f in findings)
    assert not any("protocol.box.BoxLabel" in f for f in findings)
    assert not any("protocol.box.Endpoint" in f for f in findings)
    assert not any("protocol.box.fine" in f for f in findings)
    assert not any("protocol.box belongs to no governed package" in f for f in findings)
    assert any(
        "protocol.box imports app.client.client; a protocol module is context-generic and imports no context" in f
        for f in findings
    )
    assert any(
        "protocol.box imports srv.host; a protocol module never imports srv or bootstrap" in f
        for f in findings
    )
    assert any(
        "protocol.box.Loose" in f and "declares no ts.* base; a protocol class declares its block" in f
        for f in findings
    )
    assert any(
        "protocol.box.Server" in f and "is a host; only protocol ports, protocol records, "
        "protocol rejections, protocol requests, and protocol responses live in a protocol module" in f
        for f in findings
    )
    assert any(
        "protocol.box.stray" in f and "a protocol function declares itself with @ts.function" in f
        for f in findings
    )
    assert (
        len(
            [
                f
                for f in findings
                if "protocol.box" in f
                and "declares a module constant without Final; a protocol constant is Final" in f
            ]
        )
        == 2
    )
    assert any(
        "protocol.box" in f and "imports tesser.domain inside a function; a tesser import is module-level" in f
        for f in findings
    )
    assert any(
        "protocol.box" in f and "has a loose module-level statement; a protocol module holds only imports, "
        "declared classes and functions, and Final constants" in f
        for f in findings
    )

def test_protocol_module_tesser_import_is_exactly_once_as_ts(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "protocol/loud.py",
        "import tesser.context as ts\n",
    )
    conftest.write_module(tmp_path, "protocol/quiet.py", "")
    conftest.write_module(
        tmp_path,
        "protocol/dup.py",
        "import tesser.srv as ts\n"
        "import tesser.srv as ts\n",
    )
    conftest.write_module(
        tmp_path,
        "protocol/form.py",
        "from tesser.srv import Request\n",
    )
    conftest.write_module(
        tmp_path,
        "protocol/alias.py",
        "import tesser.srv as tz\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "protocol.loud imports tesser.context; a protocol module imports only tesser.srv" in f
        for f in findings
    )
    assert any(
        "protocol.quiet never imports tesser.srv; a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "protocol.dup imports tesser.srv again; a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "protocol.form imports names from tesser.srv; "
        "a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "protocol.alias imports tesser.srv without the ts alias; "
        "a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )

def test_only_the_top_level_protocol_package_holds_protocol_modules(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "protocol/__init__.py", "")
    conftest.write_module(tmp_path, "protocol/box.py", "import tesser.srv as ts\n")
    conftest.write_module(tmp_path, "boxwire.py", "import tesser.srv as ts\n")
    conftest.write_module(tmp_path, "wire.py", "import tesser.srv as ts\n")
    findings = conftest.check_tree(tmp_path)
    assert not any("protocol/box.py" in f for f in findings)
    assert not any("protocol/__init__.py" in f for f in findings)
    assert any("boxwire belongs to no governed package" in f for f in findings)
    assert any("wire belongs to no governed package" in f for f in findings)

def test_a_protocol_init_is_empty(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "protocol/__init__.py", "LIMIT = 3\n")
    conftest.write_module(tmp_path, "protocol/box.py", "import tesser.srv as ts\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "protocol __init__ declares code; a protocol __init__ is empty" in f
        for f in findings
    )

def test_a_fake_may_implement_a_protocol_port(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "protocol/box.py",
        "from typing import Protocol\n"
        "import tesser.srv as ts\n"
        "class BoxDoor(ts.Port, Protocol):\n"
        "    def __call__(self) -> None: ...\n",
    )
    conftest.write_module(
        tmp_path,
        "app/test_doors.py",
        "import tesser.testing as ts\n"
        "from protocol.box import BoxDoor\n"
        "@ts.fake\n"
        "class FakeDoor(BoxDoor):\n"
        "    def __call__(self) -> None:\n"
        "        return None\n"
        "def test_door() -> None:\n"
        "    assert FakeDoor\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app.test_doors.FakeDoor" in f for f in findings)

def test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import tesser.srv\n"
        "from typing import Protocol\n"
        "class Sneaky(tesser.srv.Host):\n"
        "    pass\n"
        "class WireAsk(tesser.srv.Request):\n"
        "    pass\n"
        "class WireReply(tesser.srv.Response):\n"
        "    pass\n"
        "class WireDoor(tesser.srv.Port, Protocol):\n"
        "    def __call__(self) -> None: ...\n"
        "class WireLabel(tesser.srv.Record):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/box.py",
        "import tesser.srv as ts\n"
        "import tesser.domain\n"
        "class Value(tesser.domain.ValueObject):\n"
        "    pass\n"
        "class Turn(ts.Response):\n"
        "    pass\n"
        "class Label(ts.Record):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways.Sneaky" in f
        and "is a host; a host lives in srv and a protocol kind in a protocol module, never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireAsk" in f
        and "is a protocol request record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireReply" in f
        and "is a protocol response record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireDoor" in f
        and "is a protocol port; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireLabel" in f
        and "is a protocol record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "srv.box.Value" in f and "is a value object; only a host class lives in a srv module" in f
        for f in findings
    )
    assert any(
        "srv.box.Turn" in f
        and "is a protocol response record; only a host class lives in a srv module" in f
        for f in findings
    )
    assert any(
        "srv.box.Label" in f
        and "is a protocol record; only a host class lives in a srv module" in f
        for f in findings
    )

def test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/test_forms.py",
        "from app.domain.thing import Thing\n"
        "def test_thing() -> None:\n"
        "    assert Thing\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/http.py",
        "from app.adapters.gateways import HttpHandler\n",
    )
    conftest.write_module(
        tmp_path,
        "skipctx/domain/thing.py",
        "import tesser.domain as ts\n"
        "from app.client.client import AskRequest\n"
        "class SkipSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.test_forms imports names from app.domain.thing; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "srv.http imports names from app.adapters.gateways; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "skipctx.domain.thing imports app.client.client; a context reaches another context "
        "only through its client, and only from gateways and wiring" in f
        for f in findings
    )
    assert not any(
        "skipctx.domain.thing" in f and "a context module is imported as an aliased module" in f
        for f in findings
    )

def test_pure_core_allowlist_covers_application_and_domain_future(tmp_path: Path) -> None:
    conftest.write_module(
        tmp_path,
        "io2/domain/thing.py",
        "from __future__ import annotations\n"
        "import tesser.domain as ts\n"
        "class DSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    conftest.write_module(
        tmp_path,
        "io2/application/service.py",
        "from __future__ import annotations\n"
        "import typing\n"
        "import socket\n"
        "import tesser.application as ts\n"
        "class NopService(ts.ApplicationService):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("io2.domain.thing" in f and "the pure stdlib" in f for f in findings)
    assert any(
        "io2.application.service imports socket; domain, client, and application "
        "import only their context, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("io2.application.service:1" in f for f in findings)
    assert not any("io2.application.service:2" in f for f in findings)

def test_an_adapters_module_holds_one_kind(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n"
        "class SideGateway(ts.Gateway):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways mixes adapter kinds" in f and "an adapters module holds one adapter kind" in f
        for f in findings
    )

def test_a_dotted_module_base_resolves(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/test_doubles.py",
        "import tesser.testing as th\n"
        "import app.application.service\n"
        "@th.fake\n"
        "class FakePort(app.application.service.AskService):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("FakePort" in f and "implements no ts.Port" in f and "undeclared" in f for f in findings)
    assert any(
        "FakePort" in f and "a fake implements the port or client it doubles" in f
        for f in findings
    )

def test_edge_records_reject_an_empty_target() -> None:
    with pytest.raises(ValueError):
        domain.ImportEdge("", 1, False, False)
    with pytest.raises(ValueError):
        domain.TesserImport("", 1, False, False)

def test_a_test_module_may_omit_tesser_testing(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "tests/test_bare.py", "def test_bare() -> None:\n    assert True\n")
    findings = conftest.check_tree(tmp_path)
    assert not any("test_bare" in f for f in findings)

def test_a_denied_app_edge_is_not_form_checked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "srv/host.py",
        "import tesser.srv as ts\n"
        "from app.domain import thing\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "srv.host imports app.domain" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.host" in f and "never its members" in f for f in findings)

def test_a_colliding_module_definition_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "col.py", "import tesser.srv as ts\n")
    conftest.write_module(tmp_path, "col/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert any(
        "col/__init__.py:1: TB043" in f and "a module has one definition" in f
        for f in findings
    )

def test_an_unparseable_module_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "broken.py", "def f(:\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "broken.py:1: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert any("app/domain/thing.py" not in f for f in findings)

def test_a_non_utf8_file_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / "binary.py").write_bytes(b"\xff\xfe\x00junk")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "binary.py:1: TB043" in f and "every checked module is readable UTF-8 Python" in f
        for f in findings
    )

def test_skip_dirs_are_not_walked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, ".venv/lib/junk.py", "def f(:\n")
    conftest.write_module(tmp_path, "node_modules/pkg/mod.py", "x = 1\n")
    assert conftest.check_tree(tmp_path) == ()

def test_an_ignore_suppresses_exactly_its_finding(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore TB040\n")
    findings = conftest.check_tree(tmp_path)
    assert not any("stray" in f for f in findings)

def test_a_scoped_ignore_leaves_other_codes_alone(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore TB050\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "stray belongs to no governed package" in f and " TB040 " in f for f in findings
    )
    assert any(
        "stray.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )

def test_a_stale_ignore_is_itself_a_finding(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/extra.py",
        "import tesser.domain as ts  # tessercheck:ignore\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )

def test_a_file_level_ignore_covers_the_whole_module(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "srv/host.py",
        "# tessercheck:ignore-file TB050\nimport os\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("never imports tesser.srv" in f for f in findings)
    assert not any("TB090" in f and "srv/host.py" in f for f in findings)

def test_a_marker_suppresses_several_codes_space_or_comma_separated(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore TB040 TB050\n")
    conftest.write_module(tmp_path, "loose.py", "import os  # tessercheck:ignore TB040, TB050\n")
    findings = conftest.check_tree(tmp_path)
    assert not any("stray" in f for f in findings)
    assert not any("loose" in f for f in findings)

def test_a_file_level_ignore_requires_codes(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore-file\n")
    findings = conftest.check_tree(tmp_path)
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("stray.py:1: TB090" in f for f in findings)

def test_a_typo_or_junk_token_makes_the_marker_inert(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os  # tessercheck:ignored TB040\n")
    conftest.write_module(tmp_path, "loose.py", "import os  # tessercheck:ignore TB040 permanent\n")
    conftest.write_module(tmp_path, "bracket.py", "import os  # tessercheck:ignore [TB040]\n")
    findings = conftest.check_tree(tmp_path)
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("loose belongs to no governed package" in f for f in findings)
    assert any("bracket belongs to no governed package" in f for f in findings)
    assert not any("stray.py" in f and "TB090" in f for f in findings)
    assert any("loose.py:1: TB090" in f for f in findings)
    assert any("bracket.py:1: TB090" in f for f in findings)

def test_a_bare_line_ignore_is_line_scoped(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/extra.py",
        "import os\nimport tesser.domain as ts  # tessercheck:ignore\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("app.domain.extra imports os" in f and " TB062 " in f for f in findings)
    assert any("app/domain/extra.py:2: TB090" in f for f in findings)

def test_tb090_itself_cannot_be_ignored(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/extra.py",
        "import tesser.domain as ts  # tessercheck:ignore-file TB090\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )

def test_reader_findings_are_never_inline_suppressible(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "broken.py", "# tessercheck:ignore-file TB043\ndef f(:\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "broken.py:2: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert not any("TB090" in f for f in findings)

def test_a_colliding_unparseable_file_reports_the_collision(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "col.py", "def f(:\n")
    conftest.write_module(tmp_path, "col/__init__.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert not any("every checked module parses" in f for f in findings)

def test_a_utf8_bom_file_is_checked_normally(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / "app" / "domain" / "bom.py").write_bytes(
        b"\xef\xbb\xbfimport tesser.domain as ts\n"
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("bom" in f for f in findings)

def test_optional_construction_data_is_the_only_union(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/opt.py",
        "import tesser.domain as ts\n"
        "class OptSpec(ts.Spec):\n"
        "    def __init__(self, text: str | None, items: list | None, mix: str | int) -> None:\n"
        "        self.text = text\n"
        "        self.items = items\n"
        "        self.mix = mix\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("parameter 'text'" in f for f in findings)
    assert any(
        "parameter 'items' is not allowed; "
        "a spec field is a primitive, a value object, or a child spec" in f
        for f in findings
    )
    assert any("parameter 'mix' is not allowed" in f for f in findings)


def test_comments_docstrings_and_bare_strings_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_prose.py",
        '"""A docstring."""\n'
        "# a prose comment\n"
        "x: int = 1  # type: ignore\n"
        "def test_ok() -> None:\n"
        "    y = 1\n"
        '    "a bare string"\n'
        "    assert y\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "test_prose.py:1: TB020" in f and "carries a docstring; "
        "code speaks for itself — comments, docstrings, and loose strings "
        "belong in the doc layer" in f
        for f in findings
    )
    assert any("test_prose.py:2: TB020" in f and "carries a code comment" in f for f in findings)
    assert any(
        "test_prose.py:6: TB020" in f and "carries a bare string statement" in f
        for f in findings
    )
    assert not any("test_prose.py:3:" in f and "TB020" in f for f in findings)


def test_mocking_library_and_patcher_fixtures_are_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_mocky.py",
        "from unittest.mock import patch\n"
        "import pytest\n"
        "def test_a(monkeypatch: pytest.MonkeyPatch) -> None:\n"
        "    assert patch\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "test_mocky.py:1: TB030" in f and "imports a mocking library; a test double is "
        "a hand-written fake, never a mocking library or a runtime patcher" in f
        for f in findings
    )
    assert any(
        "test_mocky.py:3: TB030" in f and "takes the monkeypatch fixture" in f
        for f in findings
    )
    assert any(
        "test_mocky.py:3: TB030" in f and "reaches for pytest MonkeyPatch" in f
        for f in findings
    )


def test_a_marked_patcher_seam_is_suppressed(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_seam.py",
        "def test_a(monkeypatch) -> None:  # tessercheck:ignore TB030\n"
        "    assert monkeypatch\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("test_seam" in f for f in findings)


def test_a_called_shadowed_builtin_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_shadow.py",
        "def test_a() -> None:\n"
        "    id = 'x'\n"
        "    assert id(3)\n"
        "def test_b(len: int = 0) -> None:\n"
        "    assert len == 0\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "test_shadow.py:3: TB033" in f and "binds id and calls it in the same scope; "
        "a shadowed builtin is never called — rename the binding" in f
        for f in findings
    )
    assert not any("test_shadow.py:5:" in f and "TB033" in f for f in findings)


def test_string_form_equality_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_streq.py",
        "def test_a() -> None:\n"
        "    a, b = 1, 2\n"
        "    assert str(a) == str(b)\n"
        "    assert str(a) == 'one'\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "test_streq.py:3: TB004" in f and "compare value objects by value, "
        "never by their string form" in f
        for f in findings
    )
    assert not any("test_streq.py:4:" in f for f in findings)


def test_a_value_object_mutable_collection_field_is_flagged(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/bag.py",
        "import tesser.domain as ts\n"
        "class Bag(ts.ValueObject):\n"
        "    _items: list[str]\n"
        "    _names: tuple[str, ...]\n"
        "    def __init__(self, item: str) -> None:\n"
        "        object.__setattr__(self, '_items', [item])\n"
        "        object.__setattr__(self, '_names', (item,))\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "bag.py:3: TB002" in f and "field _items is a mutable collection; "
        "a value object's field is hashable — a tuple or frozenset, never "
        "a mutable collection" in f
        for f in findings
    )
    assert not any("_names" in f and "TB002" in f for f in findings)


def test_mutable_set_and_quoted_annotations_are_still_mutable_collections(
    tmp_path: Path,
) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/holder.py",
        "import tesser.domain as ts\n"
        "from typing import MutableSet\n"
        "class Holder(ts.ValueObject):\n"
        "    _mset: MutableSet[str]\n"
        "    _quoted: 'list[str]'\n"
        "    def __init__(self, item: str) -> None:\n"
        "        object.__setattr__(self, '_mset', {item})\n"
        "        object.__setattr__(self, '_quoted', [item])\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("field _mset is a mutable collection" in f for f in findings)
    assert any("field _quoted is a mutable collection" in f for f in findings)


def test_the_retired_category_marker_is_an_ordinary_comment(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_marked.py",
        "# tesser-category: spec\n"
        "def test_ok() -> None:\n"
        "    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "test_marked.py:1: TB020" in f and "carries a code comment" in f for f in findings
    )


def test_a_value_object_hides_its_representation(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/leaky.py",
        "import tesser.domain as ts\n"
        "class Leaky(ts.ValueObject):\n"
        "    amount: int\n"
        "    _kept: int\n"
        "    def __init__(self, amount: int) -> None:\n"
        "        object.__setattr__(self, 'amount', amount)\n"
        "        object.__setattr__(self, '_kept', amount)\n"
        "    def kept(self) -> int:\n"
        "        return self._kept\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "leaky.py:3: TB010" in f and "exposes field amount; a value object hides its "
        "representation — a public field belongs on a spec" in f
        for f in findings
    )
    assert any(
        "TB010" in f and "Leaky.kept passes the raw primitive through; "
        "a value object's accessor returns a value object — "
        "the canonical exit is the only primitive door" in f
        for f in findings
    )


def test_an_accessor_never_hands_back_the_backing_collection(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/box.py",
        "import tesser.domain as ts\n"
        "class BoxSpec(ts.Spec):\n"
        "    def __init__(self, item: str) -> None:\n"
        "        self.item = item\n"
        "class Box(ts.AggregateRoot):\n"
        "    _items: list[str]\n"
        "    def __init__(self, spec: BoxSpec) -> None:\n"
        "        self._items = [spec.item]\n"
        "    def items(self) -> list[str]:\n"
        "        return self._items\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "TB011" in f and "Box.items hands back its backing collection; an accessor "
        "returns a defensive copy, never the backing store" in f
        for f in findings
    )


def test_an_aggregate_is_referenced_by_id_never_held(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/pair.py",
        "import tesser.domain as ts\n"
        "import app.domain.thing as thing\n"
        "class PairSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Pair(ts.AggregateRoot):\n"
        "    _other: thing.Thing\n"
        "    def __init__(self, spec: PairSpec) -> None:\n"
        "        self._other = thing.Thing(thing.ThingSpec(text=spec.text))\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "TB012" in f and "Pair field _other holds another aggregate root; an aggregate "
        "is referenced by its ID value object, never held" in f
        for f in findings
    )


def test_exit_norms_leaf_and_structured(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/exits.py",
        "import tesser.domain as ts\n"
        "@ts.function\n"
        "def canonical_str(value: str) -> str:\n"
        "    return value\n"
        "class GoodLeaf(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return canonical_str(self._value)\n"
        "class WrongExit(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __int__(self) -> int:\n"
        "        return 0\n"
        "class HandRolled(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return self._value.upper()\n"
        "class Compound(ts.ValueObject):\n"
        "    _a: GoodLeaf\n"
        "    _b: GoodLeaf\n"
        "    def __init__(self, a: str, b: str) -> None:\n"
        "        object.__setattr__(self, '_a', GoodLeaf(a))\n"
        "        object.__setattr__(self, '_b', GoodLeaf(b))\n"
        "    def __str__(self) -> str:\n"
        "        return 'x'\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("GoodLeaf" in f and "TB015" in f for f in findings)
    assert not any("GoodLeaf" in f and "TB018" in f for f in findings)
    assert any(
        "TB015" in f and "WrongExit.__int__ is a mismatched exit; a leaf defines exactly "
        "its backing type's conversion dunder" in f
        for f in findings
    )
    assert any(
        "TB018" in f and "HandRolled.__str__ hand-rolls its exit; a canonical exit is a "
        "one-line delegation to its canonical_* policy" in f
        for f in findings
    )
    assert any(
        "TB015" in f and "Compound.__str__ is a primitive exit; a structured domain "
        "object has no primitive exit — decompose through leaf components" in f
        for f in findings
    )


def test_composition_norms(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/shapes.py",
        "import tesser.domain as ts\n"
        "class Flag(ts.ValueObject):\n"
        "    _value: bool\n"
        "    def __init__(self, value: bool) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "class Mixed(ts.ValueObject):\n"
        "    _raw: str\n"
        "    _on: bool\n"
        "    def __init__(self, raw: str, on: bool) -> None:\n"
        "        object.__setattr__(self, '_raw', raw)\n"
        "        object.__setattr__(self, '_on', on)\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "TB016" in f and "Flag field _value is a bool; bool and complex are not "
        "value-object material — model the raw value or reach for an enum" in f
        for f in findings
    )
    assert any(
        "TB016" in f and "Mixed field _raw is a bare primitive; a compound backs "
        "itself with child value objects" in f
        for f in findings
    )
    assert any("TB016" in f and "Mixed field _on is a bool" in f for f in findings)


def test_a_value_object_has_one_construction_door(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/doors.py",
        "import tesser.domain as ts\n"
        "@ts.function\n"
        "def canonical_str(value: str) -> str:\n"
        "    return value\n"
        "class Slug(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return canonical_str(self._value)\n"
        "    @classmethod\n"
        "    def parse(cls, raw: str) -> 'Slug':\n"
        "        return cls(raw.strip())\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "TB017" in f and "Slug.parse is a second construction door; a value object has "
        "one door — its own __init__" in f
        for f in findings
    )


def test_domain_returns_and_spec_returns(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/returns.py",
        "import tesser.domain as ts\n"
        "class WidgetSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class Widget(ts.Entity):\n"
        "    def __init__(self, spec: WidgetSpec) -> None:\n"
        "        self._text = spec.text\n"
        "    def label(self) -> str:\n"
        "        return self._text.upper()\n"
        "    def snapshot(self) -> WidgetSpec:\n"
        "        return WidgetSpec(text=self._text)\n"
        "    def touch(self) -> None:\n"
        "        return None\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "TB019" in f and "Widget.label returns str; a domain object's public behavior "
        "hands back domain objects — the licensed exits are the protocol dunders, "
        "the canonical exit, and a -> None transition" in f
        for f in findings
    )
    assert any(
        "TB015" in f and "Widget.snapshot returns a spec; a domain object never "
        "serializes itself — a spec is construction data, not an exit" in f
        for f in findings
    )
    assert not any("Widget.touch" in f for f in findings)


def test_review_pins_for_the_shape_norms(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/pins.py",
        "import tesser.domain as ts\n"
        "from typing import ClassVar, Self\n"
        "@ts.function\n"
        "def canonical_str(value: str) -> str:\n"
        "    return value\n"
        "class SelfDoor(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return canonical_str(self._value)\n"
        "    @classmethod\n"
        "    def parse(cls, raw: str) -> Self:\n"
        "        return cls(raw)\n"
        "    @classmethod\n"
        "    def bare_door(cls, raw):  # type: ignore[no-untyped-def]\n"
        "        return cls(raw)\n"
        "    @classmethod\n"
        "    def kind(cls) -> type['SelfDoor']:\n"
        "        return cls\n"
        "class Quoted(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return canonical_str(self._value)\n"
        "    def label(self) -> 'str':\n"
        "        return self._value.upper()\n"
        "class Marked(ts.ValueObject):\n"
        "    _kinds: ClassVar[tuple[str, ...]] = ()\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return canonical_str(self._value)\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("SelfDoor.parse is a second construction door" in f for f in findings)
    assert any("SelfDoor.bare_door is a second construction door" in f for f in findings)
    assert not any("SelfDoor.kind" in f for f in findings)
    assert any(
        "Quoted.label returns str" in f and "TB019" in f for f in findings
    )
    assert not any("Marked" in f for f in findings)


def test_module_qualified_canonical_delegation_passes(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/policy.py",
        "import tesser.domain as ts\n"
        "@ts.function\n"
        "def canonical_str(value: str) -> str:\n"
        "    return value\n",
    )
    conftest.write_module(
        tmp_path,
        "app/domain/word.py",
        "import tesser.domain as ts\n"
        "import app.domain.policy as policy\n"
        "class Word(ts.ValueObject):\n"
        "    _value: str\n"
        "    def __init__(self, value: str) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __str__(self) -> str:\n"
        "        return policy.canonical_str(self._value)\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("Word" in f for f in findings)


def test_undeclared_backing_collection_is_still_caught(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/sack.py",
        "import tesser.domain as ts\n"
        "class SackSpec(ts.Spec):\n"
        "    def __init__(self, item: str) -> None:\n"
        "        self.item = item\n"
        "class Sack(ts.AggregateRoot):\n"
        "    def __init__(self, spec: SackSpec) -> None:\n"
        "        self._items = [spec.item]\n"
        "    def items(self) -> list[str]:\n"
        "        return self._items\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "TB011" in f and "Sack.items hands back its backing collection" in f
        for f in findings
    )


def test_bytes_is_construction_primitive(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/digest.py",
        "import tesser.domain as ts\n"
        "class Digest(ts.ValueObject):\n"
        "    _value: bytes\n"
        "    def __init__(self, value: bytes) -> None:\n"
        "        object.__setattr__(self, '_value', value)\n"
        "    def __bytes__(self) -> bytes:\n"
        "        return self._value\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("parameter 'value' is not allowed" in f for f in findings)


def test_a_root_conftest_is_a_leaf(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "conftest.py",
        "import os\nimport sys\nimport app.domain.thing\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("imports os" in f for f in findings)


def test_a_placed_conftest_carries_its_tier(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/conftest.py",
        "import bootstrap.wire\nimport app.domain.thing\n",
    )
    conftest.write_module(
        tmp_path,
        "app/tests/__init__.py",
        "",
    )
    conftest.write_module(
        tmp_path,
        "app/tests/conftest.py",
        "import app.domain.thing as thing\nimport srv.http\n",
    )
    conftest.write_module(tmp_path, "bootstrap/wire.py", "")
    conftest.write_module(tmp_path, "srv/http.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "tests.conftest imports app.domain.thing, but a test placed in "
        "the root tests package reaches a context only through its wiring and client; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("tests.conftest imports bootstrap.wire" in f for f in findings)
    assert not any("app.tests.conftest imports app.domain.thing" in f for f in findings)
    assert any(
        "app.tests.conftest imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )


def test_a_root_module_is_a_leaf(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "helpers.py",
        "import app.domain.thing\nimport enum\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("helpers belongs to no governed package" in f for f in findings)
    assert any(
        "helpers imports app.domain.thing; "
        "a root module is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("helpers imports enum" in f for f in findings)


def test_a_context_main_is_a_stray_module(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/__main__.py",
        "import app.application.service as service\nimport app.wiring.wire as wire\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.__main__ is not a context module; a context holds only domain, "
        "application, client, adapters, wiring, and tests modules" in f
        for f in findings
    )
    assert not any("__main__ composes from" in f for f in findings)


def test_a_protocol_module_imports_nothing_else_from_its_tree(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "serialization.py", "X = 1\n")
    conftest.write_module(
        tmp_path,
        "protocol/http.py",
        "import tesser.srv as ts\nimport serialization\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "protocol.http imports serialization; "
        "a protocol module imports nothing else from its tree" in f
        for f in findings
    )


def test_a_context_role_reaches_the_app_shell_only_as_handlers_to_protocol(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "protocol/http.py",
        "import tesser.srv as ts\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/handlers.py",
        "import tesser.adapters as ts\n"
        "import protocol.http as http\n"
        "import srv.http as host\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/wiring/wire.py",
        "import tesser.context as ts\n"
        "import protocol.http as http\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import protocol.http as http\n"
        "class PeerGateway(ts.Gateway):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/handlers_support.py",
        "import tesser.adapters as ts\n"
        "import protocol.http as http\n",
    )
    conftest.write_module(tmp_path, "app/adapters/repositories/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/adapters/repositories/smuggle.py",
        "import tesser.adapters as ts\n"
        "import protocol.http as http\n"
        "class SmuggleHandler(ts.Handler):\n"
        "    pass\n",
    )
    conftest.write_module(tmp_path, "srv/http.py", "")
    findings = conftest.check_tree(tmp_path)
    clause = "of the app shell a context imports only protocol, and only from its handlers"
    assert any(
        "app.adapters.handlers imports srv.http; "
        "of the app shell a context imports only protocol, and only from its handlers" in f
        for f in findings
    )
    assert not any("app.adapters.handlers imports protocol.http" in f for f in findings)
    assert any(f"app.wiring.wire imports protocol.http; {clause}" in f for f in findings)
    assert any(
        f"app.adapters.gateways imports protocol.http; {clause}" in f for f in findings
    ), f"a gateway imported protocol without a finding: {findings}"
    assert any(
        f"app.adapters.handlers_support imports protocol.http; {clause}" in f
        for f in findings
    ), f"a handlers-adjacent name bought the grant without the placement: {findings}"
    assert any(
        f"app.adapters.repositories.smuggle imports protocol.http; {clause}" in f
        for f in findings
    ), f"a Handler class declared outside handlers/ bought the grant: {findings}"


def test_a_classless_module_inside_handlers_may_speak_protocol(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "protocol/http.py", "import tesser.srv as ts\n")
    conftest.write_module(tmp_path, "app/adapters/handlers/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/adapters/handlers/usage.py",
        "import tesser.adapters as ts\n"
        "import protocol.http as http\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any(
        "app.adapters.handlers.usage imports protocol.http" in f for f in findings
    ), f"a helper module inside handlers/ was denied protocol: {findings}"


def test_production_never_imports_the_tests_package(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "tests/test_ok.py",
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/http.py",
        "import tests.test_ok\n",
    )
    conftest.write_module(
        tmp_path,
        "bootstrap/wire.py",
        "import protocol.http\nimport tests.test_ok\n",
    )
    conftest.write_module(
        tmp_path,
        "protocol/http.py",
        "import tesser.srv as ts\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "srv.http imports tests.test_ok; "
        "production code never imports the tests package" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire imports tests.test_ok; "
        "production code never imports the tests package" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire imports protocol.http; "
        "bootstrap composes the application and never imports protocol" in f
        for f in findings
    )


def test_a_root_test_reaches_a_context_only_through_wiring_and_client(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/wiring/wire.py",
        "import tesser.context as ts\n",
    )
    conftest.write_module(
        tmp_path,
        "tests/test_app.py",
        "import app.client.client as client\n"
        "import app.wiring.wire as wire\n"
        "import app.domain.thing as thing\n"
        "import app.application.service as service\n"
        "import bootstrap.wire\n"
        "import tests.support\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(tmp_path, "tests/support.py", "import app.domain.thing as thing\n")
    conftest.write_module(tmp_path, "bootstrap/wire.py", "")
    findings = conftest.check_tree(tmp_path)
    reach = (
        "reaches a context only through its wiring and client; "
        "a test reaches only what its placement allows"
    )
    assert any(
        "tests.test_app imports app.domain.thing, but a test placed in "
        "the root tests package reaches a context only through its wiring and client; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "tests.test_app imports app.application.service" in f and reach in f for f in findings
    )
    assert not any("tests.test_app imports app.client.client" in f for f in findings)
    assert not any("tests.test_app imports app.wiring.wire" in f for f in findings)
    assert not any("tests.test_app imports bootstrap.wire" in f for f in findings)
    assert not any("tests.test_app imports tests.support" in f for f in findings)
    assert any(
        "tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        f"tests.support imports app.domain.thing, but a test placed in the root tests package {reach}" in f
        for f in findings
    )


def test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/test_thing.py",
        "import srv.http\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "srv/test_host.py",
        "import bootstrap.wire\n"
        "import tests.test_root\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "tests/test_root.py",
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "bootstrap/test_wire.py",
        "import srv.http\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(tmp_path, "srv/http.py", "")
    conftest.write_module(tmp_path, "bootstrap/wire.py", "")
    findings = conftest.check_tree(tmp_path)
    clause = "does not reach that package; a test reaches only what its placement allows"
    assert any(
        "app.domain.test_thing imports srv.http, but a test placed in domain "
        "does not reach that package; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("srv.test_host imports bootstrap.wire" in f for f in findings)
    assert any(
        "srv.test_host imports tests.test_root, but a test placed in srv "
        "does not reach that package" in f
        for f in findings
    )
    assert any(
        f"bootstrap.test_wire imports srv.http, but a test placed in bootstrap {clause}" in f
        for f in findings
    )


def test_a_context_tests_module_reaches_its_own_tests_package(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/tests/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/tests/test_thing.py",
        "import app.tests.conftest as helpers\n"
        "import two.tests.test_two as foreign\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(tmp_path, "app/tests/conftest.py", "")
    conftest.write_module(tmp_path, "two/client/client.py", "import tesser.context as ts\n")
    conftest.write_module(tmp_path, "two/tests/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "two/tests/test_two.py",
        "def test_ok() -> None:\n    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app.tests.test_thing imports app.tests.conftest" in f for f in findings)
    assert any(
        "app.tests.test_thing imports two.tests.test_two, but a test placed in tests "
        "reaches only application, client of a neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_an_unplaced_test_module_is_still_governed(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "weird/test_nested.py",
        "import app.domain.thing as thing\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "test_solo.py",
        "def test_ok() -> None:\n    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "weird.test_nested resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )
    assert any("test_solo resolves to no test tier" in f for f in findings)


def test_a_conftest_off_the_tier_map_is_a_leaf(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/adapters/conftest.py",
        "import os\nimport app.domain.thing\n",
    )
    conftest.write_module(
        tmp_path,
        "app/conftest.py",
        "import app.domain.thing\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert any(
        "app.conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("app.adapters.conftest resolves to no test tier" in f for f in findings)
    assert not any("app.adapters.conftest imports os" in f for f in findings)


def test_adapter_kind_and_protocol_tests_shell_reach(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "protocol/http.py", "import tesser.srv as ts\n")
    conftest.write_module(tmp_path, "srv/http.py", "")
    for kind in ("handlers", "gateways", "repositories"):
        conftest.write_module(tmp_path, f"app/adapters/{kind}/__init__.py", "")
        conftest.write_module(
            tmp_path,
            f"app/adapters/{kind}/test_{kind}.py",
            "import protocol.http as http\n"
            "import srv.http\n"
            "def test_ok() -> None:\n    assert True\n",
        )
    conftest.write_module(
        tmp_path,
        "protocol/test_http.py",
        "import protocol.http as http\n"
        "import srv.http\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any(
        "app.adapters.handlers.test_handlers imports protocol.http" in f
        for f in findings
    ), f"a handlers-tier test was denied protocol: {findings}"
    for kind in ("gateways", "repositories"):
        assert any(
            f"app.adapters.{kind}.test_{kind} imports protocol.http" in f
            and "does not reach that package" in f
            for f in findings
        ), f"a {kind} test reached protocol; only srv and handlers speak protocol: {findings}"
    for kind in ("handlers", "gateways", "repositories"):
        assert any(
            f"app.adapters.{kind}.test_{kind} imports srv.http" in f
            and "does not reach that package; "
            "a test reaches only what its placement allows" in f
            for f in findings
        )
    assert not any("protocol.test_http imports protocol.http" in f for f in findings)
    assert any(
        "protocol.test_http imports srv.http, but a test placed in protocol "
        "does not reach that package" in f
        for f in findings
    )


def test_an_eval_in_a_gateway_reaches_no_shell_package(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "protocol/http.py", "import tesser.srv as ts\n")
    conftest.write_module(tmp_path, "srv/http.py", "")
    conftest.write_module(tmp_path, "app/adapters/gateways/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/eval_model.py",
        "import protocol.http as http\n"
        "import srv.http\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways.eval_model imports protocol.http" in f
        and "does not reach that package" in f
        for f in findings
    ), f"a gateway eval reached protocol; only srv and handlers speak protocol: {findings}"
    assert any(
        "app.adapters.gateways.eval_model imports srv.http, but a test placed in gateways "
        "does not reach that package" in f
        for f in findings
    )


def test_a_context_tests_helper_answers_for_its_imports(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/tests/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/tests/support.py",
        "import app.domain.thing as thing\nimport srv.http\n",
    )
    conftest.write_module(tmp_path, "srv/http.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        "app.tests.support imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )
    assert not any("app.tests.support imports app.domain.thing" in f for f in findings)


def test_a_main_below_the_context_root_is_a_governed_module(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/__main__.py",
        "import app.application.service as service\n",
    )
    conftest.write_module(tmp_path, "app/tests/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/tests/__main__.py",
        "import app.application.service as service\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.domain.__main__ imports app.application.service; the same-context matrix is" in f
        for f in findings
    )
    assert any(
        "app.tests.__main__ is neither a test module nor conftest" in f for f in findings
    )


def test_a_shell_name_missing_from_the_tree_is_not_the_shell(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/domain/test_thing.py",
        "import protocol.thirdparty\n"
        "def test_ok() -> None:\n    assert True\n",
    )
    conftest.write_module(
        tmp_path,
        "app/wiring/wire.py",
        "import tesser.context as ts\nimport bootstrap\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app.domain.test_thing imports protocol.thirdparty" in f for f in findings)
    assert not any("app.wiring.wire imports bootstrap" in f for f in findings)


def test_a_vendored_tesser_package_is_not_the_tree(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "tesser/testing.py", "X = 1\n")
    conftest.write_module(tmp_path, "conftest.py", "import tesser.testing\n")
    findings = conftest.check_tree(tmp_path)
    assert not any(
        "conftest imports tesser.testing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )


def test_every_test_tier_has_a_shell_row() -> None:
    tiers = (
        set(domain.TEST_TIER_REACH)
        | {domain.SRV_TIER, domain.BOOTSTRAP_TIER, domain.PROTOCOL_TIER, domain.APP_TIER}
    )
    assert tiers <= set(domain.TEST_TIER_SHELL)


def test_ports_is_a_package_never_a_module(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/application/ports.py",
        "import tesser.application as ts\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports is a ports module; ports is a package, never a module" in f
        for f in findings
    )


def test_a_ports_init_is_empty(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "X = 1\n")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports __init__ declares code; a ports __init__ is empty" in f
        for f in findings
    )


def test_a_ports_module_is_a_leaf(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/other.py",
        "import tesser.application as ts\n"
        "class OtherSink(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "import app.domain.thing as thing\n"
        "import app.application.ports.other as other\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink imports app.domain.thing; a ports module is a leaf "
        "and imports nothing from its tree, its own siblings included" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink imports app.application.ports.other; a ports module is a leaf "
        "and imports nothing from its tree, its own siblings included" in f
        for f in findings
    )


def test_a_ports_module_stdlib_allowlist(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import enum\n"
        "import socket\n"
        "import tesser.application as ts\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink imports socket; a ports module imports "
        "only tesser.application and the pure stdlib" in f
        for f in findings
    )
    assert not any("imports enum;" in f for f in findings)


def test_a_ports_module_tesser_import_rules(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.domain as ts\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/ports/plain.py",
        "import tesser.application\n"
        "class Plain(tesser.application.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink imports tesser.domain; "
        "a ports module imports only tesser.application" in f
        for f in findings
    )
    assert any(
        "a ports module imports tesser.application exactly once, as ts" in f for f in findings
    )


def test_a_ports_module_holds_only_imports_and_classes(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "FOUND = 'found'\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink has a loose module-level statement; "
        "a ports module holds only imports and classes" in f
        for f in findings
    )


def test_a_ports_module_declares_exactly_one_port(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/two.py",
        "import tesser.application as ts\n"
        "class First(ts.Port):\n"
        "    pass\n"
        "class Second(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/ports/none.py",
        "import tesser.application as ts\n"
        "class Stray(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.two declares 2 ports; a ports module "
        "declares exactly one port, so no two ports can share a request or a response" in f
        for f in findings
    )
    assert any(
        "app.application.ports.none declares no port; a ports module "
        "declares exactly one port, so no two ports can share a request or a response" in f
        for f in findings
    )


def test_a_ports_module_holds_only_port_kinds(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "class Bare:\n"
        "    pass\n"
        "class Leaked(ts.ApplicationService):\n"
        "    pass\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Bare declares no ts.* base; a ports class declares its block" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink.Leaked is a service; only a port and the requests "
        "and responses it speaks live in a ports module" in f
        for f in findings
    )


def test_a_port_method_speaks_one_request_and_one_response(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port):\n"
        "    def save(self, text: str) -> SaveResponse: ...\n"
        "    def load(self, request: SaveRequest) -> str: ...\n"
        "    def both(self, request: SaveRequest, extra: str) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink.save parameter 'text' is not a ts.Request; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink.Sink.load does not return a ts.Response; "
        "a port method returns a ts.Response" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink.Sink.both takes 2 parameters; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    )


def test_an_adapter_reaches_application_only_through_ports(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/memory.py",
        "import tesser.adapters as ts\n"
        "import app.application.ports.sink as sink\n"
        "import app.application.service as service\n"
        "class MemorySink(ts.Repository):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways.memory imports app.application.service; "
        "the same-context matrix is a role to itself, application to domain and client, "
        "adapters to application/ports, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert not any("imports app.application.ports.sink;" in f for f in findings)


def test_a_port_dto_field_is_never_a_union(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class ItemView(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class FindResponse(ts.Response):\n"
        "    def __init__(self, item: ItemView | None) -> None:\n"
        "        self.item = item\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.FindResponse.__init__ field 'item' is a union; "
        "a port DTO field is never a union, optional included — model the outcome as an enum" in f
        for f in findings
    )


def test_a_client_dto_field_may_still_be_optional(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/client/optional.py",
        "from __future__ import annotations\n"
        "import tesser.context as ts\n"
        "class Inner(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Outer(ts.Response):\n"
        "    def __init__(self, inner: Inner | None) -> None:\n"
        "        self.inner = inner\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app.client.optional" in f and "is a union" in f for f in findings)


def test_a_conforming_ports_module_is_silent(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class Outcome(enum.Enum):\n"
        "    STORED = 'stored'\n"
        "    REFUSED = 'refused'\n"
        "class ItemView(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self, outcome: Outcome, items: tuple[ItemView, ...]) -> None:\n"
        "        self.outcome = outcome\n"
        "        self.items = items\n"
        "class ListRequest(ts.Request):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def save(self, request: SaveRequest) -> SaveResponse: ...\n"
        "    def all(self, request: ListRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("app/application/ports/sink.py" in f for f in findings), (
        f"a conforming ports module produced findings: "
        f"{[f for f in findings if 'ports/sink.py' in f]}"
    )


def test_a_ports_package_holds_only_ports_modules(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/ports/test_support.py",
        "import tesser.testing as ts\n"
        "import app.application.ports.sink as sink\n"
        "@ts.fake\n"
        "class Lookup(sink.Sink):\n"
        "    pass\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    conftest.write_module(tmp_path, "app/application/ports/conftest.py", "")
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.test_support is not a ports module; a ports package holds "
        "only ports modules, and test_/eval_/conftest are reserved names, because a fake "
        "here would be an implementation adapters may import" in f
        for f in findings
    ), f"a fake could live in the package adapters may import: {findings}"
    assert any("app.application.ports.conftest is not a ports module" in f for f in findings)


def test_a_client_dto_with_a_sibling_enum_stays_strict(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/client/verdict.py",
        "from __future__ import annotations\n"
        "import tesser.context as ts\n"
        "class Verdict:\n"
        "    pass\n"
        "class VerdictResponse(ts.Response):\n"
        "    def __init__(self, verdict: Verdict) -> None:\n"
        "        self.verdict = verdict\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.client.verdict.VerdictResponse.__init__ parameter 'verdict' is not allowed; "
        "a DTO field is a primitive or another DTO" in f
        for f in findings
    )


def test_a_port_dto_field_is_never_a_bare_bool(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "import tesser.application as ts\n"
        "class Outcome(enum.Enum):\n"
        "    YES = 'yes'\n"
        "    NO = 'no'\n"
        "class FlagResponse(ts.Response):\n"
        "    def __init__(self, found: bool, outcome: Outcome) -> None:\n"
        "        self.found = found\n"
        "        self.outcome = outcome\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.FlagResponse.__init__ field 'found' is a bool; "
        "a port DTO field is never a bare bool — model the outcome as an enum" in f
        for f in findings
    )
    assert not any("'outcome'" in f for f in findings)


def test_a_port_dto_is_never_subclassed(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class FindResponse(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class FoundItem(FindResponse):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.FoundItem subclasses a port DTO; a port DTO is never "
        "subclassed, because a response hierarchy is a union mypy cannot check for exhaustiveness" in f
        for f in findings
    )


def test_a_port_method_shape_survives_async_and_dunder_call(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class Sink(ts.Port):\n"
        "    async def fetch(self, name: str, count: int) -> bool: ...\n"
        "    def __call__(self, name: str) -> bool: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink.fetch takes 2 parameters; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    ), f"async def bypassed the port shape rule: {findings}"
    assert any(
        "app.application.ports.sink.Sink.__call__ parameter 'name' is not a ts.Request" in f
        for f in findings
    ), f"__call__ bypassed the port shape rule: {findings}"


def test_a_fake_implementing_a_port_may_expose_inspection_methods(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/test_sink.py",
        "import tesser.testing as ts\n"
        "import app.application.ports.sink as sink\n"
        "@ts.fake\n"
        "class FakeSink(sink.Sink):\n"
        "    def __init__(self) -> None:\n"
        "        self.saves = 0\n"
        "    def save(self, request: sink.SaveRequest) -> sink.SaveResponse:\n"
        "        self.saves = self.saves + 1\n"
        "        return sink.SaveResponse()\n"
        "    def save_count(self) -> int:\n"
        "        return self.saves\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("save_count" in f for f in findings), (
        f"a fake's inspection method was flagged as a port method: "
        f"{[f for f in findings if 'save_count' in f]}"
    )


def test_a_ports_enum_is_a_plain_enum(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "import tesser.application as ts\n"
        "class Loose(enum.StrEnum):\n"
        "    YES = 'yes'\n"
        "class Tight(enum.Enum):\n"
        "    YES = 'yes'\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Loose is an enum.StrEnum; a ports enum is an enum.Enum, "
        "because a str- or int-backed member compares equal to a raw literal "
        "and reopens the typo the enum closes" in f
        for f in findings
    )
    assert not any("Tight" in f for f in findings)


def test_a_port_method_declares_a_shape_and_never_a_body(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def save(self, request: SaveRequest) -> SaveResponse:\n"
        "        return SaveResponse()\n"
        "    def drop(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink.save carries a body; a port method declares a shape "
        "and never a body, because a ports module holds no logic to import" in f
        for f in findings
    )
    assert not any("Sink.drop" in f for f in findings)


def test_an_ignored_ports_file_is_still_governed(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/application/ports.py",
        "import subprocess  # tessercheck:ignore TB067\n"
        "import tesser.application as ts  # tessercheck:ignore-file TB041\n"
        "import app.domain.thing as thing\n"
        "class First(ts.Port):\n"
        "    pass\n"
        "class Second(ts.Port):\n"
        "    pass\n"
        "class Leaked(ts.ApplicationService):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports imports app.domain.thing; a ports module is a leaf" in f
        for f in findings
    ), f"an ignored TB041 unlocked the module: {findings}"
    assert any("declares 2 ports" in f for f in findings)
    assert any("app.application.ports.Leaked is a service" in f for f in findings)


def test_an_enum_base_cannot_hide_a_second_port(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "import tesser.application as ts\n"
        "class First(ts.Port):\n"
        "    pass\n"
        "class Second(ts.Port, enum.auto):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any("declares 2 ports" in f for f in findings), (
        f"an enum base hid a second port, so two ports could share every DTO: {findings}"
    )


def test_an_enum_is_resolved_by_its_binding_not_its_spelling(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/masked.py",
        "from __future__ import annotations\n"
        "import typing as enum\n"
        "import tesser.application as ts\n"
        "class Rules(enum.Any):\n"
        "    pass\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/ports/aliased.py",
        "from __future__ import annotations\n"
        "import enum as e\n"
        "import tesser.application as ts\n"
        "class Outcome(e.Enum):\n"
        "    YES = 'yes'\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.masked.Rules declares no ts.* base" in f for f in findings
    ), f"a name bound to something else was accepted as an enum: {findings}"
    assert not any("aliased.Outcome" in f for f in findings), (
        f"a properly bound enum alias was rejected: {findings}"
    )


def test_a_dynamic_import_is_not_a_way_around_the_matrix(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/memory.py",
        "import importlib\n"
        "import tesser.adapters as ts\n"
        "import app.application.ports.sink as sink\n"
        "class MemorySink(ts.Repository):\n"
        "    def __init__(self) -> None:\n"
        "        self._service = importlib.import_module('app.application.service')\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways.memory imports dynamically through importlib.import_module; "
        "an import is a statement the walk can read, never a call" in f
        for f in findings
    ), f"importlib walked around the import matrix: {findings}"


def test_a_dto_declares_its_fields_where_the_rules_can_read_them(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class ClassLevel(ts.Response):\n"
        "    flag = False\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Splatted(ts.Response):\n"
        "    def __init__(self, **fields: object) -> None:\n"
        "        self.fields = fields\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.ClassLevel carries a class-level statement; a port DTO "
        "declares its fields as __init__ parameters, where the field rules can read them" in f
        for f in findings
    ), f"a class-level bool field walked around the bare-bool rule: {findings}"
    assert any(
        "app.application.ports.sink.Splatted.__init__ uses *args/**kwargs; a DTO declares "
        "its fields as named __init__ parameters, where the field rules can read them" in f
        for f in findings
    ), f"**kwargs walked around every DTO field rule: {findings}"


def test_an_async_method_on_a_dto_is_still_a_method(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class Loaded(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "    async def resolve(self) -> str:\n"
        "        return self.id\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Loaded.resolve defines a method on a DTO; "
        "a DTO carries data and nothing else" in f
        for f in findings
    ), f"async def carried logic onto a DTO: {findings}"


def test_a_nested_class_cannot_hide_a_second_port(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class First(ts.Port):\n"
        "    pass\n"
        "class Holder(ts.Response):\n"
        "    class Second(ts.Port):\n"
        "        pass\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Holder.Second is a nested class; a ports module declares "
        "its port and its DTOs at module level, where the one-port count can see them" in f
        for f in findings
    ), f"a nested class hid a second port sharing every DTO: {findings}"


def test_a_dynamic_import_is_resolved_by_binding_not_spelling(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/memory.py",
        "from importlib import import_module\n"
        "import tesser.adapters as ts\n"
        "import app.application.ports.sink as sink\n"
        "class MemorySink(ts.Repository):\n"
        "    def __init__(self) -> None:\n"
        "        self._service = import_module('app.application.service')\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/local.py",
        "import tesser.adapters as ts\n"
        "import app.application.ports.sink as sink\n"
        "class LocalSink(ts.Repository):\n"
        "    def __init__(self, importlib: object) -> None:\n"
        "        self._loader = importlib\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.adapters.gateways.memory imports dynamically through importlib.import_module" in f
        for f in findings
    ), f"a from-import of import_module walked around TB068: {findings}"
    assert not any("local" in f and "TB068" in f for f in findings), (
        f"a local name spelled importlib false-positived: {findings}"
    )


def test_a_port_speaks_shapes_it_declares_itself(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def bare(self, request: ts.Request) -> ts.Response: ...\n"
        "    def own(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink.bare names a shape it does not declare; a port "
        "method speaks requests and responses declared in its own ports module, never a "
        "bare ts.Request or ts.Response, which two ports would share" in f
        for f in findings
    ), f"two ports could share the base classes as their whole vocabulary: {findings}"
    assert not any("Sink.own" in f for f in findings)


def test_a_ports_class_carries_no_class_level_statement(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class Outcome(enum.Enum):\n"
        "    YES = 'yes'\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    RESERVED = tuple(sorted({'admin'}))\n"
        "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink carries a class-level statement; only an enum "
        "member is class-level data in a ports module, because anything else runs at "
        "import in the one application module adapters may import" in f
        for f in findings
    ), f"import-time execution landed in the ports leaf: {findings}"
    assert not any("Outcome" in f for f in findings), f"an enum member was flagged: {findings}"


def test_a_private_port_method_carries_no_body(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def _score(self, name: str) -> int:\n"
        "        return len(name)\n"
        "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink._score carries a body; a port method declares a "
        "shape and never a body" in f
        for f in findings
    ), f"a private method carried logic every implementer inherits: {findings}"


def test_a_stub_cannot_shadow_the_shape_the_rules_read(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
    )
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.pyi",
        "import tesser.application as ts\n"
        "class Loose(ts.Response):\n"
        "    allowed: bool\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink is a stub; a module carries its own shape, because a "
        "stub is what the type checker reads and the walk cannot" in f
        for f in findings
    ), f"a stub bypassed every ports rule at the type level: {findings}"


def test_a_ports_enum_carries_nothing_but_its_members(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "import tesser.application as ts\n"
        "class Outcome(enum.Enum):\n"
        "    FOUND = 'found'\n"
        "    NEXT = enum.auto()\n"
        "    def normalise(self, raw: str) -> str:\n"
        "        return raw.strip().lower()\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Outcome carries more than its members; a ports enum "
        "is a closed set of names and nothing else, because a method or a decorator here "
        "is logic every adapter imports" in f
        for f in findings
    ), f"an enum smuggled logic into the ports leaf: {findings}"
    assert not any("FOUND" in f or "NEXT" in f for f in findings)


def test_a_port_dto_constructor_only_assigns_its_parameters(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class Validating(ts.Response):\n"
        "    def __init__(self, id: str, name: str) -> None:\n"
        "        if not id:\n"
        "            raise ValueError('empty id')\n"
        "        self.id = id\n"
        "        self.name = name.strip()\n"
        "class Plain(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Empty(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Validating.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters, because a ports module holds no "
        "logic to import" in f
        for f in findings
    ), f"domain validation lived in the ports leaf: {findings}"
    assert not any("Plain" in f or "Empty" in f for f in findings)


def test_a_port_declares_only_the_calls_an_implementer_provides(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def _raw(self, sql: str, limit: int, flag: bool) -> tuple[str, ...]: ...\n"
        "    def __enter__(self) -> str: ...\n"
        "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink._raw is not a call an implementer provides; "
        "a port declares only its public calls and __call__, because a private name is "
        "not private to anyone implementing or holding the port" in f
        for f in findings
    ), f"an underscore prefix bought a rule-free port method: {findings}"
    assert any("Sink.__enter__ is not a call an implementer provides" in f for f in findings)
    assert not any("Sink.save" in f for f in findings)


def test_a_ports_module_runs_nothing_at_import(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "import tesser.application as ts\n"
        "@enum.unique\n"
        "class Decorated(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Defaulted(ts.Response):\n"
        "    def __init__(self, id: str = str(enum.Enum)) -> None:\n"
        "        self.id = id\n"
        "class Generic[T](ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Computed(ts.Response, str(enum.Enum)):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id: str = id\n"
        "class Plain(ts.Response):\n"
        "    def __init__(self, id: str = 'none') -> None:\n"
        "        self.id = id\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Decorated is decorated; a ports module holds no "
        "decorator, because a decorator is a call that runs at import in the one "
        "application module adapters may import" in f
        for f in findings
    ), f"a decorator ran arbitrary code at import of the ports leaf: {findings}"
    assert any(
        "app.application.ports.sink.Defaulted.__init__ carries a computed default; a ports "
        "module holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"a default parameter expression ran at import: {findings}"
    assert any(
        "app.application.ports.sink.Computed computes a base; a ports module holds no "
        "expression that runs at import, and a base built by a call is logic every "
        "adapter imports" in f
        for f in findings
    ), f"a computed base ran at import: {findings}"
    assert any(
        "app.application.ports.sink.Generic is generic; a ports module names concrete "
        "shapes, because a type parameter is a slot the shape rules cannot read and a "
        "bound is an expression" in f
        for f in findings
    ), f"a generic port DTO went ungoverned: {findings}"
    assert not any("Plain" in f for f in findings)
    assert not any("Computed.__init__ carries logic" in f for f in findings), (
        f"an annotated self-assignment was rejected: {findings}"
    )


def test_an_async_port_method_runs_nothing_at_import(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    async def audit(self, request: SaveRequest = SaveRequest(id=open('x').read())) "
        "-> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Sink.audit carries a computed default; a ports module "
        "holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"an async def default expression ran at import: {findings}"


def test_a_port_dto_binds_only_its_own_parameters(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class Capability(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "        self.reach = __import__\n"
        "class Plain(ts.Response):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self._id = id\n"
        "        self.also = id\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Capability.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters" in f
        for f in findings
    ), f"a DTO bound a live capability an adapter could call: {findings}"
    assert not any("Plain" in f for f in findings)


def test_a_ports_class_carries_no_keyword(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import tesser.application as ts\n"
        "class Meta(ts.Response, metaclass=type):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.Meta carries a class keyword; a ports module holds no "
        "expression that runs at import, and a metaclass is logic every adapter imports" in f
        for f in findings
    ), f"a metaclass ran logic at import of the ports leaf: {findings}"


def test_an_enum_member_may_be_negative_or_annotated(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from __future__ import annotations\n"
        "import enum\n"
        "import tesser.application as ts\n"
        "class Outcome(enum.Enum):\n"
        "    UNKNOWN = -1\n"
        "    ALLOWED: int = 1\n"
        "    NEXT = enum.auto()\n"
        "    __doc__ = 'the verdict'\n"
        "class Sink(ts.Port):\n"
        "    pass\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert not any("UNKNOWN" in f or "ALLOWED" in f or "NEXT" in f for f in findings), (
        f"a legitimate enum member was rejected: {findings}"
    )
    assert any(
        "app.application.ports.sink.Outcome carries more than its members" in f
        for f in findings
    ), f"a dunder assignment laundered prose past the comments norm: {findings}"


def test_async_def_is_not_a_way_around_a_method_rule(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(
        tmp_path,
        "app/client/async_client.py",
        "from __future__ import annotations\n"
        "from typing import Protocol\n"
        "import tesser.context as ts\n"
        "class Ask(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class Loose(ts.Client, Protocol):\n"
        "    async def ask(self, id: str, extra: int) -> str: ...\n",
    )
    conftest.write_module(
        tmp_path,
        "app/adapters/gateways/async_repo.py",
        "from __future__ import annotations\n"
        "import tesser.adapters as ts\n"
        "import app.domain.thing as thing\n"
        "class Loose(ts.Repository):\n"
        "    async def save(self, entity: thing.Thing) -> None: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.client.async_client.Loose.ask" in f and "a client method takes exactly one" in f
        for f in findings
    ), f"an async client method escaped the client shape rule: {findings}"
    assert any(
        "app.adapters.gateways.async_repo.Loose.save carries an aggregate in its signature" in f
        for f in findings
    ), f"an async adapter method escaped the record rule: {findings}"


def test_a_ports_module_computes_no_annotation(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from typing import Annotated, Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> Annotated[None, open('x').read()]:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def save[T](self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.SaveRequest.__init__ computes an annotation; a ports "
        "module holds no expression that runs at import, and an annotation is evaluated "
        "like any other" in f
        for f in findings
    ), f"an annotation ran code at import of the ports leaf: {findings}"
    assert any(
        "app.application.ports.sink.Sink.save is generic" in f for f in findings
    ), f"a generic port method went ungoverned: {findings}"


def test_every_spelling_of_a_dynamic_import_is_a_finding(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
    )
    for name, body in (
        ("rebound", "import importlib\n_load = importlib.import_module\n"),
        ("indirect", "import importlib\n"),
        ("builtin", "import builtins\n"),
        ("registry", "import sys\n"),
    ):
        conftest.write_module(
            tmp_path,
            f"app/adapters/gateways/{name}.py",
            body
            + "import tesser.adapters as ts\n"
            + "import app.application.ports.sink as sink\n"
            + f"class Reach{name.title()}(ts.Repository):\n"
            + "    def __init__(self) -> None:\n"
            + {
                "rebound": "        self.svc = _load('app.application.service')\n",
                "indirect": "        self.svc = getattr(importlib, 'import_module')"
                "('app.application.service')\n",
                "builtin": "        self.svc = builtins.__import__('app.application.service')\n",
                "registry": "        self.svc = sys.modules['app.application.service']\n",
            }[name],
        )
    findings = conftest.check_tree(tmp_path)
    for name in ("rebound", "indirect", "builtin", "registry"):
        assert any(f"app.adapters.gateways.{name} imports dynamically" in f for f in findings), (
            f"the {name} spelling reached application with no import edge: {findings}"
        )


def test_a_ports_module_holds_only_shapes_the_rules_can_read(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "app/application/ports/__init__.py", "")
    conftest.write_module(
        tmp_path,
        "app/application/ports/sink.py",
        "from typing import Annotated, Protocol\n"
        "import tesser.application as ts\n"
        "class SaveRequest(ts.Request):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "        del id\n"
        "class Header(ts.Response, tuple[Annotated[int, 1 if True else 2], ...]):\n"
        "    def __init__(self, id: str) -> None:\n"
        "        self.id = id\n"
        "class SaveResponse(ts.Response):\n"
        "    def __init__(self) -> None:\n"
        "        return None\n"
        "class Sink(ts.Port, Protocol):\n"
        "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
    )
    findings = conftest.check_tree(tmp_path)
    assert any(
        "app.application.ports.sink.SaveRequest.__init__ holds a Delete; a ports module "
        "holds only the shapes its rules can read, so anything else is a finding by "
        "default rather than a gap nobody enumerated" in f
        for f in findings
    ), f"a statement kind nobody enumerated passed silently: {findings}"
    assert any(
        "app.application.ports.sink.Header holds a Subscript" in f for f in findings
    ), f"an expression in a class base ran at import: {findings}"


def test_an_undeclared_tree_is_a_finding_and_nothing_else_is(tmp_path: Path) -> None:
    conftest.write_module(tmp_path, "stray.py", "import os\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "this tree is not declared; a checkable tree carries a .tesser-root file "
        "containing 'app' at its root" in f
        for f in findings
    ), f"an undeclared tree was walked as if declared: {findings}"


def test_an_unrecognized_declaration_is_a_finding(tmp_path: Path) -> None:
    conftest.write_module(tmp_path, "stray.py", "import os\n")
    (tmp_path / ".tesser-root").write_text("domain\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "this tree declares an unrecognized kind; a declaration is "
        "'app', then only 'skip <dir>' lines" in f
        for f in findings
    ), f"an unrecognized declaration passed: {findings}"


def test_an_unknown_directive_is_an_unrecognized_kind(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nignore stuff\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "unrecognized kind" in findings[0], findings


def test_an_unreadable_declaration_is_a_finding(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_bytes(b"\xff\xfe\x00app")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "this tree's declaration is not readable; "
        "a .tesser-root is a plain UTF-8 text file" in f
        for f in findings
    ), f"an undecodable declaration passed: {findings}"


def test_a_declaration_that_is_a_directory_is_unreadable(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").mkdir()
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "not readable" in findings[0], findings


def test_a_bom_prefixed_declaration_still_reads(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".tesser-root").write_bytes(b"\xef\xbb\xbfapp\n")
    assert conftest.check_raw(tmp_path) == ()


def test_a_nested_declaration_is_a_finding_and_masks_the_walk(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "stray.py", "import os\n")
    (tmp_path / "app" / ".tesser-root").write_text("app\n")
    findings = conftest.check_tree(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "declares a nested tree root; a tessercheck run covers one declared tree, "
        "so run that tree directly" in f
        for f in findings
    ), f"a nested declaration passed: {findings}"


def test_a_skipped_dir_hides_no_nested_declaration(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / ".tesser-root").write_text("app\n")
    assert conftest.check_tree(tmp_path) == ()


def test_a_declared_skip_dir_is_not_walked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".tesser-root").write_text("app\nskip fixtures\n")
    conftest.write_module(tmp_path, "fixtures/bad.py", "def f(:\n")
    assert conftest.check_raw(tmp_path) == ()


def test_a_symlinked_directory_is_a_finding(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "bad.py").write_text("def f(:\n")
    (tmp_path / "vendored").symlink_to(outside)
    findings = conftest.check_tree(tmp_path)
    assert len(findings) == 1, findings
    assert any(
        "vendored:1: TB045 is a symlinked directory; a declared tree is walked in "
        "full, and a symlink escapes the walk" in f
        for f in findings
    ), f"a symlinked directory escaped the walk silently: {findings}"


def test_a_declaration_finding_is_never_inline_suppressible(tmp_path: Path) -> None:
    conftest.write_module(
        tmp_path, "stray.py", "import os  # tessercheck:ignore TB044\n"
    )
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "TB044" in findings[0], findings


def test_a_bare_skip_directive_is_an_unrecognized_kind(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "unrecognized kind" in findings[0], findings


def test_a_skip_directive_with_a_path_is_an_unrecognized_kind(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\nskip a/b\n")
    findings = conftest.check_raw(tmp_path)
    assert len(findings) == 1, findings
    assert "unrecognized kind" in findings[0], findings


def test_an_undeclared_testdata_dir_is_walked(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    conftest.write_module(tmp_path, "testdata/stray.py", "import os\n")
    findings = conftest.check_tree(tmp_path)
    assert any("TB040" in f and "testdata.stray" in f for f in findings), findings


def test_a_declared_skip_applies_at_any_depth(tmp_path: Path) -> None:
    conftest.conforming_tree(tmp_path)
    (tmp_path / ".tesser-root").write_text("app\nskip fixtures\n")
    conftest.write_module(tmp_path, "app/domain/fixtures/bad.py", "def f(:\n")
    assert conftest.check_raw(tmp_path) == ()
