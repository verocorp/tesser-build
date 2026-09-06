from __future__ import annotations

import tesser.testing as ts

import tessercheck.application.ports as ports
import tessercheck.application.service as service
import tessercheck.client as client


@ts.fake
class FakeSourceReader(ports.SourceReader):
    def __init__(self, root: ports.RootForm) -> None:
        self.form = root
        self.roots: list[str] = []

    def sources(
        self, request: ports.ReadSourcesRequest
    ) -> ports.ReadSourcesResponse:
        self.roots.append(request.tree)
        return ports.ReadSourcesResponse(
            root=self.form,
            nested=(),
            symlinked=(),
            sources=(),
            exports=(),
            imports=(),
            stdlib=(),
            pure_stdlib=(),
        )


@ts.fake
class FakeRulebookSources(ports.RulebookSources):
    def __init__(self, checks_text: str) -> None:
        self.checks_text = checks_text
        self.roots: list[str] = []

    def read(
        self, request: ports.ReadRulebookRequest
    ) -> ports.ReadRulebookResponse:
        self.roots.append(request.tree)
        return ports.ReadRulebookResponse(
            checks_text=self.checks_text,
            test_modules=(),
            contracts_text="[importlinter:contract:pure]\nname = domain stays pure\n",
        )


def test_the_requested_root_reaches_the_source_reader() -> None:
    reader = FakeSourceReader(ports.RootForm.APP)
    checker = service.TessercheckService(reader, FakeRulebookSources(""))
    checker.check(client.CheckRequest(tree="some/tree"))
    assert reader.roots == ["some/tree"]


def test_a_declared_empty_tree_answers_with_no_findings() -> None:
    checker = service.TessercheckService(
        FakeSourceReader(ports.RootForm.APP), FakeRulebookSources("")
    )
    response = checker.check(client.CheckRequest(tree="."))
    assert response.findings == ()


def test_an_undeclared_tree_answers_with_the_declaration_finding() -> None:
    checker = service.TessercheckService(
        FakeSourceReader(ports.RootForm.MISSING), FakeRulebookSources("")
    )
    response = checker.check(client.CheckRequest(tree="."))
    assert len(response.findings) == 1
    assert "TB044" in response.findings[0]


def test_the_rulebook_never_reaches_the_source_reader() -> None:
    reader = FakeSourceReader(ports.RootForm.APP)
    sources = FakeRulebookSources(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the served tail'))\n"
    )
    checker = service.TessercheckService(reader, sources)
    checker.rulebook(client.RulebookRequest(tree="some/tree"))
    assert reader.roots == []
    assert sources.roots == ["some/tree"]


def test_the_rulebook_answer_carries_the_rendered_rules_and_contracts() -> None:
    sources = FakeRulebookSources(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the served tail'))\n"
    )
    checker = service.TessercheckService(
        FakeSourceReader(ports.RootForm.APP), sources
    )
    response = checker.rulebook(client.RulebookRequest(tree="."))
    assert "| TB020 | the served tail | every module |" in response.rendered
    assert "| pure | domain stays pure |" in response.rendered


def test_a_declared_tree_of_conforming_modules_yields_no_findings() -> None:
    read = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text=(
                    "import tesser.domain as ts\n"
                    "class ThingSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n"
                    "class Thing(ts.AggregateRoot):\n"
                    "    def __init__(self, spec: ThingSpec) -> None:\n"
                    "        self.text = spec.text\n"
                ),
                state=ports.SourceState.READ,
                form=ports.ModuleForm.MODULE,
            ),
            ports.SourceFile(
                path="shop/domain/test_thing.py",
                name="shop.domain.test_thing",
                text=("def test_thing_exists() -> None:\n    assert True\n"),
                state=ports.SourceState.READ,
                form=ports.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    assert service.MapToCheckResponse(read=read).findings == ()


def test_an_undeclared_tree_is_the_only_thing_reported() -> None:
    read = ports.ReadSourcesResponse(
        root=ports.RootForm.MISSING,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text="import os\n",
                state=ports.SourceState.READ,
                form=ports.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=("os",),
        pure_stdlib=(),
    )
    found = service.MapToCheckResponse(read=read).findings
    assert len(found) == 1
    assert "TB044" in found[0]


def test_every_root_form_other_than_app_is_reported() -> None:
    for form in (
        ports.RootForm.MISSING,
        ports.RootForm.UNREADABLE,
        ports.RootForm.UNRECOGNIZED,
    ):
        read = ports.ReadSourcesResponse(
            root=form,
            nested=(),
            symlinked=(),
            sources=(),
            exports=(),
            imports=(),
            stdlib=(),
            pure_stdlib=(),
        )
        found = service.MapToCheckResponse(read=read).findings
        assert len(found) == 1
        assert "TB044" in found[0]


def test_a_symlinked_directory_from_the_read_is_reported() -> None:
    read = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=("app/vendored",),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    found = service.MapToCheckResponse(read=read).findings
    assert any("TB045" in finding and "app/vendored" in finding for finding in found)


def test_a_nested_declaration_from_the_read_is_reported() -> None:
    read = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=("app/.tesser-root",),
        symlinked=(),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    found = service.MapToCheckResponse(read=read).findings
    assert any("app/.tesser-root" in finding for finding in found)


def test_a_finding_reads_path_line_code_then_message() -> None:
    read = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text="import os\n",
                state=ports.SourceState.READ,
                form=ports.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=("os",),
        pure_stdlib=(),
    )
    found = service.MapToCheckResponse(read=read).findings
    assert found != ()
    head, _, rest = found[0].partition(": ")
    assert head == "shop/domain/thing.py:1"
    assert rest.split(" ")[0].startswith("TB0")


def test_an_unreadable_source_is_reported_rather_than_read_as_empty() -> None:
    read = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text="",
                state=ports.SourceState.UNREADABLE,
                form=ports.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    found = service.MapToCheckResponse(read=read).findings
    assert any("shop/domain/thing.py" in finding for finding in found)


def test_the_package_form_of_a_source_changes_the_judgement() -> None:
    as_package = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/__init__.py",
                name="shop.domain",
                text="",
                state=ports.SourceState.READ,
                form=ports.ModuleForm.PACKAGE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    as_module = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/__init__.py",
                name="shop.domain",
                text="",
                state=ports.SourceState.READ,
                form=ports.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    assert service.MapToCheckResponse(read=as_package).findings == ()
    assert service.MapToCheckResponse(read=as_module).findings != ()

