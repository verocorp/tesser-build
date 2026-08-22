from __future__ import annotations

import re
from typing import Final

import tesser.domain as ts

from tesser.serialization import canonical_str

READ: Final[str] = "read"

MISSING: Final[str] = "missing"

UNREADABLE: Final[str] = "unreadable"

MALFORMED: Final[str] = "malformed"

MISSHAPEN: Final[str] = "misshapen"

DIRECTORY: Final[str] = "directory"

SYMLINK: Final[str] = "symlink"

KIND_APP: Final[str] = "app"

KIND_UNGATED: Final[str] = "ungated"

KINDS: Final[frozenset[str]] = frozenset({KIND_APP, KIND_UNGATED})

DECLARATION: Final[str] = ".tesser-root"

REQUIREMENTS: Final[str] = "requirements-dev.txt"

ARM_SHAPE: Final[re.Pattern[str]] = re.compile(
    r"^\s*([a-z0-9-]+)\)\s+(run_[a-z0-9_]+)\s", re.MULTILINE
)


class Text(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("text must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class Problem(ts.ValueObject):

    _text: Text

    def __init__(self, text: str) -> None:
        object.__setattr__(self, "_text", Text(text))

    def text(self) -> Text:
        return self._text


class RepoRoot(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("repo root must be non-empty")
        if value.endswith("/") and value != "/":
            raise ValueError("repo root carries no trailing separator")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class RepoSpec(ts.Spec):

    def __init__(
        self,
        manifest: tuple[str, tuple[tuple[str, str], ...], str],
        verify: tuple[str, str],
        workflow: tuple[str, str],
        top: tuple[tuple[str, str], ...],
        examples: tuple[tuple[str, str], ...],
        declarations: tuple[tuple[str, str, str], ...],
        requirements: tuple[str, ...],
    ) -> None:
        self.manifest = manifest
        self.verify = verify
        self.workflow = workflow
        self.top = top
        self.examples = examples
        self.declarations = declarations
        self.requirements = requirements


class Repo(ts.AggregateRoot):

    def __init__(self, spec: RepoSpec) -> None:
        self._manifest = spec.manifest
        self._verify = spec.verify
        self._workflow = spec.workflow
        self._top = spec.top
        self._examples = spec.examples
        self._declarations = spec.declarations
        self._requirements = spec.requirements

    def problems(self) -> tuple[Problem, ...]:
        state, manifest_rows, note = self._manifest
        if state == MALFORMED:
            return (Problem(f"manifest.json is unreadable: {note}"),)
        if state == MISSHAPEN:
            return (
                Problem(
                    "manifest.json is not a flat object of directory-path to kind strings"
                ),
            )
        if state != READ:
            return (Problem(f"manifest.json is {state}"),)
        rows = dict(manifest_rows)
        found: list[Problem] = []
        found.extend(
            Problem(
                f"manifest.json row '{key}' declares unknown kind '{kind}'; "
                f"the kinds are 'app' and 'ungated'"
            )
            for key, kind in sorted(rows.items())
            if kind not in KINDS
        )
        top_rows = {key for key in rows if "/" not in key}
        top_disk = {name for name, _ in self._top}
        for name in sorted(top_disk - top_rows):
            found.append(
                Problem(
                    f"top-level directory '{name}' has no manifest.json row; "
                    f"every top-level directory declares what it is"
                )
            )
        for name in sorted(top_rows - top_disk):
            found.append(Problem(f"manifest.json row '{name}' names no directory on disk"))
        example_rows = {key.split("/", 1)[1] for key in rows if key.startswith("examples/")}
        example_disk = {name for name, _ in self._examples}
        for name in sorted(example_disk - example_rows):
            found.append(Problem(f"examples/{name} has no manifest.json row"))
        for name in sorted(example_rows - example_disk):
            found.append(
                Problem(f"manifest.json row 'examples/{name}' names no directory on disk")
            )
        entries = [(name, form) for name, form in sorted(self._top)]
        entries.extend((f"examples/{name}", form) for name, form in sorted(self._examples))
        for name, form in entries:
            if form == SYMLINK:
                found.append(
                    Problem(
                        f"{name} is a symlinked directory; "
                        f"a declared directory is a real one"
                    )
                )
        verify_state, verify_text = self._verify
        workflow_state, workflow_text = self._workflow
        if verify_state != READ:
            found.append(Problem(f"scripts/verify is {verify_state}"))
        if workflow_state != READ:
            found.append(Problem(f".github/workflows/test.yml is {workflow_state}"))
        arms = {match.group(1): match.group(2) for match in ARM_SHAPE.finditer(verify_text)}
        names: dict[str, str] = {}
        checked: set[str] = set()
        for key in sorted(key for key, kind in rows.items() if kind == KIND_APP):
            tree = key.split("/")[-1]
            if tree in names:
                found.append(
                    Problem(
                        f"'{key}' and '{names[tree]}' share the gate name '{tree}'; "
                        f"scripts/verify picks its steps by that name, so app "
                        f"directory names must be unique"
                    )
                )
            names[tree] = key
            if tree not in arms:
                found.append(Problem(f"{key} has no scripts/verify case arm for '{tree}'"))
            else:
                arm = re.search(
                    rf"^{arms[tree]}\(\) {{\n(.*?)^}}",
                    verify_text,
                    re.MULTILINE | re.DOTALL,
                )
                if "tessercheck_tree" in (arm.group(1) if arm else ""):
                    checked.add(f"{key}/{DECLARATION}")
            if not re.search(
                rf"^\s*run: scripts/verify {re.escape(tree)}\s*$",
                workflow_text,
                re.MULTILINE,
            ):
                found.append(Problem(f"{key} has no CI job step 'run: scripts/verify {tree}'"))
        on_disk = {path for path, _, _ in self._declarations}
        for path in sorted(on_disk - checked):
            found.append(
                Problem(
                    f"{path} declares a tree whose scripts/verify steps "
                    f"do not run tessercheck"
                )
            )
        for path in sorted(checked - on_disk):
            found.append(
                Problem(
                    f"{path} is missing; a tree that tessercheck runs on "
                    f"declares itself with {DECLARATION}"
                )
            )
        for path, declaration_state, text in sorted(self._declarations):
            if path not in checked:
                continue
            if declaration_state != READ:
                found.append(Problem(f"{path} does not declare 'app': {declaration_state}"))
                continue
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if not lines or lines[0] != KIND_APP:
                found.append(Problem(f"{path} does not declare 'app': first line is not 'app'"))
        found.extend(
            Problem(
                f"{key} holds a {REQUIREMENTS} but is not an app row; "
                f"a Python tree cannot sit outside the gates"
            )
            for key in sorted(self._requirements)
            if rows.get(key) != KIND_APP
        )
        return tuple(found)

    def trees(self) -> tuple[Text, ...]:
        state, manifest_rows, _ = self._manifest
        if state != READ:
            return ()
        rows = dict(manifest_rows)
        return tuple(
            Text(key.split("/")[-1])
            for key, kind in rows.items()
            if kind == KIND_APP and key.split("/")[-1]
        )

    def counts(self) -> tuple[Text, ...]:
        state, manifest_rows, _ = self._manifest
        if state != READ:
            return (Text("0"), Text("0"))
        rows = dict(manifest_rows)
        apps = sum(1 for kind in rows.values() if kind == KIND_APP)
        return (Text(str(len(rows))), Text(str(apps)))
