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


def test_import_matrix_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "two/adapters/gateways.py",
                "two.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import app.client.client as app_client\n"
                "class Bridge(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "two/domain/thing.py",
                "two.domain.thing",
                "import tesser.domain as ts\n"
                "import two.client.client\n"
                "class TwoSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "two/application/service.py",
                "two.application.service",
                "import tesser.application as ts\n"
                "import app.domain.thing\n",
                False,
            ),
        ))).violations()
               )
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


def test_srv_and_bootstrap_import_rows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "two/adapters/gateways.py",
                "two.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class Bridge(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "import app.application.service\n"
                "import app.adapters.gateways as app_adapters\n"
                "import two.adapters.gateways\n"
                "import bootstrap.wire\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "import app.domain.thing\n"
                "import app.wiring.wire as wiring\n"
                "import app.client.client as app_client\n"
                "import srv.http\n",
                False,
            ),
        ))).violations()
               )
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


def test_only_a_handler_imports_its_own_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import app.client.client as app_client\n"
                "class HttpHandler(ts.Handler):\n"
                "    def ask(self, body: str) -> str:\n"
                "        return app_client.AskRequest(text=body).text\n",
                False,
            ),
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "two/adapters/gateways.py",
                "two.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import two.client.client\n"
                "class SneakyGateway(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.adapters.gateways" in f and "imports app.client.client" in f for f in findings)
    assert any(
        "two.adapters.gateways" in f and "imports two.client.client" in f
        and "only a handler imports its own context's client" in f
        for f in findings
    )


def test_only_a_gateway_reaches_a_foreign_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import two.client.client\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.adapters.gateways" in f and "imports two.client.client" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )


def test_role_module_tesser_import_is_exactly_once_as_ts() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "lone/domain/thing.py",
                "lone.domain.thing",
                "class Bare:\n"
                "    pass\n",
                False,
            ),
            (
                "noalias/domain/thing.py",
                "noalias.domain.thing",
                "import tesser.domain as td\n"
                "class ThingSpec(td.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "fromform/domain/thing.py",
                "fromform.domain.thing",
                "from tesser.domain import Spec\n"
                "class OtherSpec(Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "dup/domain/thing.py",
                "dup.domain.thing",
                "import tesser.domain as ts\n"
                "import tesser.domain as ts\n"
                "class DupSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
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


def test_reexport_only_role_init_needs_no_tesser_import() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "deep/domain/__init__.py",
                "deep.domain",
                "from deep.domain.money import Money\n",
                True,
            ),
            (
                "deep/domain/money.py",
                "deep.domain.money",
                "import tesser.domain as ts\n"
                "class Money(ts.ValueObject):\n"
                "    def __init__(self, amount: str) -> None:\n"
                "        object.__setattr__(self, '_amount', amount)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("deep.domain" in f and "exactly once, as ts" in f for f in findings)


def test_role_init_only_reexports_its_own_role() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "pkg/domain/__init__.py",
                "pkg.domain",
                "import tesser.domain as ts\n"
                "from pkg.domain.vo import Tag\n"
                "LIMIT = 3\n",
                True,
            ),
            (
                "pkg/domain/vo.py",
                "pkg.domain.vo",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
        ))).violations()
               )
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


def test_a_role_init_may_import_a_module_but_never_a_class() -> None:
    vo = (
        "mod/domain/vo.py",
        "mod.domain.vo",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
        False,
    )
    client = (
        "mod/client/client.py",
        "mod.client.client",
        "import tesser.context as ts\n"
        "class AskRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
        False,
    )
    client_init = ("mod/client/__init__.py", "mod.client", "", True)
    module_form = (
        "mod/domain/__init__.py",
        "mod.domain",
        "import mod.domain.vo as vo\n",
        True,
    )
    class_form = (
        "mod/domain/__init__.py",
        "mod.domain",
        "from mod.domain.vo import Tag\n",
        True,
    )
    assert not any(
        "mod.domain:" in f for f in tuple(
                                        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                                        for v in checks.Codebase(_spec(sources=(vo, module_form, client, client_init))).violations()
                                    )
    )

    assert any(
        "mod.domain imports names from mod.domain.vo; "
        "a context module is imported as an aliased module, never its members" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=(vo, class_form, client, client_init))).violations()
                 )
    )


def test_srv_and_bootstrap_statement_totality() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/box.py",
                "srv.box",
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
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "def build() -> None:\n"
                "    return None\n"
                "class App:\n"
                "    pass\n"
                "LIMIT = 3\n"
                "print('hi')\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.box imports tesser.domain; a srv module's tesser imports "
        "are tesser.srv, tesser.errors, and tesser.lifecycle" in f
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


def test_pure_core_stdlib_allowlist() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "io1/domain/thing.py",
                "io1.domain.thing",
                "import os\n"
                "import datetime\n"
                "import tesser.domain as ts\n"
                "class StampSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "io1/client/client.py",
                "io1.client.client",
                "from __future__ import annotations\n"
                "import datetime\n"
                "import tesser.context as ts\n"
                "class StampRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "io1/adapters/gateways.py",
                "io1.adapters.gateways",
                "from pathlib import Path\n"
                "import tesser.adapters as ts\n"
                "class DiskRepository(ts.Repository):\n"
                "    def load(self, key: str) -> str: ...\n",
                False,
            ),
        ))).violations()
               )
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


def test_context_module_import_form() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "form/client/client.py",
                "form.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "form/application/service.py",
                "form.application.service",
                "import tesser.application as ts\n"
                "from form.client.client import PingRequest\n",
                False,
            ),
            (
                "form/wiring/wire.py",
                "form.wiring.wire",
                "import tesser.context as ts\n"
                "import form.application.service\n"
                "class PingWiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
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


def test_relative_imports_resolve_against_the_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "rel/domain/__init__.py",
                "rel.domain",
                "from .money import Money\n",
                True,
            ),
            (
                "rel/domain/money.py",
                "rel.domain.money",
                "import tesser.domain as ts\n"
                "class Money(ts.ValueObject):\n"
                "    def __init__(self, amount: str) -> None:\n"
                "        object.__setattr__(self, '_amount', amount)\n",
                False,
            ),
            (
                "rel/client/client.py",
                "rel.client.client",
                "import tesser.context as ts\n"
                "class RelRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "rel/wiring/wire.py",
                "rel.wiring.wire",
                "import tesser.context as ts\n"
                "from ..client.client import RelRequest\n"
                "class RelWiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
            (
                "rel/adapters/repo.py",
                "rel.adapters.repo",
                "import tesser.adapters as ts\n"
                "from ..domain.money import Money\n"
                "class LoadingRepo(ts.Repository):\n"
                "    def load(self, key: str) -> Money: ...\n",
                False,
            ),
            (
                "rel/adapters/beyond.py",
                "rel.adapters.beyond",
                "import tesser.adapters as ts\n"
                "from ...domain.money import Money\n"
                "class BeyondRepo(ts.Repository):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
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


def test_nested_imports_neither_classify_nor_satisfy_presence() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "lazy/domain/thing.py",
                "lazy.domain.thing",
                "class HiddenSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        import tesser.domain as ts\n"
                "        self.text = text\n",
                False,
            ),
            (
                "lazy2/domain/thing.py",
                "lazy2.domain.thing",
                "import tesser.domain as ts\n"
                "class LazySpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        import os\n"
                "        self.text = text\n",
                False,
            ),
            (
                "lazy3/domain/thing.py",
                "lazy3.domain.thing",
                "import tesser.domain as ts\n"
                "class GoodSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        import tesser.context as tc\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
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


def test_srv_and_bootstrap_tesser_form_modes() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/dup.py",
                "srv.dup",
                "import tesser.srv as ts\n"
                "import tesser.srv as ts\n"
                "@ts.function\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "srv/alias.py",
                "srv.alias",
                "import tesser.srv as tc\n"
                "@tc.function\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "bootstrap/fromform.py",
                "bootstrap.fromform",
                "from tesser.context import function\n"
                "@function\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "bootstrap/wrongpkg.py",
                "bootstrap.wrongpkg",
                "import tesser.context as ts\n"
                "import tesser.domain as td\n",
                False,
            ),
            (
                "srv/consts.py",
                "srv.consts",
                "from typing import Final\n"
                "LIMIT: Final[int] = 3\n",
                False,
            ),
            (
                "srv/annconst.py",
                "srv.annconst",
                "LIMIT: int = 3\n",
                False,
            ),
            (
                "srv/tfinal.py",
                "srv.tfinal",
                "import tesser.srv as ts\n"
                "import typing\n"
                "LIMIT: typing.Final[int] = 3\n",
                False,
            ),
            ("srv/__init__.py", "srv", "X = 1\n", True),
            ("bootstrap/__init__.py", "bootstrap", "", True),
            (
                "konst/domain/thing.py",
                "konst.domain.thing",
                "from typing import Final\n"
                "LIMIT: Final[int] = 3\n",
                False,
            ),
        ), base=())).violations()
               )
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
        "a bootstrap module's tesser imports are tesser.context, "
        "tesser.errors, and tesser.lifecycle" in f
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


def test_pure_core_allowlist_covers_application_and_domain_future() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "io2/domain/thing.py",
                "io2.domain.thing",
                "from __future__ import annotations\n"
                "import tesser.domain as ts\n"
                "class DSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "io2/application/service.py",
                "io2.application.service",
                "from __future__ import annotations\n"
                "import typing\n"
                "import socket\n"
                "import tesser.application as ts\n"
                "class NopService(ts.ApplicationService):\n"
                "    pass\n",
                False,
            ),
        ), base=())).violations()
               )
    assert not any("io2.domain.thing" in f and "the pure stdlib" in f for f in findings)
    assert any(
        "io2.application.service imports socket; domain, client, and application "
        "import only their context, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("io2.application.service:1" in f for f in findings)
    assert not any("io2.application.service:2" in f for f in findings)


def test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
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
                False,
            ),
            (
                "srv/box.py",
                "srv.box",
                "import tesser.srv as ts\n"
                "import tesser.domain\n"
                "class Value(tesser.domain.ValueObject):\n"
                "    pass\n"
                "class Turn(ts.Response):\n"
                "    pass\n"
                "class Label(ts.Record):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
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


def test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_forms.py",
                "app.test_forms",
                "from app.domain.thing import Thing\n"
                "def test_thing() -> None:\n"
                "    assert Thing\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "from app.adapters.gateways import HttpHandler\n",
                False,
            ),
            (
                "skipctx/domain/thing.py",
                "skipctx.domain.thing",
                "import tesser.domain as ts\n"
                "from app.client.client import AskRequest\n"
                "class SkipSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
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


def test_a_denied_app_edge_is_not_form_checked() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/host.py",
                "srv.host",
                "import tesser.srv as ts\n"
                "from app.domain import thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.host imports app.domain" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.host" in f and "never its members" in f for f in findings)


def test_production_never_imports_the_tests_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_ok.py",
                "tests.test_ok",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "import tests.test_ok\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "import protocol.http\nimport tests.test_ok\n",
                False,
            ),
            (
                "protocol/http.py",
                "protocol.http",
                "import tesser.srv as ts\n",
                False,
            ),
        ))).violations()
               )
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


def test_a_context_role_reaches_the_app_shell_only_as_handlers_to_protocol() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/http.py",
                "protocol.http",
                "import tesser.srv as ts\n",
                False,
            ),
            (
                "app/adapters/handlers.py",
                "app.adapters.handlers",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "import srv.http as host\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n"
                "import protocol.http as http\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "class PeerGateway(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "app/adapters/handlers_support.py",
                "app.adapters.handlers_support",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n",
                False,
            ),
            ("app/adapters/repositories/__init__.py", "app.adapters.repositories", "", True),
            (
                "app/adapters/repositories/smuggle.py",
                "app.adapters.repositories.smuggle",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "class SmuggleHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
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


def test_a_classless_module_inside_handlers_may_speak_protocol() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("app/adapters/handlers/__init__.py", "app.adapters.handlers", "", True),
            (
                "app/adapters/handlers/usage.py",
                "app.adapters.handlers.usage",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "app.adapters.handlers.usage imports protocol.http" in f for f in findings
    ), f"a helper module inside handlers/ was denied protocol: {findings}"


def test_a_shell_name_missing_from_the_tree_is_not_the_shell() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/test_thing.py",
                "app.domain.test_thing",
                "import protocol.thirdparty\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\nimport bootstrap\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.domain.test_thing imports protocol.thirdparty" in f for f in findings)
    assert not any("app.wiring.wire imports bootstrap" in f for f in findings)


def test_a_vendored_tesser_package_is_not_the_tree() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("tesser/testing.py", "tesser.testing", "X = 1\n", False),
            ("conftest.py", "conftest", "import tesser.testing\n", False),
        ))).violations()
               )
    assert not any(
        "conftest imports tesser.testing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )


def test_a_root_module_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "helpers.py",
                "helpers",
                "import app.domain.thing\nimport enum\n",
                False,
            ),
        ))).violations()
               )
    assert any("helpers belongs to no governed package" in f for f in findings)
    assert any(
        "helpers imports app.domain.thing; "
        "a root module is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("helpers imports enum" in f for f in findings)


def test_a_root_conftest_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "conftest.py",
                "conftest",
                "import os\nimport sys\nimport app.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("imports os" in f for f in findings)


def test_a_protocol_module_imports_nothing_else_from_its_tree() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("serialization.py", "serialization", "X = 1\n", False),
            (
                "protocol/http.py",
                "protocol.http",
                "import tesser.srv as ts\nimport serialization\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "protocol.http imports serialization; "
        "a protocol module imports nothing else from its tree" in f
        for f in findings
    )


def test_a_norm_module_is_from_imported_where_its_placement_allows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "fine/domain/money.py",
                "fine.domain.money",
                "import tesser.domain as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = canonical_str(code)\n",
                False,
            ),
            (
                "whole/domain/money.py",
                "whole.domain.money",
                "import tesser.domain as ts\n"
                "import tesser.serialization\n"
                "class WholeSpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = code\n",
                False,
            ),
            (
                "appside/application/service.py",
                "appside.application.service",
                "import tesser.application as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class SideService(ts.ApplicationService):\n"
                "    def ask(self, code: str) -> str:\n"
                "        return canonical_str(code)\n",
                False,
            ),
            (
                "only/domain/money.py",
                "only.domain.money",
                "from tesser.serialization import canonical_str\n"
                "class OnlyMoney:\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = canonical_str(code)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("fine.domain.money" in f for f in findings)
    assert any(
        "whole.domain.money imports tesser.serialization whole; a norm module "
        "is from-imported by name, never whole — the ts alias belongs to the "
        "placement's own package" in f
        for f in findings
    )
    assert any(
        "appside.application.service imports tesser.serialization; "
        "an application module's tesser imports are "
        "tesser.application and tesser.errors" in f
        for f in findings
    )
    assert any(
        "only.domain.money never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )


def test_wiring_bootstrap_and_srv_may_from_import_tesser_lifecycle() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n"
                "from tesser.lifecycle import Closeable\n"
                "class Wiring(ts.Wiring):\n"
                "    def closeables(self) -> tuple[Closeable, ...]:\n"
                "        return ()\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "import tesser.context as ts\n"
                "from tesser.lifecycle import Closeable\n",
                False,
            ),
            (
                "srv/run.py",
                "srv.run",
                "import tesser.srv as ts\n"
                "from tesser.lifecycle import Closeable\n",
                False,
            ),
            (
                "astray/wiring/wire.py",
                "astray.wiring.wire",
                "import tesser.context as ts\n"
                "import tesser.domain\n"
                "class Wiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.wiring.wire" in f for f in findings)
    assert not any("bootstrap.wire" in f and "tesser.lifecycle" in f for f in findings)
    assert not any("srv.run" in f and "tesser.lifecycle" in f for f in findings)
    assert any(
        "astray.wiring.wire imports tesser.domain; "
        "a wiring module's tesser imports are tesser.context, "
        "tesser.errors, and tesser.lifecycle" in f
        for f in findings
    )


def test_any_role_but_client_may_from_import_tesser_errors() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/money.py",
                "app.domain.money",
                "import tesser.domain as ts\n"
                "from tesser.errors import invalid\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        if not code:\n"
                "            raise invalid(\"bad_code\", \"code is empty\")\n"
                "        self.code = code\n",
                False,
            ),
            (
                "app/application/views.py",
                "app.application.views",
                "import tesser.application as ts\n"
                "import app.client.client as client\n"
                "from tesser.errors import not_found\n"
                "class ViewService(ts.ApplicationService):\n"
                "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
                "        raise not_found(\"no_row\", request.text)\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "from tesser.errors import InfraError\n"
                "class MemoryGateway(ts.Gateway):\n"
                "    def load(self, key: str) -> str:\n"
                "        raise InfraError(key)\n",
                False,
            ),
            (
                "stray/client/client.py",
                "stray.client.client",
                "import tesser.context as ts\n"
                "from tesser.errors import invalid\n"
                "class AskRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "astray/adapters/gateways.py",
                "astray.adapters.gateways",
                "import tesser.adapters as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class StrayGateway(ts.Gateway):\n"
                "    def load(self, key: str) -> str:\n"
                "        return canonical_str(key)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.domain.money" in f for f in findings)
    assert not any("app.application.views" in f for f in findings)
    assert not any("app.adapters.gateways" in f for f in findings)
    assert any(
        "stray.client.client imports tesser.errors; "
        "a role module imports only its own tesser package" in f
        for f in findings
    )
    assert any(
        "astray.adapters.gateways imports tesser.serialization; "
        "an adapters module's tesser imports are "
        "tesser.adapters and tesser.errors" in f
        for f in findings
    )
