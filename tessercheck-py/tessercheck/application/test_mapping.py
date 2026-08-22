from __future__ import annotations

import tessercheck.application.mapping as mapping
import tessercheck.application.ports.source_reader as source_reader


def test_a_declared_tree_of_conforming_modules_yields_no_findings() -> None:
    read = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            source_reader.SourceFile(
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
                state=source_reader.SourceState.READ,
                form=source_reader.ModuleForm.MODULE,
            ),
            source_reader.SourceFile(
                path="shop/domain/test_thing.py",
                name="shop.domain.test_thing",
                text=("def test_thing_exists() -> None:\n    assert True\n"),
                state=source_reader.SourceState.READ,
                form=source_reader.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
    )
    assert mapping.findings(read) == ()


def test_an_undeclared_tree_is_the_only_thing_reported() -> None:
    read = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.MISSING,
        nested=(),
        symlinked=(),
        sources=(
            source_reader.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text="import os\n",
                state=source_reader.SourceState.READ,
                form=source_reader.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=("os",),
    )
    found = mapping.findings(read)
    assert len(found) == 1
    assert "TB044" in found[0]


def test_every_root_form_other_than_app_is_reported() -> None:
    for form in (
        source_reader.RootForm.MISSING,
        source_reader.RootForm.UNREADABLE,
        source_reader.RootForm.UNRECOGNIZED,
    ):
        read = source_reader.ReadSourcesResponse(
            root=form,
            nested=(),
            symlinked=(),
            sources=(),
            exports=(),
            imports=(),
            stdlib=(),
        )
        found = mapping.findings(read)
        assert len(found) == 1
        assert "TB044" in found[0]


def test_a_symlinked_directory_from_the_read_is_reported() -> None:
    read = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=(),
        symlinked=("app/vendored",),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
    )
    found = mapping.findings(read)
    assert any("TB045" in finding and "app/vendored" in finding for finding in found)


def test_a_nested_declaration_from_the_read_is_reported() -> None:
    read = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=("app/.tesser-root",),
        symlinked=(),
        sources=(),
        exports=(),
        imports=(),
        stdlib=(),
    )
    found = mapping.findings(read)
    assert any("app/.tesser-root" in finding for finding in found)


def test_a_finding_reads_path_line_code_then_message() -> None:
    read = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            source_reader.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text="import os\n",
                state=source_reader.SourceState.READ,
                form=source_reader.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=("os",),
    )
    found = mapping.findings(read)
    assert found != ()
    head, _, rest = found[0].partition(": ")
    assert head == "shop/domain/thing.py:1"
    assert rest.split(" ")[0].startswith("TB0")


def test_an_unreadable_source_is_reported_rather_than_read_as_empty() -> None:
    read = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            source_reader.SourceFile(
                path="shop/domain/thing.py",
                name="shop.domain.thing",
                text="",
                state=source_reader.SourceState.UNREADABLE,
                form=source_reader.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
    )
    found = mapping.findings(read)
    assert any("shop/domain/thing.py" in finding for finding in found)


def test_the_package_form_of_a_source_changes_the_judgement() -> None:
    as_package = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            source_reader.SourceFile(
                path="shop/domain/__init__.py",
                name="shop.domain",
                text="",
                state=source_reader.SourceState.READ,
                form=source_reader.ModuleForm.PACKAGE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
    )
    as_module = source_reader.ReadSourcesResponse(
        root=source_reader.RootForm.APP,
        nested=(),
        symlinked=(),
        sources=(
            source_reader.SourceFile(
                path="shop/domain/__init__.py",
                name="shop.domain",
                text="",
                state=source_reader.SourceState.READ,
                form=source_reader.ModuleForm.MODULE,
            ),
        ),
        exports=(),
        imports=(),
        stdlib=(),
    )
    assert mapping.findings(as_package) == ()
    assert mapping.findings(as_module) != ()

