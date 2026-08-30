from __future__ import annotations

import tesser.testing as ts

import tessercheck.application.ports.rulebook_sources as rulebook_sources
import tessercheck.application.ports.source_reader as source_reader
import tessercheck.application.service as service
import tessercheck.client.client as client


@ts.fake
class FakeSourceReader(source_reader.SourceReader):
    def __init__(self, root: source_reader.RootForm) -> None:
        self.form = root
        self.roots: list[str] = []

    def sources(
        self, request: source_reader.ReadSourcesRequest
    ) -> source_reader.ReadSourcesResponse:
        self.roots.append(request.tree)
        return source_reader.ReadSourcesResponse(
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
class FakeRulebookSources(rulebook_sources.RulebookSources):
    def __init__(self, checks_text: str) -> None:
        self.checks_text = checks_text
        self.roots: list[str] = []

    def read(
        self, request: rulebook_sources.ReadRulebookRequest
    ) -> rulebook_sources.ReadRulebookResponse:
        self.roots.append(request.tree)
        return rulebook_sources.ReadRulebookResponse(
            checks_text=self.checks_text,
            test_modules=(),
            contracts_text="[importlinter:contract:pure]\nname = domain stays pure\n",
        )


def test_the_requested_root_reaches_the_source_reader() -> None:
    reader = FakeSourceReader(source_reader.RootForm.APP)
    checker = service.TessercheckService(reader, FakeRulebookSources(""))
    checker.check(client.CheckRequest(tree="some/tree"))
    assert reader.roots == ["some/tree"]


def test_a_declared_empty_tree_answers_with_no_findings() -> None:
    checker = service.TessercheckService(
        FakeSourceReader(source_reader.RootForm.APP), FakeRulebookSources("")
    )
    response = checker.check(client.CheckRequest(tree="."))
    assert response.findings == ()


def test_an_undeclared_tree_answers_with_the_declaration_finding() -> None:
    checker = service.TessercheckService(
        FakeSourceReader(source_reader.RootForm.MISSING), FakeRulebookSources("")
    )
    response = checker.check(client.CheckRequest(tree="."))
    assert len(response.findings) == 1
    assert "TB044" in response.findings[0]


def test_the_rulebook_never_reaches_the_source_reader() -> None:
    reader = FakeSourceReader(source_reader.RootForm.APP)
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
        FakeSourceReader(source_reader.RootForm.APP), sources
    )
    response = checker.rulebook(client.RulebookRequest(tree="."))
    assert "| TB020 | the served tail | every module |" in response.rendered
    assert "| pure | domain stays pure |" in response.rendered
