from __future__ import annotations

import tesser.testing as ts

import tessercheck.application.ports as ports
import tessercheck.application as application
import tessercheck.client as client


@ts.fake
class FakeSourceReader(ports.SourceReader):
    def __init__(self, root: ports.RootForm) -> None:
        self.root = root
        self.roots: list[str] = []

    def sources(
        self, read_sources_request: ports.ReadSourcesRequest
    ) -> ports.ReadSourcesResponse:
        self.roots.append(read_sources_request.tree)
        return ports.ReadSourcesResponse(
            root=self.root,
            nested=(),
            symlinked=(),
            sources=(),
            exports=(),
            imports=(),
            stdlib=(),
            pure_stdlib=(),
        )


@ts.fake
class FakeSourceWriter(ports.SourceWriter):
    def __init__(self) -> None:
        self.written: list[tuple[str, str]] = []

    def write(
        self, write_sources_request: ports.WriteSourcesRequest
    ) -> ports.WriteSourcesResponse:
        for source in write_sources_request.sources:
            self.written.append((source.path, source.text))
        return ports.WriteSourcesResponse(written=len(write_sources_request.sources))


@ts.fake
class FakeRulebookSources(ports.RulebookSources):
    def __init__(self, checks_text: str) -> None:
        self.checks_text = checks_text
        self.roots: list[str] = []

    def read(
        self, read_rulebook_request: ports.ReadRulebookRequest
    ) -> ports.ReadRulebookResponse:
        self.roots.append(read_rulebook_request.tree)
        return ports.ReadRulebookResponse(
            checks_text=self.checks_text,
            test_modules=(),
            contracts_text="[importlinter:contract:pure]\nname = domain stays pure\n",
        )


@ts.fake
class FakePreparedReader(ports.SourceReader):
    def __init__(self, read_sources_response: ports.ReadSourcesResponse) -> None:
        self.read_sources_response = read_sources_response

    def sources(
        self, read_sources_request: ports.ReadSourcesRequest
    ) -> ports.ReadSourcesResponse:
        return self.read_sources_response


@ts.fake
class FakeScriptedReader(ports.SourceReader):
    def __init__(self, *responses: ports.ReadSourcesResponse) -> None:
        self.responses = responses
        self.reads = 0

    def sources(
        self, read_sources_request: ports.ReadSourcesRequest
    ) -> ports.ReadSourcesResponse:
        self.reads += 1
        return self.responses[min(self.reads, len(self.responses)) - 1]


@ts.helper
def _tree_of(text: str = "import os\n") -> ports.ReadSourcesResponse:
    return ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            ports.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text=text,
                state=ports.SourceState.READ,
                form=ports.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=("os",),
        pure_stdlib=(),
    )


def test_a_mark_hands_the_writer_the_line_the_finding_names() -> None:
    fake_source_writer = FakeSourceWriter()
    tessercheck_service = application.TessercheckService(
        FakePreparedReader(_tree_of("import os\n")),
        fake_source_writer,
        FakeRulebookSources(""),
    )
    tessercheck_service.mark(client.MarkRequest(tree="."))
    assert len(fake_source_writer.written) == 1
    path, text = fake_source_writer.written[0]
    assert path == "shop/domain/thing.py"
    assert text.startswith("import os  # tesser:debt TB0")


def test_what_a_mark_reports_as_remaining_is_what_a_check_would_report_after_it() -> None:
    read_sources_response = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    fake_scripted_reader = FakeScriptedReader(
        _tree_of("import os\n"), read_sources_response
    )
    tessercheck_service = application.TessercheckService(
        fake_scripted_reader, FakeSourceWriter(), FakeRulebookSources("")
    )
    mark_response = tessercheck_service.mark(client.MarkRequest(tree="."))
    assert fake_scripted_reader.reads == 2
    assert mark_response.files == 1
    assert mark_response.remaining == ()


def test_a_tree_declaration_finding_is_reported_rather_than_marked() -> None:
    fake_source_writer = FakeSourceWriter()
    tessercheck_service = application.TessercheckService(
        FakeSourceReader(ports.RootForm.MISSING), fake_source_writer, FakeRulebookSources("")
    )
    mark_response = tessercheck_service.mark(client.MarkRequest(tree="."))
    assert fake_source_writer.written == []
    assert mark_response.files == 0
    assert len(mark_response.remaining) == 1
    assert "TB044" in mark_response.remaining[0]


def test_a_symlinked_directory_is_reported_rather_than_marked() -> None:
    fake_source_writer = FakeSourceWriter()
    read_sources_response = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=("app/vendored",),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    tessercheck_service = application.TessercheckService(
        FakePreparedReader(read_sources_response),
        fake_source_writer,
        FakeRulebookSources(""),
    )
    mark_response = tessercheck_service.mark(client.MarkRequest(tree="."))
    assert fake_source_writer.written == []
    assert any("TB045" in finding for finding in mark_response.remaining)


def test_a_stale_marker_is_reported_rather_than_marked_again() -> None:
    fake_source_writer = FakeSourceWriter()
    tessercheck_service = application.TessercheckService(
        FakePreparedReader(_tree_of("held = 1  # tesser:debt TB023\n")),
        fake_source_writer,
        FakeRulebookSources(""),
    )
    mark_response = tessercheck_service.mark(client.MarkRequest(tree="."))
    _, text = fake_source_writer.written[0]
    assert "TB023" in text
    assert "TB090" not in text
    assert any("TB090" in finding for finding in mark_response.remaining)


def test_the_requested_root_reaches_the_source_reader() -> None:
    fake_source_reader = FakeSourceReader(ports.RootForm.APP)
    tessercheck_service = application.TessercheckService(fake_source_reader, FakeSourceWriter(), FakeRulebookSources(""))
    tessercheck_service.check(client.CheckRequest(tree="some/tree"))
    assert fake_source_reader.roots == ["some/tree"]


def test_a_declared_empty_tree_answers_with_no_findings() -> None:
    tessercheck_service = application.TessercheckService(
        FakeSourceReader(ports.RootForm.APP), FakeSourceWriter(), FakeRulebookSources("")
    )
    check_response = tessercheck_service.check(client.CheckRequest(tree="."))
    assert check_response.findings == ()


def test_an_undeclared_tree_answers_with_the_declaration_finding() -> None:
    tessercheck_service = application.TessercheckService(
        FakeSourceReader(ports.RootForm.MISSING), FakeSourceWriter(), FakeRulebookSources("")
    )
    check_response = tessercheck_service.check(client.CheckRequest(tree="."))
    assert len(check_response.findings) == 1
    assert "TB044" in check_response.findings[0]


def test_the_rulebook_never_reaches_the_source_reader() -> None:
    fake_source_reader = FakeSourceReader(ports.RootForm.APP)
    fake_rulebook_sources = FakeRulebookSources(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the served tail'))\n"
    )
    tessercheck_service = application.TessercheckService(fake_source_reader, FakeSourceWriter(), fake_rulebook_sources)
    tessercheck_service.rulebook(client.RulebookRequest(tree="some/tree"))
    assert fake_source_reader.roots == []
    assert fake_rulebook_sources.roots == ["some/tree"]


def test_the_rulebook_answer_carries_the_rendered_rules_and_contracts() -> None:
    fake_rulebook_sources = FakeRulebookSources(
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the served tail'))\n"
    )
    tessercheck_service = application.TessercheckService(
        FakeSourceReader(ports.RootForm.APP), FakeSourceWriter(), fake_rulebook_sources
    )
    rulebook_response = tessercheck_service.rulebook(client.RulebookRequest(tree="."))
    assert "| TB020 | the served tail | every module |" in rulebook_response.rendered
    assert "| pure | domain stays pure |" in rulebook_response.rendered


def test_a_declared_tree_of_conforming_modules_yields_no_findings() -> None:
    read_sources_response = ports.ReadSourcesResponse(
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
    assert application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings == ()


def test_an_undeclared_tree_is_the_only_thing_reported() -> None:
    read_sources_response = ports.ReadSourcesResponse(
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
    found = application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings
    assert len(found) == 1
    assert "TB044" in found[0]


def test_every_root_form_other_than_app_is_reported() -> None:
    for form in (
        ports.RootForm.MISSING,
        ports.RootForm.UNREADABLE,
        ports.RootForm.UNRECOGNIZED,
    ):
        read_sources_response = ports.ReadSourcesResponse(
            root=form,
            nested=(),
            symlinked=(),
            sources=(),
            exports=(),
            imports=(),
            stdlib=(),
            pure_stdlib=(),
        )
        found = application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings
        assert len(found) == 1
        assert "TB044" in found[0]


def test_a_symlinked_directory_from_the_read_is_reported() -> None:
    read_sources_response = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=(),
        symlinked=("app/vendored",),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    found = application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings
    assert any("TB045" in finding and "app/vendored" in finding for finding in found)


def test_a_nested_declaration_from_the_read_is_reported() -> None:
    read_sources_response = ports.ReadSourcesResponse(
        root=ports.RootForm.APP,
        nested=("app/.tesser-root",),
        symlinked=(),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
        pure_stdlib=(),
    )
    found = application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings
    assert any("app/.tesser-root" in finding for finding in found)


def test_a_finding_reads_path_line_code_then_message() -> None:
    read_sources_response = ports.ReadSourcesResponse(
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
    found = application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings
    assert found != ()
    head, _, rest = found[0].partition(": ")
    assert head == "shop/domain/thing.py:1"
    assert rest.split(" ")[0].startswith("TB0")


def test_an_unreadable_source_is_reported_rather_than_read_as_empty() -> None:
    read_sources_response = ports.ReadSourcesResponse(
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
    found = application.TessercheckService(FakePreparedReader(read_sources_response), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings
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
    assert application.TessercheckService(FakePreparedReader(as_package), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings == ()
    assert application.TessercheckService(FakePreparedReader(as_module), FakeSourceWriter(), FakeRulebookSources('')).check(client.CheckRequest(tree='.')).findings != ()

