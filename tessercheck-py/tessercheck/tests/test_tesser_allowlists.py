import json
import pathlib

import tessercheck.adapters.repositories as repositories
import tessercheck.application.ports as ports
import tessercheck.domain as domain


def test_every_tesser_allowlist_entry_is_earned_by_the_shipped_distribution() -> None:
    repo = pathlib.Path(__file__).resolve().parents[3]
    manifest = json.loads((repo / "manifest.json").read_text(encoding="utf-8"))
    filesystem_source_reader = repositories.FilesystemSourceReader()
    for key, kind in sorted(manifest.items()):
        if kind != "app" or not (repo / key / ".tesser-root").is_file():
            continue
        read_sources_response = filesystem_source_reader.sources(ports.ReadSourcesRequest(tree=str(repo / key)))
        if read_sources_response.exports != (domain.TESSER,):
            continue
        names = [source.name for source in read_sources_response.sources]
        members = frozenset(
            name.split(".")[1]
            for name in names
            if name.split(".")[0] == domain.TESSER and len(name.split(".")) >= 2
        )
        unearned = domain.TESSER_NAMESPACES - members
        assert unearned == frozenset(), (
            f"TESSER_NAMESPACES allows {sorted(unearned)}, but the shipped "
            "distribution has no such member; an allowance the checker grants "
            "only itself is how context-main lived unnoticed for six releases"
        )
        heads = frozenset(
            imported.split(".")[0]
            for source in read_sources_response.sources
            if source.name.split(".")[0] == domain.TESSER
            for line in source.text.splitlines()
            for imported in (
                [line.split()[1]]
                if line.startswith("import ")
                else [line.split()[1]]
                if line.startswith("from ")
                else []
            )
        )
        stale = domain.TESSER_STDLIB - heads
        assert stale == frozenset(), (
            f"TESSER_STDLIB allows {sorted(stale)}, but no shell module imports "
            "it; the allowlist is the distribution's measured surface, not a grant"
        )
        return
    raise AssertionError(
        "no checked tree exports tesser; this test must run from the "
        "tesser-build repo checkout"
    )
