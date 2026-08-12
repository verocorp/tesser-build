"""The ``# tesser-category:`` vocabulary — the one parser TB020 and TB032
both read, and the reason the split between them is shape-vs-name.
"""

import ast

import pytest

from tessercheck.comments_check import check_comments
from tessercheck.markers import (
    CATEGORIES,
    CATEGORY_PREFIX,
    category_list,
    declared_category,
    is_known_category,
)


def _tb020(src: str) -> list[str]:
    return [f.code for f in check_comments("m.py", src, ast.parse(src))]


@pytest.mark.parametrize(
    ("comment", "expected"),
    [
        ("# tesser-category: spec", "spec"),
        ("#tesser-category:spec", "spec"),
        ("#   tesser-category:   fixture   ", "fixture"),
        ("# tesser-category: spce", "spce"),
        ("# tesser-category:", ""),
    ],
)
def test_declared_category_returns_the_raw_name_valid_or_not(
    comment: str, expected: str
) -> None:
    # Returning the raw name rather than validating here is what lets the
    # caller tell "you misspelled a category" from "this is not a marker".
    # Collapsing the two would make the typo diagnosis impossible.
    assert declared_category(comment) == expected


@pytest.mark.parametrize(
    "comment",
    [
        "# noqa",
        "# tessercheck:ignore",
        "# a comment mentioning tesser-category: spec mid-sentence",
        "# tesser-categories: spec",
        "",
    ],
)
def test_declared_category_is_none_for_a_non_marker(comment: str) -> None:
    assert declared_category(comment) is None


def test_declared_category_rejects_trailing_prose() -> None:
    # The marker is a whole comment, not a prefix a sentence can ride on.
    # Without the end anchor, "# tesser-category: spec because it builds one"
    # would parse as the category "spec" and smuggle prose past TB020 under a
    # directive's cover.
    assert declared_category("# tesser-category: spec because it builds one") is None


def test_every_category_is_known_and_nothing_else_is() -> None:
    for name in CATEGORIES:
        assert is_known_category(name)
    assert not is_known_category("client")
    assert not is_known_category("")


def test_category_list_renders_the_closed_set_sorted() -> None:
    # This string goes into a diagnostic telling an author what they may write,
    # so it must be the actual set, not a hand-maintained copy of it.
    assert category_list() == ", ".join(sorted(CATEGORIES))
    for name in CATEGORIES:
        assert name in category_list()


def test_tb020_exemption_runs_through_the_same_parser_tb032_uses() -> None:
    # The coupling this module exists to create. TB020 does not pattern-match the
    # marker itself — it asks declared_category, the same function TB032 asks —
    # so the two can never disagree about what a marker is, and renaming the
    # marker in one place cannot leave the other honoring the old spelling.
    assert _tb020(f"x = 1  # {CATEGORY_PREFIX} spec\n") == []
    assert _tb020("x = 1  # tesser-categorized: spec\n") == ["TB020"]
