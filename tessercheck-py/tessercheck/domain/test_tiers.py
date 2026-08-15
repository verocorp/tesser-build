from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks


@ts.helper
def _spec(
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
    base: tuple[tuple[str, str, str | None, bool], ...] = (
        (
            "app/domain/thing.py",
            "app.domain.thing",
            "import tesser.domain as ts\n"
            "class ThingSpec(ts.Spec):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class Thing(ts.AggregateRoot):\n"
            "    def __init__(self, spec: ThingSpec) -> None:\n"
            "        self.text = spec.text\n",
            False,
        ),
        (
            "app/client/client.py",
            "app.client.client",
            "import tesser.context as ts\n"
            "class AskRequest(ts.Request):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class AskResponse(ts.Response):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n",
            False,
        ),
        (
            "app/application/service.py",
            "app.application.service",
            "import tesser.application as ts\n"
            "import app.client.client as client\n"
            "class AskService(ts.ApplicationService):\n"
            "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
            "        return client.AskResponse(text=request.text)\n"
            "    def _helper(self, anything: int) -> int:\n"
            "        return anything\n",
            False,
        ),
    ),
) -> checks.CodebaseSpec:
    return checks.CodebaseSpec(
        sources=base + sources, declared="app", nested=(), symlinked=()
    )


def test_an_eval_lives_only_in_a_gateway() -> None:
    body = (
        "import tesser.testing as ts\n"
        "def test_model_picks_a_tool() -> None:\n"
        "    assert True\n"
    )
    loose = (
        ("app/adapters/eval_flat.py", "app.adapters.eval_flat", body, False),
        ("app/tests/__init__.py", "app.tests", "", True),
        ("app/tests/eval_tier.py", "app.tests.eval_tier", body, False),
        ("app/domain/eval_role.py", "app.domain.eval_role", body, False),
    )
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=loose)).violations()
               )
    for outside in ("app.adapters.eval_flat", "app.tests.eval_tier", "app.domain.eval_role"):
        assert any(
            f"{outside} is an eval outside a gateway; an eval lives only in a gateway, "
            "the one place a sampled real-model call is honest" in f
            for f in findings
        ), outside

    housed = tuple(
                 f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                 for v in checks.Codebase(_spec(sources=loose
        + (
            (
                "app/adapters/gateways/__init__.py",
                "app.adapters.gateways",
                "",
                True,
            ),
            (
                "app/adapters/gateways/eval_llm.py",
                "app.adapters.gateways.eval_llm",
                body,
                False,
            ),
            (
                "app/adapters/gateways/llm/__init__.py",
                "app.adapters.gateways.llm",
                "",
                True,
            ),
            (
                "app/adapters/gateways/llm/evals/__init__.py",
                "app.adapters.gateways.llm.evals",
                "",
                True,
            ),
            (
                "app/adapters/gateways/llm/evals/eval_tools.py",
                "app.adapters.gateways.llm.evals.eval_tools",
                body,
                False,
            ),
        ))).violations()
             )
    assert not any("eval_llm is an eval outside a gateway" in f for f in housed)
    assert not any("eval_tools is an eval outside a gateway" in f for f in housed)


def test_a_handler_sibling_fakes_only_the_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/handlers/http.py",
                "app.adapters.handlers.http",
                "import tesser.adapters as ts\n"
                "import app.client.client as client\n"
                "class Handler(ts.Handler):\n"
                "    def __init__(self, c: client.Client) -> None:\n"
                "        self._c = c\n",
                False,
            ),
            ("app/adapters/handlers/__init__.py", "app.adapters.handlers", "", True),
            ("app/adapters/__init__.py", "app.adapters", "", True),
            (
                "app/adapters/handlers/test_http.py",
                "app.adapters.handlers.test_http",
                "import tesser.testing as ts\n"
                "import app.adapters.handlers.http as http\n"
                "import app.client.client as client\n"
                "import app.application.service as application\n"
                "import app.adapters.gateways as gateways\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("app/adapters/gateways/__init__.py", "app.adapters.gateways", "", True),
        ))).violations()
               )
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


def test_a_srv_test_reaches_a_context_only_through_its_handlers() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/handlers/http.py",
                "app.adapters.handlers.http",
                "import tesser.adapters as ts\n"
                "import app.client.client as client\n"
                "class Handler(ts.Handler):\n"
                "    def __init__(self, c: client.Client) -> None:\n"
                "        self._c = c\n",
                False,
            ),
            ("app/adapters/handlers/__init__.py", "app.adapters.handlers", "", True),
            ("app/adapters/__init__.py", "app.adapters", "", True),
            (
                "srv/test_router.py",
                "srv.test_router",
                "import tesser.testing as ts\n"
                "import app.adapters.handlers.http as http\n"
                "import app.application.service as application\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.test_router imports app.application.service, but a test placed in "
        "srv reaches a context only through its handlers; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_router:2" in f for f in findings)


def test_a_test_reaches_only_what_its_placement_allows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "far/domain/test_thing.py",
                "far.domain.test_thing",
                "import tesser.testing as ts\n"
                "import far.client.client as client\n"
                "import app.client.client as foreign\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "far/domain/thing.py",
                "far.domain.thing",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            (
                "far/client/client.py",
                "far.client.client",
                "import tesser.context as ts\n"
                "class Client(ts.Client):\n"
                "    ...\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
            ("far/client/__init__.py", "far.client", "", True),
        ))).violations()
               )
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


def test_a_repository_sibling_test_reaches_its_kind_and_application_only() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/repositories/words.py",
                "app.adapters.repositories.words",
                "import tesser.adapters as ts\n"
                "class WordsRepository(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._rows: dict[str, str] = {}\n",
                False,
            ),
            (
                "app/adapters/repositories/__init__.py",
                "app.adapters.repositories",
                "",
                True,
            ),
            ("app/adapters/__init__.py", "app.adapters", "", True),
            (
                "app/adapters/repositories/test_words.py",
                "app.adapters.repositories.test_words",
                "import app.adapters.repositories.words as words\n"
                "import app.application.ports.words as words_port\n"
                "import app.domain.thing as thing\n"
                "import far.client.client as farclient\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "far/client/client.py",
                "far.client.client",
                "import tesser.context as ts\n"
                "class Ping(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            ("far/client/__init__.py", "far.client", "", True),
            (
                "far/domain/thing.py",
                "far.domain.thing",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
        ))).violations()
               )
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


def test_a_wiring_sibling_test_mirrors_production_wiring_reach() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/wiring/__init__.py", "app.wiring", "", True),
            (
                "app/wiring/test_wire.py",
                "app.wiring.test_wire",
                "import app.application.service as service\n"
                "import far.client.client as farclient\n"
                "import app.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "far/client/client.py",
                "far.client.client",
                "import tesser.context as ts\n"
                "class Ping(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            ("far/client/__init__.py", "far.client", "", True),
            (
                "far/domain/thing.py",
                "far.domain.thing",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
        ))).violations()
               )
    assert any(
        "app.wiring.test_wire imports app.domain.thing, but a test placed in wiring "
        "reaches only wiring, application, adapters, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_wire.py:1:" in f for f in findings)
    assert not any("test_wire.py:2:" in f for f in findings)


def test_a_client_sibling_test_reaches_only_its_own_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/client/test_client.py",
                "app.client.test_client",
                "import app.client.client as client\n"
                "import app.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.client.test_client imports app.domain.thing, but a test placed in client "
        "reaches only client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_client.py:1:" in f for f in findings)


def test_a_bootstrap_test_reaches_a_context_like_production_bootstrap() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "bootstrap/test_boot.py",
                "bootstrap.test_boot",
                "import app.client.client as client\n"
                "import app.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("bootstrap/__init__.py", "bootstrap", "", True),
        ))).violations()
               )
    assert any(
        "bootstrap.test_boot imports app.domain.thing, but a test placed in "
        "bootstrap reaches a context only through its wiring, client, and adapters; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_boot.py:1:" in f for f in findings)


def test_a_protocol_test_reaches_no_context() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/test_proto.py",
                "protocol.test_proto",
                "import app.client.client as client\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("protocol/__init__.py", "protocol", "", True),
        ))).violations()
               )
    assert any(
        "protocol.test_proto imports app.client.client, but a test placed in "
        "protocol reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_a_test_that_resolves_to_no_tier_is_itself_a_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/test_flat.py",
                "app.adapters.test_flat",
                "def test_x() -> None:\n    assert True\n",
                False,
            ),
            (
                "app/adapters/blobs/test_blob.py",
                "app.adapters.blobs.test_blob",
                "def test_x() -> None:\n    assert True\n",
                False,
            ),
            ("app/adapters/blobs/__init__.py", "app.adapters.blobs", "", True),
            ("app/adapters/__init__.py", "app.adapters", "", True),
        ))).violations()
               )
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


def test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application() -> None:
    context = (
        (
            "near/domain/thing.py",
            "near.domain.thing",
            "import tesser.domain as ts\n"
            "class Tag(ts.ValueObject):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        object.__setattr__(self, '_text', text)\n",
            False,
        ),
        (
            "near/client/client.py",
            "near.client.client",
            "import tesser.context as ts\n"
            "class Client(ts.Client):\n"
            "    ...\n",
            False,
        ),
        ("near/domain/__init__.py", "near.domain", "", True),
        ("near/client/__init__.py", "near.client", "", True),
        (
            "near/tests/test_wiring.py",
            "near.tests.test_wiring",
            "import tesser.testing as ts\n"
            "import near.domain.thing as thing\n"
            "import app.application.service as neighbour\n"
            "def test_x() -> None:\n"
            "    assert True\n",
            False,
        ),
    )
    empty = (("near/tests/__init__.py", "near.tests", "", True),)
    assert not any(
        "near.tests.test_wiring" in f for f in tuple(
                                                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                                                   for v in checks.Codebase(_spec(sources=empty + context)).violations()
                                               )
    )

    declared = (("near/tests/__init__.py", "near.tests", "X = 1\n", True),)
    assert any(
        "near.tests __init__ declares code; a context tests __init__ is empty" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=declared + context)).violations()
                 )
    )

    helpers = (("near/tests/helpers.py", "near.tests.helpers", "VALUE = 1\n", False),)
    assert any(
        "near.tests.helpers is neither a test module nor conftest; "
        "a context tests package holds only test modules and conftest" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=empty + context + helpers)).violations()
                 )
    )


def test_a_root_test_reaches_a_context_only_through_wiring_and_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n",
                False,
            ),
            (
                "tests/test_app.py",
                "tests.test_app",
                "import app.client.client as client\n"
                "import app.wiring.wire as wire\n"
                "import app.domain.thing as thing\n"
                "import app.application.service as service\n"
                "import bootstrap.wire\n"
                "import tests.support\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "tests/support.py",
                "tests.support",
                "import app.domain.thing as thing\n",
                False,
            ),
            ("bootstrap/wire.py", "bootstrap.wire", "", False),
        ))).violations()
               )
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


def test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/test_thing.py",
                "app.domain.test_thing",
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "srv/test_host.py",
                "srv.test_host",
                "import bootstrap.wire\n"
                "import tests.test_root\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "tests/test_root.py",
                "tests.test_root",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "bootstrap/test_wire.py",
                "bootstrap.test_wire",
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
            ("bootstrap/wire.py", "bootstrap.wire", "", False),
        ))).violations()
               )
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


def test_a_context_tests_module_reaches_its_own_tests_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/test_thing.py",
                "app.tests.test_thing",
                "import app.tests.conftest as helpers\n"
                "import two.tests.test_two as foreign\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            ("app/tests/conftest.py", "app.tests.conftest", "", False),
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n",
                False,
            ),
            ("two/tests/__init__.py", "two.tests", "", True),
            (
                "two/tests/test_two.py",
                "two.tests.test_two",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.tests.test_thing imports app.tests.conftest" in f for f in findings)
    assert any(
        "app.tests.test_thing imports two.tests.test_two, but a test placed in tests "
        "reaches only application, client of a neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_an_unplaced_test_module_is_still_governed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "weird/test_nested.py",
                "weird.test_nested",
                "import app.domain.thing as thing\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "test_solo.py",
                "test_solo",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "weird.test_nested resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )
    assert any("test_solo resolves to no test tier" in f for f in findings)


def test_a_conftest_off_the_tier_map_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/conftest.py",
                "app.adapters.conftest",
                "import os\nimport app.domain.thing\n",
                False,
            ),
            (
                "app/conftest.py",
                "app.conftest",
                "import app.domain.thing\n",
                False,
            ),
        ))).violations()
               )
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


def test_a_placed_conftest_carries_its_tier() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/conftest.py",
                "tests.conftest",
                "import bootstrap.wire\nimport app.domain.thing\n",
                False,
            ),
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/conftest.py",
                "app.tests.conftest",
                "import app.domain.thing as thing\nimport srv.http\n",
                False,
            ),
            ("bootstrap/wire.py", "bootstrap.wire", "", False),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
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


def test_adapter_kind_and_protocol_tests_shell_reach() -> None:
    kinds = ("handlers", "gateways", "repositories")
    adapters = tuple(
        entry
        for kind in kinds
        for entry in (
            (f"app/adapters/{kind}/__init__.py", f"app.adapters.{kind}", "", True),
            (
                f"app/adapters/{kind}/test_{kind}.py",
                f"app.adapters.{kind}.test_{kind}",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        )
    )
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("srv/http.py", "srv.http", "", False),
        )
        + adapters
        + (
            (
                "protocol/test_http.py",
                "protocol.test_http",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
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


def test_an_eval_in_a_gateway_reaches_no_shell_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("srv/http.py", "srv.http", "", False),
            ("app/adapters/gateways/__init__.py", "app.adapters.gateways", "", True),
            (
                "app/adapters/gateways/eval_model.py",
                "app.adapters.gateways.eval_model",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
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


def test_a_context_tests_helper_answers_for_its_imports() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/support.py",
                "app.tests.support",
                "import app.domain.thing as thing\nimport srv.http\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
    assert any(
        "app.tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        "app.tests.support imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )
    assert not any("app.tests.support imports app.domain.thing" in f for f in findings)


def test_a_main_below_the_context_root_is_a_governed_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/__main__.py",
                "app.domain.__main__",
                "import app.application.service as service\n",
                False,
            ),
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/__main__.py",
                "app.tests.__main__",
                "import app.application.service as service\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.domain.__main__ imports app.application.service; the same-context matrix is" in f
        for f in findings
    )
    assert any(
        "app.tests.__main__ is neither a test module nor conftest" in f for f in findings
    )


def test_every_test_tier_has_a_shell_row() -> None:
    tiers = (
        set(checks.TEST_TIER_REACH)
        | {checks.SRV_TIER, checks.BOOTSTRAP_TIER, checks.PROTOCOL_TIER, checks.APP_TIER}
    )
    assert tiers <= set(checks.TEST_TIER_SHELL)


def test_test_module_tesser_import_rules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_imports.py",
                "app.test_imports",
                "import tesser.domain as ts\n"
                "import tesser.testing as th\n"
                "import tesser.testing as ts2\n"
                "def test_nothing() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "app/test_fromform.py",
                "app.test_fromform",
                "from tesser.testing import fake\n"
                "def test_nothing() -> None:\n"
                "    assert fake is not None\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.test_imports imports tesser.domain; a test module's tesser imports "
        "are tesser.testing, tesser.lifecycle, and tesser.serialization" in f
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


def test_a_test_module_may_omit_tesser_testing() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_bare.py",
                "tests.test_bare",
                "def test_bare() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("test_bare" in f for f in findings)


def test_test_module_totality_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_junk.py",
                "app.test_junk",
                "import tesser.testing as th\n"
                "def build() -> None:\n"
                "    return None\n"
                "class Junk:\n"
                "    pass\n"
                "@th.fake\n"
                "class FakeNothing:\n"
                "    pass\n"
                "COUNT = 2\n",
                False,
            ),
        ))).violations()
               )
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


def test_helper_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_helpers.py",
                "app.test_helpers",
                "import tesser.testing as th\n"
                "from app.domain.thing import Thing, ThingSpec\n"
                "@th.helper\n"
                "def bad_builder(thing: Thing, count: int) -> Thing:\n"
                "    if count:\n"
                "        return thing\n"
                "    return thing\n",
                False,
            ),
        ))).violations()
               )
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


def test_a_fake_may_implement_a_protocol_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/box.py",
                "protocol.box",
                "from typing import Protocol\n"
                "import tesser.srv as ts\n"
                "class BoxDoor(ts.Port, Protocol):\n"
                "    def __call__(self) -> None: ...\n",
                False,
            ),
            (
                "app/test_doors.py",
                "app.test_doors",
                "import tesser.testing as ts\n"
                "from protocol.box import BoxDoor\n"
                "@ts.fake\n"
                "class FakeDoor(BoxDoor):\n"
                "    def __call__(self) -> None:\n"
                "        return None\n"
                "def test_door() -> None:\n"
                "    assert FakeDoor\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.test_doors.FakeDoor" in f for f in findings)


def test_a_test_module_may_from_import_tesser_serialization() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/test_thing.py",
                "app.domain.test_thing",
                "from tesser.serialization import canonical_str\n"
                "def test_canonical() -> None:\n"
                '    assert canonical_str("x") == "x"\n',
                False,
            ),
        ))).violations()
               )
    assert not any("app.domain.test_thing" in f for f in findings)
