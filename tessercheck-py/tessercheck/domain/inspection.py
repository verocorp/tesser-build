from __future__ import annotations

import ast
import typing

import tesser.domain as ts
import tesser.errors as errors
import tesser.serialization as serialization

_SHELL_PACKAGES: typing.Final[frozenset[str]] = frozenset(
    {"app", "protocol", "srv", "web", "tests", "kernel", "__pycache__"}
)
_CONFIG_OWNERS: typing.Final[frozenset[str]] = frozenset({"cfg", "config"})


class InspectionPath(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class ContextNames(ts.ValueObject):
    _items: tuple[str, ...]

    def __init__(self, items: tuple[str, ...]) -> None:
        object.__setattr__(self, "_items", tuple(sorted(set(items))))

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._items)


class InspectionPaths(ts.ValueObject):
    _items: tuple[str, ...]

    def __init__(self, items: tuple[str, ...]) -> None:
        object.__setattr__(self, "_items", tuple(sorted(set(items))))

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._items)


class InspectionLines(ts.ValueObject):
    _items: tuple[int, ...]

    def __init__(self, items: tuple[int, ...]) -> None:
        object.__setattr__(self, "_items", tuple(sorted(set(items))))

    def __iter__(self) -> typing.Iterator[int]:
        return iter(self._items)


class ExportedNames(ts.ValueObject):
    _items: tuple[str, ...]

    def __init__(self, items: tuple[str, ...]) -> None:
        object.__setattr__(self, "_items", tuple(sorted(set(items))))

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._items)


class ModuleInspectionSpec(ts.Spec):
    def __init__(self, path: str, text: str, contexts: tuple[str, ...]) -> None:
        self.path = path
        self.text = text
        self.contexts = contexts


class ModuleInspection(ts.ValueObject):
    _path: InspectionPath
    _reached: ContextNames
    _calls: InspectionLines
    _top_level_calls: InspectionLines
    _exports: ExportedNames

    def __init__(self, spec: ModuleInspectionSpec) -> None:
        try:
            tree = ast.parse(spec.text)
        except SyntaxError as error:
            raise errors.invalid(
                "inspection_syntax", f"{spec.path}: {error.msg}"
            ) from error
        contexts = frozenset(spec.contexts)
        reached: set[str] = set()
        called: set[int] = set()
        top_level_calls = tuple(
            node.lineno
            for node in tree.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        )
        exported_names: set[str] = set()
        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom):
                exported_names.update(
                    alias.name
                    for alias in statement.names
                    if alias.name == alias.asname
                )
        module_aliases: dict[str, str] = {}
        pending: list[tuple[str, ast.AST, dict[str, str], dict[str, str], bool]] = [
            ("visit", tree, module_aliases, module_aliases, False)
        ]
        while pending:
            action, node, aliases, outer_aliases, in_class = pending.pop()
            if action == "bind":
                assigned: ast.expr | None = None
                targets: list[ast.expr] = []
                if isinstance(node, ast.Assign):
                    assigned, targets = node.value, list(node.targets)
                elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
                    assigned, targets = node.value, [node.target]
                elif isinstance(node, ast.AugAssign):
                    targets = [node.target]
                elif isinstance(node, ast.Delete):
                    targets = list(node.targets)
                elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                    targets = [node.target]
                elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                    targets = [node.optional_vars]
                elif isinstance(node, ast.ExceptHandler) and node.name is not None:
                    aliases.pop(node.name, None)
                elif isinstance(node, ast.match_case):
                    for capture in ast.walk(node.pattern):
                        if isinstance(capture, (ast.MatchAs, ast.MatchStar)) and capture.name is not None:
                            aliases.pop(capture.name, None)
                        elif isinstance(capture, ast.MatchMapping) and capture.rest is not None:
                            aliases.pop(capture.rest, None)
                context: str | None = None
                if isinstance(assigned, ast.Attribute) and assigned.attr in contexts:
                    if not (
                        isinstance(assigned.value, ast.Name)
                        and assigned.value.id in _CONFIG_OWNERS
                    ):
                        context = assigned.attr
                elif isinstance(assigned, ast.Name):
                    context = aliases.get(assigned.id)
                for target in targets:
                    for bound in ast.walk(target):
                        if isinstance(bound, ast.Name) and isinstance(
                            bound.ctx, (ast.Store, ast.Del)
                        ):
                            aliases.pop(bound.id, None)
                    if isinstance(target, ast.Name) and context is not None:
                        aliases[target.id] = context
                continue
            if isinstance(node, ast.Attribute) and node.attr in contexts:
                if not (
                    isinstance(node.value, ast.Name) and node.value.id in _CONFIG_OWNERS
                ):
                    reached.add(node.attr)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                if isinstance(owner, ast.Attribute) and owner.attr in contexts:
                    if not (
                        isinstance(owner.value, ast.Name)
                        and owner.value.id in _CONFIG_OWNERS
                    ):
                        called.add(node.lineno)
                elif isinstance(owner, ast.Name) and owner.id in aliases:
                    called.add(node.lineno)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                inherited = dict(outer_aliases if in_class else aliases)
                body: list[ast.AST] = (
                    [node.body] if isinstance(node, ast.Lambda) else list(node.body)
                )
                locals_to_scan: list[ast.AST] = list(body)
                local_names = {
                    argument.arg
                    for argument in node.args.posonlyargs
                    + node.args.args
                    + node.args.kwonlyargs
                }
                global_names: set[str] = set()
                nonlocal_names: set[str] = set()
                for argument in (node.args.vararg, node.args.kwarg):
                    if argument is not None:
                        local_names.add(argument.arg)
                while locals_to_scan:
                    local = locals_to_scan.pop()
                    if isinstance(
                        local, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    ):
                        local_names.add(local.name)
                        continue
                    if isinstance(local, ast.Lambda):
                        continue
                    if isinstance(local, ast.comprehension):
                        locals_to_scan.extend([local.iter, *local.ifs])
                        continue
                    if isinstance(local, ast.Global):
                        global_names.update(local.names)
                    if isinstance(local, ast.Nonlocal):
                        nonlocal_names.update(local.names)
                    if isinstance(local, ast.ExceptHandler) and local.name is not None:
                        local_names.add(local.name)
                    if isinstance(local, (ast.MatchAs, ast.MatchStar)) and local.name is not None:
                        local_names.add(local.name)
                    if isinstance(local, ast.MatchMapping) and local.rest is not None:
                        local_names.add(local.rest)
                    if isinstance(local, ast.Name) and isinstance(
                        local.ctx, (ast.Store, ast.Del)
                    ):
                        local_names.add(local.id)
                    if isinstance(local, (ast.Import, ast.ImportFrom)):
                        local_names.update(
                            alias.asname or alias.name.split(".")[0]
                            for alias in local.names
                        )
                    locals_to_scan.extend(ast.iter_child_nodes(local))
                for local_name in local_names - global_names - nonlocal_names:
                    inherited.pop(local_name, None)
                for global_name in global_names:
                    inherited.pop(global_name, None)
                    if global_name in module_aliases:
                        inherited[global_name] = module_aliases[global_name]
                pending.extend(
                    ("visit", child, inherited, inherited, False)
                    for child in reversed(body)
                )
                outside_body = [
                    child for child in ast.iter_child_nodes(node) if child not in body
                ]
                pending.extend(
                    ("visit", child, aliases, outer_aliases, in_class)
                    for child in reversed(outside_body)
                )
                if not isinstance(node, ast.Lambda):
                    aliases.pop(node.name, None)
                continue
            if isinstance(node, ast.ClassDef):
                inherited = dict(aliases)
                pending.extend(
                    ("visit", child, inherited, aliases, True)
                    for child in reversed(node.body)
                )
                outside_body = [
                    child
                    for child in ast.iter_child_nodes(node)
                    if child not in node.body
                ]
                pending.extend(
                    ("visit", child, aliases, outer_aliases, in_class)
                    for child in reversed(outside_body)
                )
                aliases.pop(node.name, None)
                continue
            if isinstance(
                node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ):
                inherited = dict(outer_aliases if in_class else aliases)
                sequence: list[
                    tuple[str, ast.AST, dict[str, str], dict[str, str], bool]
                ] = []
                for index, generator in enumerate(node.generators):
                    sequence.append(
                        (
                            "visit",
                            generator.iter,
                            aliases if index == 0 else inherited,
                            outer_aliases,
                            in_class,
                        )
                    )
                    sequence.append(("bind", generator, inherited, inherited, False))
                    sequence.extend(
                        ("visit", condition, inherited, inherited, False)
                        for condition in generator.ifs
                    )
                elements = (
                    [node.key, node.value]
                    if isinstance(node, ast.DictComp)
                    else [node.elt]
                )
                sequence.extend(
                    ("visit", element, inherited, inherited, False)
                    for element in elements
                )
                pending.extend(reversed(sequence))
                continue
            if isinstance(node, (ast.For, ast.AsyncFor)):
                pending.extend(
                    ("visit", statement, aliases, outer_aliases, in_class)
                    for statement in reversed(node.body + node.orelse)
                )
                pending.append(("bind", node, aliases, outer_aliases, in_class))
                pending.append(("visit", node.iter, aliases, outer_aliases, in_class))
                continue
            if isinstance(node, ast.ExceptHandler):
                pending.extend(
                    ("visit", statement, aliases, outer_aliases, in_class)
                    for statement in reversed(node.body)
                )
                pending.append(("bind", node, aliases, outer_aliases, in_class))
                if node.type is not None:
                    pending.append(
                        ("visit", node.type, aliases, outer_aliases, in_class)
                    )
                continue
            if isinstance(node, ast.match_case):
                pending.extend(
                    ("visit", statement, aliases, outer_aliases, in_class)
                    for statement in reversed(node.body)
                )
                if node.guard is not None:
                    pending.append(("visit", node.guard, aliases, outer_aliases, in_class))
                pending.append(("bind", node, aliases, outer_aliases, in_class))
                pending.append(("visit", node.pattern, aliases, outer_aliases, in_class))
                continue
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    aliases.pop(alias.asname or alias.name.split(".")[0], None)
            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.NamedExpr,
                    ast.AugAssign,
                    ast.Delete,
                    ast.withitem,
                ),
            ):
                pending.append(("bind", node, aliases, outer_aliases, in_class))
            pending.extend(
                ("visit", child, aliases, outer_aliases, in_class)
                for child in reversed(list(ast.iter_child_nodes(node)))
            )
        object.__setattr__(self, "_path", InspectionPath(spec.path))
        object.__setattr__(self, "_reached", ContextNames(tuple(reached)))
        object.__setattr__(self, "_calls", InspectionLines(tuple(called)))
        object.__setattr__(self, "_top_level_calls", InspectionLines(top_level_calls))
        object.__setattr__(self, "_exports", ExportedNames(tuple(exported_names)))

    def path(self) -> InspectionPath:
        return self._path

    def reached(self) -> ContextNames:
        return self._reached

    def calls(self) -> InspectionLines:
        return self._calls

    def top_level_calls(self) -> InspectionLines:
        return self._top_level_calls

    def exports(self) -> ExportedNames:
        return self._exports


class TreeInspectionSpec(ts.Spec):
    def __init__(
        self,
        sources: tuple[tuple[str, str | None], ...],
        directories: tuple[str, ...],
        declared: bool,
        unreadable_directories: tuple[str, ...],
    ) -> None:
        self.sources = sources
        self.directories = directories
        self.declared = declared
        self.unreadable_directories = unreadable_directories


class TreeInspection(ts.ValueObject):
    _contexts: ContextNames
    _unclassified: ContextNames
    _directories: InspectionPaths
    _modules: tuple[ModuleInspection, ...]

    def __init__(self, spec: TreeInspectionSpec) -> None:
        if not spec.declared:
            raise errors.invalid(
                "inspection_undeclared",
                "inspection requires a standalone app tree without nested declarations or symlinked directories",
            )
        if spec.unreadable_directories:
            raise errors.invalid(
                "inspection_unreadable",
                f"directories cannot be read: {', '.join(spec.unreadable_directories)}",
            )
        sources: dict[str, str] = {}
        trees: dict[str, ast.Module] = {}
        for path, text in spec.sources:
            if text is None:
                raise errors.invalid(
                    "inspection_unreadable", f"{path}: source is unreadable"
                )
            sources[path] = text
            try:
                trees[path] = ast.parse(text)
            except SyntaxError as error:
                raise errors.invalid(
                    "inspection_syntax", f"{path}: {error.msg}"
                ) from error
        contexts: list[str] = []
        unclassified: list[str] = []
        for directory in sorted(spec.directories):
            if (
                "/" in directory
                or directory.startswith(".")
                or directory in _SHELL_PACKAGES
            ):
                continue
            client_package = f"{directory}/client"
            candidates = (
                [
                    path
                    for path in sources
                    if path.rsplit("/", 1)[0] == client_package and path.endswith(".py")
                ]
                if client_package in spec.directories
                else [f"{directory}/client.py"]
            )
            exposes_client = False
            for candidate in candidates:
                if candidate not in trees:
                    continue
                for node in ast.walk(trees[candidate]):
                    if isinstance(node, ast.ImportFrom):
                        exposes_client |= any(
                            (alias.asname or alias.name).endswith("Client")
                            for alias in node.names
                        )
                    if isinstance(node, ast.ClassDef):
                        exposes_client |= node.name.endswith("Client")
            if exposes_client:
                contexts.append(directory)
            else:
                unclassified.append(directory)
        object.__setattr__(self, "_contexts", ContextNames(tuple(contexts)))
        object.__setattr__(self, "_unclassified", ContextNames(tuple(unclassified)))
        object.__setattr__(self, "_directories", InspectionPaths(spec.directories))
        object.__setattr__(
            self,
            "_modules",
            tuple(
                ModuleInspection(
                    ModuleInspectionSpec(path=path, text=text, contexts=tuple(contexts))
                )
                for path, text in sorted(sources.items())
            ),
        )

    def contexts(self) -> ContextNames:
        return self._contexts

    def unclassified(self) -> ContextNames:
        return self._unclassified

    def directories(self) -> InspectionPaths:
        return self._directories

    def modules(self) -> tuple[ModuleInspection, ...]:
        return self._modules
