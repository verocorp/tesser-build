"""TB033 — a shadowed builtin that the same scope then calls.

The bug, not the name. Binding a builtin's name is harmless on its own —
``def load(self, id: str)`` and a spec field called ``id`` both leave ``id()``
working everywhere a human writes code. What breaks is binding the name **and
then calling it in the same scope**:

* the binding is a parameter — ``def f(id: str): return id(x)`` raises
  ``TypeError: 'str' object is not callable``;
* the binding is a local — ``len = 0`` then ``len(name)`` in the same function
  raises the same thing.

Order does not matter and no flow analysis is needed, which is what makes this
decidable from one pass. Python decides scope per *function*, not per
statement: any assignment to ``len`` anywhere in a body makes ``len`` local for
the **whole** body, so a call placed *earlier* than the assignment raises
``UnboundLocalError`` rather than reaching the builtin. Either way the code is
broken, so the presence of a binding plus the presence of a call is the whole
signal.

**Why the call is the discriminator.** A bound name and an intended-builtin
reference are the *same AST node* — inside ``def load(self, id)``, every ``id``
is the parameter, and that is exactly what the author meant. There is no way to
tell a deliberate parameter reference from a mistaken builtin one. A *call* is
different: calling a name that has been bound to a string or an int is either
intent to reach the builtin or an immediate crash, so it is the one shape that
distinguishes a bug from a naming preference.

This is deliberately **not** the name-based ban. Ruff's ``A001``/``A002``
(flake8-builtins) already implements that, and on this repo it flags four sites
including ``log_message(self, format, *args)`` — a
``BaseHTTPRequestHandler`` override whose signature the stdlib fixes, so
complying would mean breaking the override. Nothing off the shelf checks the
call-collision shape, which is why this check exists (Chris ruling 2026-07-26).

**Known holes.**

* A **nested function** that calls a builtin its *enclosing* function bound sees
  the closure variable, not the builtin. Each scope is analyzed on its own here,
  so that case is not reported.
* A **callable binding** legitimately called — ``def apply(filter, xs): return
  filter(xs)`` — is reported, because a parameter's annotation is not consulted.
  There are zero instances in the gated trees; if one appears it takes
  ``# tessercheck:ignore``.
"""

import ast
import builtins
import io
import tokenize

from tessercheck.finding import Finding

_SUPPRESS_MARKER = "# tessercheck:ignore"

_BUILTINS: frozenset[str] = frozenset(
    name for name in dir(builtins) if not name.startswith("_")
)

_MSG = (
    "{name!r} is bound here and called as a builtin in the same scope — the "
    "call reaches the binding, not the builtin ({failure}). Rename the "
    "binding; a builtin name is only a problem when the scope also calls it, "
    "so a field or parameter merely named {name!r} is fine"
)


def _suppressed_lines(source: str) -> frozenset[int]:
    try:
        return frozenset(
            token.start[0]
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if token.type == tokenize.COMMENT and _SUPPRESS_MARKER in token.string
        )
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return frozenset()


def _bound_names(node: ast.AST) -> set[str]:
    """Builtin names this scope binds: parameters, and every assignment target
    that is a plain name. Nested scopes are excluded — they bind their own."""
    bound: set[str] = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        args = node.args
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if arg.arg in _BUILTINS:
                bound.add(arg.arg)
        for extra in (args.vararg, args.kwarg):
            if extra is not None and extra.arg in _BUILTINS:
                bound.add(extra.arg)

    declared_elsewhere: set[str] = set()
    for child in _own_scope(node):
        # ``global x`` / ``nonlocal x`` mean the binding is NOT local, so the
        # call's target depends on execution order the way a module-level
        # rebind does — undecidable here. Drop the name rather than report it.
        if isinstance(child, (ast.Global, ast.Nonlocal)):
            declared_elsewhere.update(child.names)
        # ``except E as name`` binds ``name`` for the handler body. The alias is
        # a plain str on the handler, not a Name node, so the target walk below
        # never sees it.
        if isinstance(child, ast.ExceptHandler) and child.name in _BUILTINS:
            bound.add(child.name)

    for child in _own_scope(node):
        targets: list[ast.expr] = []
        if isinstance(child, ast.Assign):
            targets = list(child.targets)
        elif isinstance(child, (ast.AnnAssign, ast.AugAssign)):
            targets = [child.target]
        elif isinstance(child, (ast.For, ast.AsyncFor)):
            targets = [child.target]
        elif isinstance(child, ast.NamedExpr):
            targets = [child.target]
        elif isinstance(child, ast.withitem):
            targets = [child.optional_vars] if child.optional_vars else []
        for target in targets:
            for name in ast.walk(target):
                # Store context only. A subscript target descends into its own
                # index expression, so ``self._by_id[str(c.id)] = rec`` would
                # otherwise read the ``str`` call in the index as a binding —
                # measured as 4 false positives on the example trees before this
                # narrowed. That statement binds nothing; the Subscript carries
                # the Store and the names inside the index are Loads.
                if (
                    isinstance(name, ast.Name)
                    and isinstance(name.ctx, ast.Store)
                    and name.id in _BUILTINS
                ):
                    bound.add(name.id)
    return bound - declared_elsewhere


def _scope_roots(node: ast.AST) -> list[ast.AST]:
    """The expressions that actually EXECUTE inside ``node``'s scope.

    For a function this is its body and nothing else. A parameter default, a
    decorator, and an annotation are evaluated in the ENCLOSING scope, at
    definition time, where the parameter does not exist yet — so
    ``def f(len=len("ab"))`` calls the builtin and must not be reported. Walking
    ``iter_child_nodes`` swept those in and produced exactly that false positive.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return list(node.body)
    if isinstance(node, ast.Lambda):
        return [node.body]
    if isinstance(node, ast.Module):
        return list(node.body)
    return list(ast.iter_child_nodes(node))


def _own_scope(node: ast.AST) -> list[ast.AST]:
    """Every descendant belonging to ``node``'s own scope — nested function and
    class bodies are pruned, because their names resolve separately."""
    out: list[ast.AST] = []
    stack: list[ast.AST] = list(_scope_roots(node))
    while stack:
        child = stack.pop()
        if isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            continue
        out.append(child)
        stack.extend(ast.iter_child_nodes(child))
    return out


def _calls(node: ast.AST) -> list[ast.Call]:
    return [
        child
        for child in _own_scope(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
    ]


def check_shadowing(path: str, source: str, tree: ast.Module) -> list[Finding]:
    """Every TB033 finding for one file: a builtin bound and called in one scope."""
    marked = _suppressed_lines(source)
    findings: list[Finding] = []

    scopes: list[ast.AST] = [tree]
    scopes.extend(
        node
        for node in ast.walk(tree)
        # A lambda and a class body are scopes too. A class body in particular
        # executes at IMPORT time, so ``len = 0`` followed by ``len("a")`` there
        # breaks the module for every importer.
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
        )
    )

    for scope in scopes:
        bound = _bound_names(scope)
        if not bound:
            continue
        for call in _calls(scope):
            assert isinstance(call.func, ast.Name)
            name = call.func.id
            if name not in bound or call.lineno in marked:
                continue
            failure = (
                "TypeError if the binding runs first, UnboundLocalError if it "
                "does not"
            )
            findings.append(
                Finding(
                    path,
                    call.lineno,
                    call.col_offset + 1,
                    "TB033",
                    _MSG.format(name=name, failure=failure),
                )
            )
    return findings
