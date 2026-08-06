from pathlib import Path

from tests.conftest import check_tree, conforming_tree, write_module


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
        "from app.client import AskRequest, AskResponse\n"
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
        "from app.client import AskRequest, AskResponse\n"
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
        "from app.client import AskRequest, AskResponse\n"
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
        "from app.application import AskService\n"
        "from app.client import AskRequest\n"
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
        "plain/domain.py",
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
    assert any("plain.domain.Loose" in f and "every context class declares its block" in f for f in findings)
    assert any("plain.domain.Ask" in f and "a kind lives only in its role module" in f for f in findings)
    assert any("plain.domain.stray" in f and "a module function declares itself with @ts.function" in f for f in findings)
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
        "plain/domain.py",
        "from typing import Final\n"
        "import tesser.domain as ts\n"
        "LIMIT: Final[int] = 3\n"
        "@ts.function\n"
        "def declared() -> None:\n"
        "    return None\n",
    )
    findings = check_tree(tmp_path)
    assert not any("plain.domain" in f and "@ts.function" in f for f in findings)
    assert not any("plain.domain" in f and "a module constant is Final" in f for f in findings)


def test_non_context_module_and_nonempty_init_are_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(tmp_path, "app/util.py", "def anything() -> None:\n    return None\n")
    write_module(tmp_path, "app/__init__.py", "X = 1\n")
    findings = check_tree(tmp_path)
    assert any(
        "app.util" in f and "a context holds only domain, application, client, adapters, and wiring modules" in f
        for f in findings
    )
    assert any("app" in f and "a context __init__ is empty" in f for f in findings)


def test_import_matrix_is_flagged(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "two/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/adapters.py",
        "import tesser.adapters as ts\n"
        "import app.client\n"
        "class Bridge(ts.Gateway):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "two/domain.py",
        "import tesser.domain as ts\n"
        "import two.client\n"
        "class TwoSpec(ts.Spec):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/application.py",
        "import tesser.application as ts\n"
        "import app.domain\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "two.domain" in f
        and "the same-context matrix is a role to itself, application to domain and client, adapters to application, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert any(
        "two.application" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )
    assert not any("two.adapters" in f and "imports app.client" in f for f in findings)


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
        "from app.domain import Thing, ThingSpec\n"
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
    assert any("bad_builder" in f and "has control flow at line" in f and "a helper only constructs" in f for f in findings)


def test_service_dependencies_must_be_ports(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/extra.py",
        "import tesser.application as ts\n"
        "from app.client import AskRequest, AskResponse\n"
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
        "from app.domain import Thing\n"
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
        "from deep.domain.currency import Currency\n"
        "class Money(ts.ValueObject):\n"
        "    def __init__(self, amount: str, currency: Currency) -> None:\n"
        "        object.__setattr__(self, '_amount', amount)\n"
        "        object.__setattr__(self, '_currency', currency)\n",
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
        "two/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "app/wiring.py",
        "import tesser.context as ts\n"
        "import app.application\n"
        "import app.client\n"
        "import two.client\n"
        "import two.domain\n"
        "class AskWiring(ts.Wiring):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert not any("app.wiring" in f and "not a context module" in f for f in findings)
    assert not any("app.wiring" in f and "imports app.application" in f for f in findings)
    assert not any("app.wiring" in f and "imports two.client" in f for f in findings)
    assert not any("app.wiring.AskWiring" in f and "a kind lives only in its role module" in f for f in findings)
    assert any(
        "app.wiring" in f and "imports two.domain" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )


def test_srv_and_bootstrap_import_rows(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "two/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/adapters.py",
        "import tesser.adapters as ts\n"
        "class Bridge(ts.Gateway):\n"
        "    pass\n",
    )
    write_module(
        tmp_path,
        "srv/http.py",
        "import app.application\n"
        "import app.adapters\n"
        "import two.adapters\n"
        "import bootstrap.wire\n",
    )
    write_module(
        tmp_path,
        "bootstrap/wire.py",
        "import app.domain\n"
        "import app.wiring\n"
        "import app.client\n"
        "import srv.http\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "srv.http" in f and "imports app.application" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert any(
        "srv.http" in f and "imports two.adapters" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.http" in f and "imports app.adapters" in f for f in findings)
    assert not any("srv.http" in f and "imports bootstrap.wire" in f for f in findings)
    assert any(
        "bootstrap.wire" in f and "imports app.domain" in f
        and "bootstrap builds from wiring, clients, and adapters, never domain or application" in f
        for f in findings
    )
    assert not any("bootstrap.wire" in f and "imports app.wiring" in f for f in findings)
    assert not any("bootstrap.wire" in f and "imports app.client" in f for f in findings)
    assert any(
        "bootstrap.wire" in f and "imports srv.http" in f
        and "the composition root never imports a host" in f
        for f in findings
    )


def test_only_a_handler_imports_its_own_client(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters.py",
        "import tesser.adapters as ts\n"
        "import app.client\n"
        "class HttpHandler(ts.Handler):\n"
        "    def ask(self, body: str) -> str:\n"
        "        return app.client.AskRequest(text=body).text\n",
    )
    write_module(
        tmp_path,
        "two/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "two/adapters.py",
        "import tesser.adapters as ts\n"
        "import two.client\n"
        "class SneakyGateway(ts.Gateway):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert not any("app.adapters" in f and "imports app.client" in f for f in findings)
    assert any(
        "two.adapters" in f and "imports two.client" in f
        and "only a handler imports its own context's client" in f
        for f in findings
    )


def test_only_a_gateway_reaches_a_foreign_client(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "two/client.py",
        "import tesser.context as ts\n"
        "class PingRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
    )
    write_module(
        tmp_path,
        "app/adapters.py",
        "import tesser.adapters as ts\n"
        "import two.client\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "app.adapters" in f and "imports two.client" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )


def test_an_adapters_module_holds_one_kind(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/adapters.py",
        "import tesser.adapters as ts\n"
        "class HttpHandler(ts.Handler):\n"
        "    pass\n"
        "class SideGateway(ts.Gateway):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert any(
        "app.adapters mixes adapter kinds" in f and "an adapters module holds one adapter kind" in f
        for f in findings
    )


def test_a_dotted_module_base_resolves(tmp_path: Path) -> None:
    conforming_tree(tmp_path)
    write_module(
        tmp_path,
        "app/test_doubles.py",
        "import tesser.testing as th\n"
        "import app.application\n"
        "@th.fake\n"
        "class FakePort(app.application.AskService):\n"
        "    pass\n",
    )
    findings = check_tree(tmp_path)
    assert not any("FakePort" in f and "implements no ts.Port" in f and "undeclared" in f for f in findings)
    assert any(
        "FakePort" in f and "a fake implements the port or client it doubles" in f
        for f in findings
    )
