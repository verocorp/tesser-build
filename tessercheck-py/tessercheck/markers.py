"""The ``# tesser-category:`` marker vocabulary — one closed set, two readers.

A test-file function that TB032 cannot classify structurally declares what it is
with ``# tesser-category: <name>``. Two checkers read that marker and they must
not disagree, which is why the vocabulary lives here rather than in either of
them:

* :mod:`tessercheck.comments_check` (TB020) exempts anything :func:`declared_category`
  recognizes as a marker — the SHAPE, not a valid name;
* :mod:`tessercheck.helpers_check` (TB032) validates that name against
  :data:`CATEGORIES` and reports a typo itself.

Both go through :func:`declared_category`, so they cannot disagree about what a
marker is. Splitting shape from name is deliberate, in both directions. If TB020
exempted only *valid* names, ``# tesser-category: spce`` would report twice —
once as a banned comment and once as an unknown category — and the comments-norm
finding would be the misleading one, pointing an author at prose they did not
write. If instead TB020 exempted a bare *prefix*, then
``# tesser-category: spec because it builds one`` would be ordinary prose using a
directive as cover, and the comments norm would have a hole in it.

The set is closed and small on purpose. TB032 is a totality check: every
function in a test file must classify, and what does not classify is flagged.
The flags are the worklist, so a category is added when a shape earns one from
evidence — never to silence a flag that is telling the truth.
"""

import re

CATEGORY_PREFIX = "tesser-category:"

# The closed set. ``spec`` and ``dto`` are the two shapes a helper is allowed to
# build (a helper never returns a constructed domain object); ``fixture`` is a
# pytest fixture factory. All three are normally detected structurally — the
# marker is for the cases detection cannot reach, such as a return annotation
# that names a type defined in a test file, which the classifier registry
# deliberately does not hold.
CATEGORIES: frozenset[str] = frozenset({"spec", "dto", "fixture"})

_CATEGORY_MARKER = re.compile(
    rf"^#\s*{re.escape(CATEGORY_PREFIX)}\s*(?P<name>\S*)\s*$"
)


def declared_category(comment: str) -> str | None:
    """The name in a ``# tesser-category:`` comment, valid or not.

    Returns ``None`` when the comment is not a category marker at all. A
    *malformed* marker (missing or unknown name) returns the raw text so the
    caller can report the typo precisely; validating here would collapse
    "not a marker" and "a marker with a bad name" into the same answer, and
    those need different diagnostics.
    """
    match = _CATEGORY_MARKER.match(comment.strip())
    if match is None:
        return None
    return match.group("name")


def is_known_category(name: str) -> bool:
    """True when ``name`` is in the closed set."""
    return name in CATEGORIES


def category_list() -> str:
    """The closed set, rendered for a diagnostic message."""
    return ", ".join(sorted(CATEGORIES))
