from pathlib import Path

import pytest

import tessercheck.domain.checks as domain
from tests.conftest import check_tree, conforming_tree, write_module

def test_every_declared_block_has_a_name_and_a_home() -> None:
    blocks = set(domain.TESSER_BASE_BLOCKS.values())
    assert set(domain.KIND_NAME) == blocks
    assert set(domain.KIND_ROLE) == blocks - domain.SRV_KINDS

def test_every_kind_row_names_a_real_tesser_export() -> None:
    root = Path(__file__).resolve().parents[2] / "tesser-py"
    rows = list(domain.TESSER_BASE_BLOCKS) + list(domain.TESSER_DECORATORS)
    for package, name in rows:
        exports = (root / package.replace(".", "/") / "__init__.py").read_text()
        assert f" {name} as {name}" in exports

def test_conforming_tree_is_clean(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    assert check_tree(tmp_path) == ()

def test_primitive_parameter_and_return_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/bad.py",
        "import tesser.application as ts\n"
        "class BadService(ts.ApplicationService):\n"
        "    def ask(self, text: str) -> str:\n"
        "        return text\n",
    )
    findings = check_tree(tmp_path)
    assert any("parameter 'text' is not a ts.Request; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("does not return a ts.Response; a service method returns a ts.Response" in f for f in findings)

def test_arity_and_missing_annotations_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
    assert any("takes 2 parameters; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("parameter 'request' is not a ts.Request; a service method takes exactly one ts.Request" in f for f in findings)
    assert any("uses *args/**kwargs; a service method takes exactly one ts.Request" in f for f in findings)

def test_aggregate_constructor_violations_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
    assert not any("ChainService" in f and "a service method branches one level deep" in f for f in findings)

def test_indirect_subclass_still_classifies(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/derived.py",
        "from app.application.service import AskService\n"
        "from app.client.client import AskRequest\n"
        "class DerivedService(AskService):\n"
        "    def again(self, request: AskRequest) -> AskRequest:\n"
        "        return request\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "DerivedService.again" in f
        and "does not return a ts.Response; a service method returns a ts.Response" in f
        for f in findings
    )

def test_placement_totality_is_flagged(tmp_path: Path) -> None:
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/domain2.py",
        "",
    )
    write_module(
        tmp_path,
        "plain/domain/thing.py",
        "from typing import Final\n"
        "import tesser.domain as ts\n"
        "LIMIT: Final[int] = 3\n"
        "@ts.function\n"
        "def declared() -> None:\n"
        "    return None\n",
    )
    findings = check_tree(tmp_path)
    assert not any("plain.domain.thing" in f and "@ts.function" in f for f in findings)
    assert not any("plain.domain.thing" in f and "a module constant is Final" in f for f in findings)

def test_non_context_module_and_nonempty_init_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "app/util.py", "def anything() -> None:\n    return None\n")
    write_module(tmp_path, "app/__init__.py", "X = 1\n")
    findings = check_tree(tmp_path)
    assert any(
        "app.util" in f
        and "a context holds only domain, application, client, adapters, wiring, and tests modules" in f
        for f in findings
    )
    assert any("app" in f and "a context __init__ is empty" in f for f in findings)

def test_import_matrix_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as app_client\n"
        "class Bridge(ts.Gateway):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "two/domain/thing.py",
        "import tesser.domain as ts\n"
        "import two.client.client\n"
        "class TwoSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/application/service.py",
        "import tesser.application as ts\n"
        "import app.domain.thing\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "two.domain.thing" in f
        and "the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert any(
        "two.application.service" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )
    assert not any("two.adapters.gateways" in f and "imports app.client.client" in f for f in findings)

def test_test_module_totality_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
    assert any(
        "NeedyService.__init__" in f and "parameter 'db' is not a ts.Port; a service depends only on ports" in f
        for f in findings
    )

def test_client_method_rules_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/extra2.py",
        "from typing import Protocol\n"
        "import tesser.context as tc\n"
        "class BadClient(tc.Client, Protocol):\n"
        "    def ask(self, text: str) -> str: ...\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "BadClient.ask" in f and "parameter 'text' is not a ts.Request; a client method takes exactly one ts.Request" in f
        for f in findings
    )
    assert any(
        "BadClient.ask" in f and "does not return a ts.Response; a client method returns a ts.Response" in f
        for f in findings
    )

def test_records_never_carry_domain_objects(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
    assert any(
        "LoadingRepo.load" in f and "an adapter speaks records, never domain objects" in f
        for f in findings
    )
    assert any(
        "LoadingPort.fetch" in f and "a port speaks records, never domain objects" in f
        for f in findings
    )

def test_domain_field_rules_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    body = "import tesser.testing as ts\ndef test_model_picks_a_tool() -> None:\n    assert True\n"
    write_module(tmp_path, "app/adapters/eval_flat.py", body)
    write_module(tmp_path, "app/tests/__init__.py", "")
    write_module(tmp_path, "app/tests/eval_tier.py", body)
    write_module(tmp_path, "app/domain/eval_role.py", body)
    findings = check_tree(tmp_path)
    for outside in ("app.adapters.eval_flat", "app.tests.eval_tier", "app.domain.eval_role"):
        assert any(
            f"{outside} is an eval outside a gateway; an eval lives only in a gateway, "
            "the one place a sampled real-model call is honest" in f
            for f in findings
        ), outside

    write_module(tmp_path, "app/adapters/gateways/__init__.py", "")
    write_module(tmp_path, "app/adapters/gateways/eval_llm.py", body)
    write_module(tmp_path, "app/adapters/gateways/llm/__init__.py", "")
    write_module(tmp_path, "app/adapters/gateways/llm/evals/__init__.py", "")
    write_module(tmp_path, "app/adapters/gateways/llm/evals/eval_tools.py", body)
    housed = check_tree(tmp_path)
    assert not any("eval_llm is an eval outside a gateway" in f for f in housed)
    assert not any("eval_tools is an eval outside a gateway" in f for f in housed)

def test_a_handler_sibling_fakes_only_the_client(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters/handlers/http.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as client\n"
        "class Handler(ts.Handler):\n"
        "    def __init__(self, c: client.Client) -> None:\n"
        "        self._c = c\n",
    )
    write_module(tmp_path, "app/adapters/handlers/__init__.py", "")
    write_module(tmp_path, "app/adapters/__init__.py", "")
    write_module(
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
    write_module(
        tmp_path,
        "app/adapters/gateways/__init__.py",
        "",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters/handlers/http.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as client\n"
        "class Handler(ts.Handler):\n"
        "    def __init__(self, c: client.Client) -> None:\n"
        "        self._c = c\n",
    )
    write_module(tmp_path, "app/adapters/handlers/__init__.py", "")
    write_module(tmp_path, "app/adapters/__init__.py", "")
    write_module(
        tmp_path,
        "srv/test_router.py",
        "import tesser.testing as ts\n"
        "import app.adapters.handlers.http as http\n"
        "import app.application.service as application\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "srv.test_router imports app.application.service, but a test placed in "
        "srv reaches a context only through its handlers; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_router:2" in f for f in findings)

def test_a_test_reaches_only_what_its_placement_allows(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "far/domain/test_thing.py",
        "import tesser.testing as ts\n"
        "import far.client.client as client\n"
        "import app.client.client as foreign\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    write_module(
        tmp_path,
        "far/domain/thing.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    write_module(
        tmp_path,
        "far/client/client.py",
        "import tesser.context as ts\n"
        "class Client(ts.Client):\n"
        "    ...\n",
    )
    write_module(tmp_path, "far/domain/__init__.py", "")
    write_module(tmp_path, "far/client/__init__.py", "")
    findings = check_tree(tmp_path)
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

def test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application(
    tmp_path: Path,
) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "near/tests/__init__.py", "")
    write_module(
        tmp_path,
        "near/domain/thing.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    write_module(
        tmp_path,
        "near/client/client.py",
        "import tesser.context as ts\n"
        "class Client(ts.Client):\n"
        "    ...\n",
    )
    write_module(tmp_path, "near/domain/__init__.py", "")
    write_module(tmp_path, "near/client/__init__.py", "")
    write_module(
        tmp_path,
        "near/tests/test_wiring.py",
        "import tesser.testing as ts\n"
        "import near.domain.thing as thing\n"
        "import app.application.service as neighbour\n"
        "def test_x() -> None:\n"
        "    assert True\n",
    )
    assert not any("near.tests.test_wiring" in f for f in check_tree(tmp_path))

    write_module(tmp_path, "near/tests/__init__.py", "X = 1\n")
    assert any(
        "near.tests __init__ declares code; a context tests __init__ is empty" in f
        for f in check_tree(tmp_path)
    )

    write_module(tmp_path, "near/tests/__init__.py", "")
    write_module(tmp_path, "near/tests/helpers.py", "VALUE = 1\n")
    assert any(
        "near.tests.helpers is neither a test module nor conftest; "
        "a context tests package holds only test modules and conftest" in f
        for f in check_tree(tmp_path)
    )

def test_a_role_must_be_a_package(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "flat/domain.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    write_module(
        tmp_path,
        "flat/client/client.py",
        "import tesser.context as ts\n"
        "class Client(ts.Client):\n"
        "    ...\n",
    )
    write_module(tmp_path, "flat/client/__init__.py", "")
    findings = check_tree(tmp_path)
    assert any(
        "flat.domain is a role module; a role is a package, never a module" in f
        for f in findings
    )
    assert not any("flat.client" in f for f in findings)

def test_a_role_may_be_a_package(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "deep/domain/__init__.py",
        "from deep.domain.money import Money\n",
    )
    write_module(
        tmp_path,
        "deep/domain/money.py",
        "import tesser.domain as ts\n"
        "import deep.domain.currency as currency\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str, unit: currency.Currency) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n"
        "        object.__setattr__(self, '_unit', unit)\n",
    )
    write_module(
        tmp_path,
        "deep/domain/currency.py",
        "import tesser.domain as ts\n"
        "class Currency(ts.ValueObject):\n"
        "    def __init__(self, code: str) -> None:\n"
        "        object.__setattr__(self, '_code', code)\n",
    )
    write_module(
        tmp_path,
        "deep/domain/svc.py",
        "import tesser.application as ts\n"
        "class SneakyService(ts.ApplicationService):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class Bridge(ts.Gateway):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "srv/http.py",
        "import app.application.service\n"
        "import app.adapters.gateways as app_adapters\n"
        "import two.adapters.gateways\n"
        "import bootstrap.wire\n",
    )
    write_module(
        tmp_path,
        "bootstrap/wire.py",
        "import app.domain.thing\n"
        "import app.wiring.wire as wiring\n"
        "import app.client.client as app_client\n"
        "import srv.http\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import app.client.client as app_client\n"
        "class HttpHandler(ts.Handler):\n"
        "    def ask(self, body: str) -> str:\n"
        "        return app_client.AskRequest(text=body).text\n",
    )
    write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import two.client.client\n"
        "class SneakyGateway(ts.Gateway):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert not any("app.adapters.gateways" in f and "imports app.client.client" in f for f in findings)
    assert any(
        "two.adapters.gateways" in f and "imports two.client.client" in f
        and "only a handler imports its own context's client" in f
        for f in findings
    )

def test_only_a_gateway_reaches_a_foreign_client(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "two/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "import two.client.client\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "app.adapters.gateways" in f and "imports two.client.client" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )

def test_role_module_tesser_import_is_exactly_once_as_ts(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "lone/domain/thing.py",
        "class Bare:\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "noalias/domain/thing.py",
        "import tesser.domain as td\n"
        "class ThingSpec(td.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "fromform/domain/thing.py",
        "from tesser.domain import Spec\n"
        "class OtherSpec(Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "dup/domain/thing.py",
        "import tesser.domain as ts\n"
        "import tesser.domain as ts\n"
        "class DupSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "deep/domain/__init__.py",
        "from deep.domain.money import Money\n",
    )
    write_module(
        tmp_path,
        "deep/domain/money.py",
        "import tesser.domain as ts\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n",
    )
    findings = check_tree(tmp_path)
    assert not any("deep.domain" in f and "exactly once, as ts" in f for f in findings)

def test_test_module_tesser_import_rules(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/test_imports.py",
        "import tesser.domain as ts\n"
        "import tesser.testing as th\n"
        "import tesser.testing as ts2\n"
        "def test_nothing() -> None:\n"
        "    assert True\n",
    )
    write_module(
        tmp_path,
        "app/test_fromform.py",
        "from tesser.testing import fake\n"
        "def test_nothing() -> None:\n"
        "    assert fake is not None\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(tmp_path, "loose.py", "def anything() -> None:\n    return None\n")
    write_module(tmp_path, "stray/util.py", "def anything() -> None:\n    return None\n")
    write_module(tmp_path, "rules.py", "def anything() -> None:\n    return None\n")
    findings = check_tree(tmp_path)
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
    assert not any("rules belongs to no governed package" in f for f in findings)

def test_tests_package_totality_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "tests/__init__.py", "X = 1\n")
    write_module(tmp_path, "tests/util.py", "def anything() -> None:\n    return None\n")
    write_module(tmp_path, "tests/test_ok.py", "def test_ok() -> None:\n    assert True\n")
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "pkg/domain/__init__.py",
        "import tesser.domain as ts\n"
        "from pkg.domain.vo import Tag\n"
        "LIMIT = 3\n",
    )
    write_module(
        tmp_path,
        "pkg/domain/vo.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "mod/domain/vo.py",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
    )
    write_module(tmp_path, "mod/domain/__init__.py", "import mod.domain.vo as vo\n")
    write_module(
        tmp_path,
        "mod/client/client.py",
        "import tesser.context as ts\n"
        "class AskRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(tmp_path, "mod/client/__init__.py", "")
    assert not any("mod.domain:" in f for f in check_tree(tmp_path))

    write_module(tmp_path, "mod/domain/__init__.py", "from mod.domain.vo import Tag\n")
    assert any(
        "mod.domain imports names from mod.domain.vo; "
        "a context module is imported as an aliased module, never its members" in f
        for f in check_tree(tmp_path)
    )

def test_srv_and_bootstrap_statement_totality(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    write_module(
        tmp_path,
        "bootstrap/wire.py",
        "def build() -> None:\n"
        "    return None\n"
        "class App:\n"
        "    pass\n"
        "LIMIT = 3\n"
        "print('hi')\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "io1/domain/thing.py",
        "import os\n"
        "import datetime\n"
        "import tesser.domain as ts\n"
        "class StampSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "io1/client/client.py",
        "from __future__ import annotations\n"
        "import datetime\n"
        "import tesser.context as ts\n"
        "class StampRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "io1/adapters/gateways.py",
        "from pathlib import Path\n"
        "import tesser.adapters as ts\n"
        "class DiskRepository(ts.Repository):\n"
        "    def load(self, key: str) -> str: ...\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "form/client/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "form/application/service.py",
        "import tesser.application as ts\n"
        "from form.client.client import PingRequest\n",
    )
    write_module(
        tmp_path,
        "form/wiring/wire.py",
        "import tesser.context as ts\n"
        "import form.application.service\n"
        "class PingWiring(ts.Wiring):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "rel/domain/__init__.py",
        "from .money import Money\n",
    )
    write_module(
        tmp_path,
        "rel/domain/money.py",
        "import tesser.domain as ts\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n",
    )
    write_module(
        tmp_path,
        "rel/client/client.py",
        "import tesser.context as ts\n"
        "class RelRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "rel/wiring/wire.py",
        "import tesser.context as ts\n"
        "from ..client.client import RelRequest\n"
        "class RelWiring(ts.Wiring):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "rel/adapters/repo.py",
        "import tesser.adapters as ts\n"
        "from ..domain.money import Money\n"
        "class LoadingRepo(ts.Repository):\n"
        "    def load(self, key: str) -> Money: ...\n",
    )
    write_module(
        tmp_path,
        "rel/adapters/beyond.py",
        "import tesser.adapters as ts\n"
        "from ...domain.money import Money\n"
        "class BeyondRepo(ts.Repository):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "lazy/domain/thing.py",
        "class HiddenSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        import tesser.domain as ts\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "lazy2/domain/thing.py",
        "import tesser.domain as ts\n"
        "class LazySpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        import os\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "lazy3/domain/thing.py",
        "import tesser.domain as ts\n"
        "class GoodSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        import tesser.context as tc\n"
        "        self.text = text\n",
    )
    findings = check_tree(tmp_path)
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
    write_module(
        tmp_path,
        "srv/dup.py",
        "import tesser.srv as ts\n"
        "import tesser.srv as ts\n"
        "@ts.function\n"
        "def go() -> None:\n"
        "    return None\n",
    )
    write_module(
        tmp_path,
        "srv/alias.py",
        "import tesser.srv as tc\n"
        "@tc.function\n"
        "def go() -> None:\n"
        "    return None\n",
    )
    write_module(
        tmp_path,
        "bootstrap/fromform.py",
        "from tesser.context import function\n"
        "@function\n"
        "def go() -> None:\n"
        "    return None\n",
    )
    write_module(
        tmp_path,
        "bootstrap/wrongpkg.py",
        "import tesser.context as ts\n"
        "import tesser.domain as td\n",
    )
    write_module(
        tmp_path,
        "srv/consts.py",
        "from typing import Final\n"
        "LIMIT: Final[int] = 3\n",
    )
    write_module(
        tmp_path,
        "srv/annconst.py",
        "LIMIT: int = 3\n",
    )
    write_module(
        tmp_path,
        "srv/tfinal.py",
        "import tesser.srv as ts\n"
        "import typing\n"
        "LIMIT: typing.Final[int] = 3\n",
    )
    write_module(tmp_path, "srv/__init__.py", "X = 1\n")
    write_module(tmp_path, "bootstrap/__init__.py", "")
    write_module(
        tmp_path,
        "konst/domain/thing.py",
        "from typing import Final\n"
        "LIMIT: Final[int] = 3\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
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
    write_module(tmp_path, "srv/host.py", "import tesser.srv as ts\n")
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "protocol/loud.py",
        "import tesser.context as ts\n",
    )
    write_module(tmp_path, "protocol/quiet.py", "")
    write_module(
        tmp_path,
        "protocol/dup.py",
        "import tesser.srv as ts\n"
        "import tesser.srv as ts\n",
    )
    write_module(
        tmp_path,
        "protocol/form.py",
        "from tesser.srv import Request\n",
    )
    write_module(
        tmp_path,
        "protocol/alias.py",
        "import tesser.srv as tz\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(tmp_path, "protocol/__init__.py", "")
    write_module(tmp_path, "protocol/box.py", "import tesser.srv as ts\n")
    write_module(tmp_path, "boxwire.py", "import tesser.srv as ts\n")
    write_module(tmp_path, "wire.py", "import tesser.srv as ts\n")
    findings = check_tree(tmp_path)
    assert not any("protocol/box.py" in f for f in findings)
    assert not any("protocol/__init__.py" in f for f in findings)
    assert any("boxwire belongs to no governed package" in f for f in findings)
    assert any("wire belongs to no governed package" in f for f in findings)

def test_a_protocol_init_is_empty(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "protocol/__init__.py", "LIMIT = 3\n")
    write_module(tmp_path, "protocol/box.py", "import tesser.srv as ts\n")
    findings = check_tree(tmp_path)
    assert any(
        "protocol __init__ declares code; a protocol __init__ is empty" in f
        for f in findings
    )

def test_a_fake_may_implement_a_protocol_port(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "protocol/box.py",
        "from typing import Protocol\n"
        "import tesser.srv as ts\n"
        "class BoxDoor(ts.Port, Protocol):\n"
        "    def __call__(self) -> None: ...\n",
    )
    write_module(
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
    findings = check_tree(tmp_path)
    assert not any("app.test_doors.FakeDoor" in f for f in findings)

def test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/test_forms.py",
        "from app.domain.thing import Thing\n"
        "def test_thing() -> None:\n"
        "    assert Thing\n",
    )
    write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "srv/http.py",
        "from app.adapters.gateways import HttpHandler\n",
    )
    write_module(
        tmp_path,
        "skipctx/domain/thing.py",
        "import tesser.domain as ts\n"
        "from app.client.client import AskRequest\n"
        "class SkipSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    findings = check_tree(tmp_path)
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
    write_module(
        tmp_path,
        "io2/domain/thing.py",
        "from __future__ import annotations\n"
        "import tesser.domain as ts\n"
        "class DSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "io2/application/service.py",
        "from __future__ import annotations\n"
        "import typing\n"
        "import socket\n"
        "import tesser.application as ts\n"
        "class NopService(ts.ApplicationService):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert not any("io2.domain.thing" in f and "the pure stdlib" in f for f in findings)
    assert any(
        "io2.application.service imports socket; domain, client, and application "
        "import only their context, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("io2.application.service:1" in f for f in findings)
    assert not any("io2.application.service:2" in f for f in findings)

def test_an_adapters_module_holds_one_kind(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters/gateways.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n"
        "class SideGateway(ts.Gateway):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "app.adapters.gateways mixes adapter kinds" in f and "an adapters module holds one adapter kind" in f
        for f in findings
    )

def test_a_dotted_module_base_resolves(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/test_doubles.py",
        "import tesser.testing as th\n"
        "import app.application.service\n"
        "@th.fake\n"
        "class FakePort(app.application.service.AskService):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(tmp_path, "tests/test_bare.py", "def test_bare() -> None:\n    assert True\n")
    findings = check_tree(tmp_path)
    assert not any("test_bare" in f for f in findings)

def test_a_denied_app_edge_is_not_form_checked(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "srv/host.py",
        "import tesser.srv as ts\n"
        "from app.domain import thing\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "srv.host imports app.domain" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.host" in f and "never its members" in f for f in findings)

def test_a_colliding_module_definition_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "col.py", "import tesser.srv as ts\n")
    write_module(tmp_path, "col/__init__.py", "")
    findings = check_tree(tmp_path)
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert any(
        "col/__init__.py:1: TB043" in f and "a module has one definition" in f
        for f in findings
    )

def test_an_unparseable_module_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "broken.py", "def f(:\n")
    findings = check_tree(tmp_path)
    assert any(
        "broken.py:1: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert any("app/domain/thing.py" not in f for f in findings)

def test_a_non_utf8_file_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    (tmp_path / "binary.py").write_bytes(b"\xff\xfe\x00junk")
    findings = check_tree(tmp_path)
    assert any(
        "binary.py:1: TB043" in f and "every checked module is readable UTF-8 Python" in f
        for f in findings
    )

def test_skip_dirs_are_not_walked(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, ".venv/lib/junk.py", "def f(:\n")
    write_module(tmp_path, "node_modules/pkg/mod.py", "x = 1\n")
    assert check_tree(tmp_path) == ()

def test_an_ignore_suppresses_exactly_its_finding(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore TB040\n")
    findings = check_tree(tmp_path)
    assert not any("stray" in f for f in findings)

def test_a_scoped_ignore_leaves_other_codes_alone(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore TB050\n")
    findings = check_tree(tmp_path)
    assert any(
        "stray belongs to no governed package" in f and " TB040 " in f for f in findings
    )
    assert any(
        "stray.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )

def test_a_stale_ignore_is_itself_a_finding(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/domain/extra.py",
        "import tesser.domain as ts  # tessercheck:ignore\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )

def test_a_file_level_ignore_covers_the_whole_module(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "srv/host.py",
        "# tessercheck:ignore-file TB050\nimport os\n",
    )
    findings = check_tree(tmp_path)
    assert not any("never imports tesser.srv" in f for f in findings)
    assert not any("TB090" in f and "srv/host.py" in f for f in findings)

def test_a_marker_suppresses_several_codes_space_or_comma_separated(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore TB040 TB050\n")
    write_module(tmp_path, "loose.py", "import os  # tessercheck:ignore TB040, TB050\n")
    findings = check_tree(tmp_path)
    assert not any("stray" in f for f in findings)
    assert not any("loose" in f for f in findings)

def test_a_file_level_ignore_requires_codes(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "stray.py", "import os  # tessercheck:ignore-file\n")
    findings = check_tree(tmp_path)
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("stray.py:1: TB090" in f for f in findings)

def test_a_typo_or_junk_token_makes_the_marker_inert(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "stray.py", "import os  # tessercheck:ignored TB040\n")
    write_module(tmp_path, "loose.py", "import os  # tessercheck:ignore TB040 permanent\n")
    findings = check_tree(tmp_path)
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("loose belongs to no governed package" in f for f in findings)
    assert not any("TB090" in f for f in findings)

def test_a_bare_line_ignore_is_line_scoped(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/domain/extra.py",
        "import os\nimport tesser.domain as ts  # tessercheck:ignore\n",
    )
    findings = check_tree(tmp_path)
    assert any("app.domain.extra imports os" in f and " TB062 " in f for f in findings)
    assert any("app/domain/extra.py:2: TB090" in f for f in findings)

def test_tb090_itself_cannot_be_ignored(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/domain/extra.py",
        "import tesser.domain as ts  # tessercheck:ignore-file TB090\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )

def test_reader_findings_are_never_inline_suppressible(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "broken.py", "# tessercheck:ignore-file TB043\ndef f(:\n")
    findings = check_tree(tmp_path)
    assert any(
        "broken.py:2: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert not any("TB090" in f for f in findings)

def test_a_colliding_unparseable_file_reports_the_collision(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "col.py", "def f(:\n")
    write_module(tmp_path, "col/__init__.py", "")
    findings = check_tree(tmp_path)
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert not any("every checked module parses" in f for f in findings)

def test_a_utf8_bom_file_is_checked_normally(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    (tmp_path / "app" / "domain" / "bom.py").write_bytes(
        b"\xef\xbb\xbfimport tesser.domain as ts\n"
    )
    findings = check_tree(tmp_path)
    assert not any("bom" in f for f in findings)

def test_optional_construction_data_is_the_only_union(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/domain/opt.py",
        "import tesser.domain as ts\n"
        "class OptSpec(ts.Spec):\n"
        "    def __init__(self, text: str | None, items: list | None, mix: str | int) -> None:\n"
        "        self.text = text\n"
        "        self.items = items\n"
        "        self.mix = mix\n",
    )
    findings = check_tree(tmp_path)
    assert not any("parameter 'text'" in f for f in findings)
    assert any(
        "parameter 'items' is not allowed; "
        "a spec field is a primitive, a value object, or a child spec" in f
        for f in findings
    )
    assert any("parameter 'mix' is not allowed" in f for f in findings)


def test_comments_docstrings_and_bare_strings_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "tests/test_mocky.py",
        "from unittest.mock import patch\n"
        "import pytest\n"
        "def test_a(monkeypatch: pytest.MonkeyPatch) -> None:\n"
        "    assert patch\n",
    )
    findings = check_tree(tmp_path)
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
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "tests/test_seam.py",
        "def test_a(monkeypatch) -> None:  # tessercheck:ignore TB030\n"
        "    assert monkeypatch\n",
    )
    findings = check_tree(tmp_path)
    assert not any("test_seam" in f for f in findings)


def test_a_called_shadowed_builtin_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "tests/test_shadow.py",
        "def test_a() -> None:\n"
        "    id = 'x'\n"
        "    assert id(3)\n"
        "def test_b(len: int = 0) -> None:\n"
        "    assert len == 0\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "test_shadow.py:3: TB033" in f and "binds id and calls it in the same scope; "
        "a shadowed builtin is never called — rename the binding" in f
        for f in findings
    )
    assert not any("test_shadow.py:5:" in f and "TB033" in f for f in findings)


def test_string_form_equality_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "tests/test_streq.py",
        "def test_a() -> None:\n"
        "    a, b = 1, 2\n"
        "    assert str(a) == str(b)\n"
        "    assert str(a) == 'one'\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "test_streq.py:3: TB004" in f and "compare value objects by value, "
        "never by their string form" in f
        for f in findings
    )
    assert not any("test_streq.py:4:" in f for f in findings)


def test_a_value_object_mutable_collection_field_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
    assert any(
        "bag.py:3: TB002" in f and "field _items is a mutable collection; "
        "a value object's field is hashable — a tuple or frozenset, never "
        "a mutable collection" in f
        for f in findings
    )
    assert not any("_names" in f for f in findings)


def test_mutable_set_and_quoted_annotations_are_still_mutable_collections(
    tmp_path: Path,
) -> None:
    conforming_tree(tmp_path)
    write_module(
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
    findings = check_tree(tmp_path)
    assert any("field _mset is a mutable collection" in f for f in findings)
    assert any("field _quoted is a mutable collection" in f for f in findings)


def test_a_category_marker_with_trailing_prose_is_a_comment(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "tests/test_marked.py",
        "# tesser-category: spec\n"
        "# tesser-category: spec because it builds one\n"
        "def test_ok() -> None:\n"
        "    assert True\n",
    )
    findings = check_tree(tmp_path)
    assert not any("test_marked.py:1:" in f for f in findings)
    assert any(
        "test_marked.py:2: TB020" in f and "carries a code comment" in f for f in findings
    )
