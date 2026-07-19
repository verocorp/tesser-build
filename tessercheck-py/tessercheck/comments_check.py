"""TB020 — the comments norm (v0, ``skills/tesser-build/comments.md``):
constructed-app code carries no comments, no docstrings, and no bare
string-literal statements (prose smuggled as a string). Machine directives
are exempt (instructions to tools, not prose): shebang, PEP 263 coding
declarations (lines 1-2 only — an unanchored "coding" exemption let prose
containing the word escape), ``type: ignore``, ``noqa``,
``tessercheck:ignore``, the tb-cell/tb-status/tb-allow-missing roadmap
marker grammar, ``pragma``, and formatter/linter control lines. The
exemption ledger grows only from discovered evidence — extend it in
``comments.md`` and here in the same change. Applies to test files too
(the norm has no test scope).
"""

import ast
import io
import re
import tokenize
from typing import TypeGuard

from tessercheck.finding import Finding

_DIRECTIVE = re.compile(
    r"^#\s*(!|type:|noqa|tessercheck:ignore|tb-(?:cell|status|allow-missing):"
    r"|pragma|fmt:|isort:|ruff:)"
)
_CODING_DECL = re.compile(r"^#.*?coding[:=]\s*[-\w.]+")
_SUPPRESS_MARKER = "# tessercheck:ignore"

_COMMENT_MSG = (
    "code comment is banned (zero-comment norm v0); delete it — if it states "
    "a real constraint, that belongs in the doc layer "
    "(skills/tesser-build/comments.md)"
)
_DOCSTRING_MSG = (
    "docstring is banned (zero-comment norm v0); delete it — the name, "
    "signature, and tests carry the meaning (skills/tesser-build/comments.md)"
)
_BARE_STRING_MSG = (
    "bare string-literal statement is banned (zero-comment norm v0) — a "
    "comment smuggled as a string is still a comment "
    "(skills/tesser-build/comments.md)"
)


def check_comments(path: str, source: str, tree: ast.Module) -> list[Finding]:
    """Every TB020 finding for one file: non-directive comments, docstrings,
    and bare string-literal statements anywhere in a body."""
    lines = source.splitlines()

    def suppressed(line: int) -> bool:
        return 1 <= line <= len(lines) and _SUPPRESS_MARKER in lines[line - 1]

    def exempt(tok: tokenize.TokenInfo) -> bool:
        if _DIRECTIVE.match(tok.string):
            return True
        # PEP 263 coding declarations are only meaningful on lines 1-2;
        # anywhere else, "coding" in a comment is just prose.
        return tok.start[0] <= 2 and bool(_CODING_DECL.match(tok.string))

    findings: list[Finding] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError) as err:
        # Fail loud, not silently comment-blind: a file that parses as AST but
        # defeats tokenize would otherwise pass the comment half of the norm.
        tokens = []
        findings.append(
            Finding(
                path,
                1,
                1,
                "TB020",
                f"source could not be tokenized ({err}); the comment scan is "
                "incomplete — fix the file's encoding/continuations",
            )
        )
    for tok in tokens:
        if tok.type != tokenize.COMMENT or exempt(tok):
            continue
        line, col = tok.start
        if suppressed(line):
            continue
        findings.append(Finding(path, line, col + 1, "TB020", _COMMENT_MSG))

    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        if node.body and _is_bare_string(node.body[0]):
            docstrings.add(id(node.body[0]))

    for node in ast.walk(tree):
        if not _is_bare_string(node) or suppressed(node.lineno):
            continue
        message = _DOCSTRING_MSG if id(node) in docstrings else _BARE_STRING_MSG
        findings.append(
            Finding(path, node.lineno, node.col_offset + 1, "TB020", message)
        )
    return findings


def _is_bare_string(node: ast.AST) -> TypeGuard[ast.Expr]:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )
