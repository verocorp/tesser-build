from __future__ import annotations

import pathlib

import tessercheck.client as tessercheck_client
import tessercheck.component as tessercheck_component


def test_no_top_level_expression_calls_in_contexts_or_bootstrap() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    offenders = {
        source.path: source.top_level_calls for source in inspect_tree_response.sources
        if source.path.split("/")[0] in (*inspect_tree_response.contexts, "bootstrap") and source.top_level_calls
    }
    assert not offenders, f"module-level expression calls: {offenders}"


def test_a_context_a_host_exposes_owns_a_handler() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    exposed = {
        context for source in inspect_tree_response.sources if source.path.startswith("srv/")
        for context in source.reached_contexts
    }
    assert exposed, "no context is reachable from a host — the walk found nothing"
    missing = sorted(context for context in exposed if f"{context}/adapters/handlers" not in inspect_tree_response.directories)
    assert not missing, f"a host exposes these contexts but they own no handler role: {missing}"


def test_a_host_routes_and_never_translates() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    inspect_tree_response = tessercheck_component.Tessercheck(
        tessercheck_component.Config(tessercheck_component.Spec())
    ).client.inspect_tree(tessercheck_client.InspectTreeRequest(tree=str(root)))
    offenders = {
        source.path: source.client_calls for source in inspect_tree_response.sources
        if source.path.startswith("srv/") and source.client_calls
    }
    assert not offenders, f"a host calls a context Client instead of routing to a handler: {offenders}"
