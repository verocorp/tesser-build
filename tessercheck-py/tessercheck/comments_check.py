"""TB020 — the comments norm (v0, ``skills/tesser-build/comments.md``):
constructed-app code carries no comments and no docstrings. Machine
directives are exempt (instructions to tools, not prose): shebang, coding
lines, ``type: ignore``, ``noqa``, ``tessercheck:ignore``, the
tb-cell/tb-status/tb-allow-missing roadmap marker grammar, ``pragma``, and
formatter/linter control lines. The exemption ledger grows only from
discovered evidence — extend it in ``comments.md`` and here in the same
change. Applies to test files too (the norm has no test scope).
"""

import ast
import io
import re
import tokenize

from tessercheck.finding import Finding

_DIRECTIVE = re.compile(
    r"^#\s*(!|.*coding[:=]|type:|noqa|tessercheck:ignore|tb-cell|tb-status"
    r"|tb-allow-missing|pragma|fmt:|isort:|ruff:)"
)
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


def check_comments(path: str, source: str, tree: ast.Module) -> list[Finding]:
    """Every TB020 finding for one file: non-directive comments + docstrings."""
    lines = source.splitlines()

    def suppressed(line: int) -> bool:
        return 1 <= line <= len(lines) and _SUPPRESS_MARKER in lines[line - 1]

    findings: list[Finding] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError):
        tokens = []
    for tok in tokens:
        if tok.type != tokenize.COMMENT or _DIRECTIVE.match(tok.string):
            continue
        line, col = tok.start
        if suppressed(line):
            continue
        findings.append(Finding(path, line, col + 1, "TB020", _COMMENT_MSG))

    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and not suppressed(first.lineno)
        ):
            findings.append(
                Finding(path, first.lineno, first.col_offset + 1, "TB020", _DOCSTRING_MSG)
            )
    return findings
