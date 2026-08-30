from __future__ import annotations

import enum
import re
import typing

import tesser.domain as ts

import tesser.serialization as serialization

READ: typing.Final[str] = "read"

MISSING: typing.Final[str] = "missing"

UNREADABLE: typing.Final[str] = "unreadable"

MALFORMED: typing.Final[str] = "malformed"

MISSHAPEN: typing.Final[str] = "misshapen"

UNDECLARED: typing.Final[str] = "undeclared"

DIRECTORY: typing.Final[str] = "directory"

SYMLINK: typing.Final[str] = "symlink"

KIND_APP: typing.Final[str] = "app"

KIND_UNGATED: typing.Final[str] = "ungated"

KINDS: typing.Final[frozenset[str]] = frozenset({KIND_APP, KIND_UNGATED})

MANIFEST: typing.Final[str] = "manifest.json"

VERIFY: typing.Final[str] = "scripts/verify"

WORKFLOW: typing.Final[str] = ".github/workflows/test.yml"

DECLARATION: typing.Final[str] = ".tesser-root"

REQUIREMENTS: typing.Final[str] = "requirements-dev.txt"

FLOOR: typing.Final[str] = "3.12"

REQUIRES_PYTHON: typing.Final[str] = "requires-python"

TARGET_VERSION: typing.Final[str] = "target-version"

FLOOR_LITERALS: typing.Final[dict[str, str]] = {
    REQUIRES_PYTHON: f">={FLOOR}",
    TARGET_VERSION: f"py{FLOOR.replace('.', '')}",
}

ARM_SHAPE: typing.Final[re.Pattern[str]] = re.compile(
    r"^\s*([a-z0-9-]+)\)\s+(run_[a-z0-9_]+)\s", re.MULTILINE
)

PYTHON_PIN: typing.Final[re.Pattern[str]] = re.compile(
    r"^\s*python-version:\s*(.+)$", re.MULTILINE
)

VERSION_TOKEN: typing.Final[re.Pattern[str]] = re.compile(r"\d+\.\d+")


class Rule(enum.Enum):

    MANIFEST_MISSING = "manifest_missing"
    MANIFEST_UNREADABLE = "manifest_unreadable"
    MANIFEST_MALFORMED = "manifest_malformed"
    MANIFEST_MISSHAPEN = "manifest_misshapen"
    UNKNOWN_KIND = "unknown_kind"
    UNREGISTERED_TOP_LEVEL = "unregistered_top_level"
    UNREGISTERED_EXAMPLE = "unregistered_example"
    ROW_WITHOUT_DIRECTORY = "row_without_directory"
    SYMLINKED_DIRECTORY = "symlinked_directory"
    VERIFY_UNAVAILABLE = "verify_unavailable"
    WORKFLOW_UNAVAILABLE = "workflow_unavailable"
    SHARED_GATE_NAME = "shared_gate_name"
    NO_VERIFY_ARM = "no_verify_arm"
    NO_CI_JOB = "no_ci_job"
    DECLARATION_UNCHECKED = "declaration_unchecked"
    DECLARATION_MISSING = "declaration_missing"
    DECLARATION_UNAVAILABLE = "declaration_unavailable"
    DECLARATION_NOT_APP = "declaration_not_app"
    REQUIREMENTS_OUTSIDE_APP = "requirements_outside_app"
    REQUIRES_PYTHON_UNDECLARED = "requires_python_undeclared"
    TARGET_VERSION_UNDECLARED = "target_version_undeclared"
    FLOOR_FILE_UNAVAILABLE = "floor_file_unavailable"
    REQUIRES_PYTHON_BELOW_FLOOR = "requires_python_below_floor"
    TARGET_VERSION_BELOW_FLOOR = "target_version_below_floor"
    WORKFLOW_PIN_BELOW_FLOOR = "workflow_pin_below_floor"


class Health(ts.Outcome):

    CLEAN = enum.auto()
    PROBLEMS = enum.auto()


class Presence(ts.Outcome):

    ONLY = enum.auto()
    AMONG = enum.auto()
    ABSENT = enum.auto()


class Text(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("text must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Subject(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Note(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class ProblemSpec(ts.Spec):

    def __init__(self, rule: Rule, subject: str, note: str = "") -> None:
        self.rule = rule
        self.subject = subject
        self.note = note


class Problem(ts.ValueObject):

    _rule: Rule
    _subject: Subject
    _note: Note

    def __init__(self, spec: ProblemSpec) -> None:
        object.__setattr__(self, "_rule", spec.rule)
        object.__setattr__(self, "_subject", Subject(spec.subject))
        object.__setattr__(self, "_note", Note(spec.note))

    def subject(self) -> Subject:
        return self._subject

    def note(self) -> Note:
        return self._note

    def text(self) -> Text:
        subject = str(self._subject)
        note = str(self._note)
        tree = subject.split("/")[-1]
        match self._rule:
            case Rule.MANIFEST_MISSING:
                return Text(f"{subject} is {MISSING}")
            case Rule.MANIFEST_UNREADABLE:
                return Text(f"{subject} is {UNREADABLE}")
            case Rule.MANIFEST_MALFORMED:
                return Text(f"{subject} is {UNREADABLE}: {note}")
            case Rule.MANIFEST_MISSHAPEN:
                return Text(f"{subject} is not a flat object of directory-path to kind strings")
            case Rule.UNKNOWN_KIND:
                return Text(
                    f"{MANIFEST} row '{subject}' declares unknown kind '{note}'; "
                    f"the kinds are '{KIND_APP}' and '{KIND_UNGATED}'"
                )
            case Rule.UNREGISTERED_TOP_LEVEL:
                return Text(
                    f"top-level directory '{subject}' has no {MANIFEST} row; "
                    f"every top-level directory declares what it is"
                )
            case Rule.UNREGISTERED_EXAMPLE:
                return Text(f"{subject} has no {MANIFEST} row")
            case Rule.ROW_WITHOUT_DIRECTORY:
                return Text(f"{MANIFEST} row '{subject}' names no directory on disk")
            case Rule.SYMLINKED_DIRECTORY:
                return Text(f"{subject} is a symlinked directory; a declared directory is a real one")
            case Rule.VERIFY_UNAVAILABLE:
                return Text(f"{subject} is {note}")
            case Rule.WORKFLOW_UNAVAILABLE:
                return Text(f"{subject} is {note}")
            case Rule.SHARED_GATE_NAME:
                return Text(
                    f"'{subject}' and '{note}' share the gate name '{tree}'; "
                    f"{VERIFY} picks its steps by that name, so app "
                    f"directory names must be unique"
                )
            case Rule.NO_VERIFY_ARM:
                return Text(f"{subject} has no {VERIFY} case arm for '{tree}'")
            case Rule.NO_CI_JOB:
                return Text(f"{subject} has no CI job step 'run: {VERIFY} {tree}'")
            case Rule.DECLARATION_UNCHECKED:
                return Text(
                    f"{subject} declares a tree whose {VERIFY} steps do not run tessercheck"
                )
            case Rule.DECLARATION_MISSING:
                return Text(
                    f"{subject} is missing; a tree that tessercheck runs on "
                    f"declares itself with {DECLARATION}"
                )
            case Rule.DECLARATION_UNAVAILABLE:
                return Text(f"{subject} does not declare '{KIND_APP}': {note}")
            case Rule.DECLARATION_NOT_APP:
                return Text(
                    f"{subject} does not declare '{KIND_APP}': first line is not '{KIND_APP}'"
                )
            case Rule.REQUIREMENTS_OUTSIDE_APP:
                return Text(
                    f"{subject} holds a {REQUIREMENTS} but is not an app row; "
                    f"a Python tree cannot sit outside the gates"
                )
            case Rule.REQUIRES_PYTHON_UNDECLARED:
                return Text(
                    f"{subject} declares a distribution without {REQUIRES_PYTHON}; "
                    f"every distribution states the Python floor as "
                    f"'{FLOOR_LITERALS[REQUIRES_PYTHON]}'"
                )
            case Rule.TARGET_VERSION_UNDECLARED:
                return Text(
                    f"{subject} declares a distribution without {TARGET_VERSION}; "
                    f"every distribution states the Python floor as "
                    f"'{FLOOR_LITERALS[TARGET_VERSION]}'"
                )
            case Rule.FLOOR_FILE_UNAVAILABLE:
                return Text(f"{subject} is {note}")
            case Rule.REQUIRES_PYTHON_BELOW_FLOOR:
                return Text(
                    f"{subject} states {REQUIRES_PYTHON} = '{note}'; the Python floor "
                    f"is {FLOOR}, so it reads '{FLOOR_LITERALS[REQUIRES_PYTHON]}'"
                )
            case Rule.TARGET_VERSION_BELOW_FLOOR:
                return Text(
                    f"{subject} states {TARGET_VERSION} = '{note}'; the Python floor "
                    f"is {FLOOR}, so it reads '{FLOOR_LITERALS[TARGET_VERSION]}'"
                )
            case Rule.WORKFLOW_PIN_BELOW_FLOOR:
                return Text(
                    f"{subject} pins python-version {note}, below the Python floor {FLOOR}"
                )
            case _ as unreachable:
                typing.assert_never(unreachable)


class RepoRoot(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("repo root must be non-empty")
        if value.endswith("/") and value != "/":
            raise ValueError("repo root carries no trailing separator")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


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
        floors: tuple[tuple[str, str, str, str], ...],
    ) -> None:
        self.manifest = manifest
        self.verify = verify
        self.workflow = workflow
        self.top = top
        self.examples = examples
        self.declarations = declarations
        self.requirements = requirements
        self.floors = floors


class Repo(ts.AggregateRoot):

    def __init__(self, spec: RepoSpec) -> None:
        self._manifest = spec.manifest
        self._verify = spec.verify
        self._workflow = spec.workflow
        self._top = spec.top
        self._examples = spec.examples
        self._declarations = spec.declarations
        self._requirements = spec.requirements
        self._floors = spec.floors
        state, manifest_rows, note = self._manifest
        found: list[Problem] = []
        if state == MALFORMED:
            found.append(Problem(ProblemSpec(Rule.MANIFEST_MALFORMED, MANIFEST, note)))
        elif state == MISSHAPEN:
            found.append(Problem(ProblemSpec(Rule.MANIFEST_MISSHAPEN, MANIFEST)))
        elif state == MISSING:
            found.append(Problem(ProblemSpec(Rule.MANIFEST_MISSING, MANIFEST)))
        elif state != READ:
            found.append(Problem(ProblemSpec(Rule.MANIFEST_UNREADABLE, MANIFEST)))
        else:
            rows = dict(manifest_rows)
            found.extend(
                Problem(ProblemSpec(Rule.UNKNOWN_KIND, key, kind))
                for key, kind in sorted(rows.items())
                if kind not in KINDS
            )
            top_rows = {key for key in rows if "/" not in key}
            top_disk = {name for name, _ in self._top}
            for name in sorted(top_disk - top_rows):
                found.append(Problem(ProblemSpec(Rule.UNREGISTERED_TOP_LEVEL, name)))
            for name in sorted(top_rows - top_disk):
                found.append(Problem(ProblemSpec(Rule.ROW_WITHOUT_DIRECTORY, name)))
            example_rows = {key.split("/", 1)[1] for key in rows if key.startswith("examples/")}
            example_disk = {name for name, _ in self._examples}
            for name in sorted(example_disk - example_rows):
                found.append(Problem(ProblemSpec(Rule.UNREGISTERED_EXAMPLE, f"examples/{name}")))
            for name in sorted(example_rows - example_disk):
                found.append(Problem(ProblemSpec(Rule.ROW_WITHOUT_DIRECTORY, f"examples/{name}")))
            entries = [(name, form) for name, form in sorted(self._top)]
            entries.extend((f"examples/{name}", form) for name, form in sorted(self._examples))
            for name, form in entries:
                if form == SYMLINK:
                    found.append(Problem(ProblemSpec(Rule.SYMLINKED_DIRECTORY, name)))
            verify_state, verify_text = self._verify
            workflow_state, workflow_text = self._workflow
            if verify_state != READ:
                found.append(Problem(ProblemSpec(Rule.VERIFY_UNAVAILABLE, VERIFY, verify_state)))
            if workflow_state != READ:
                found.append(Problem(ProblemSpec(Rule.WORKFLOW_UNAVAILABLE, WORKFLOW, workflow_state)))
            arms = {match.group(1): match.group(2) for match in ARM_SHAPE.finditer(verify_text)}
            names: dict[str, str] = {}
            checked: set[str] = set()
            for key in sorted(key for key, kind in rows.items() if kind == KIND_APP):
                tree = key.split("/")[-1]
                if tree in names:
                    found.append(Problem(ProblemSpec(Rule.SHARED_GATE_NAME, key, names[tree])))
                names[tree] = key
                if tree not in arms:
                    found.append(Problem(ProblemSpec(Rule.NO_VERIFY_ARM, key)))
                else:
                    arm = re.search(
                        rf"^{arms[tree]}\(\) {{\n(.*?)^}}",
                        verify_text,
                        re.MULTILINE | re.DOTALL,
                    )
                    if "tessercheck_tree" in (arm.group(1) if arm else ""):
                        checked.add(f"{key}/{DECLARATION}")
                if not re.search(
                    rf"^\s*run: {re.escape(VERIFY)} {re.escape(tree)}\s*$",
                    workflow_text,
                    re.MULTILINE,
                ):
                    found.append(Problem(ProblemSpec(Rule.NO_CI_JOB, key)))
            on_disk = {path for path, _, _ in self._declarations}
            for path in sorted(on_disk - checked):
                found.append(Problem(ProblemSpec(Rule.DECLARATION_UNCHECKED, path)))
            for path in sorted(checked - on_disk):
                found.append(Problem(ProblemSpec(Rule.DECLARATION_MISSING, path)))
            for path, declaration_state, text in sorted(self._declarations):
                if path not in checked:
                    continue
                if declaration_state != READ:
                    found.append(
                        Problem(ProblemSpec(Rule.DECLARATION_UNAVAILABLE, path, declaration_state))
                    )
                    continue
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if not lines or lines[0] != KIND_APP:
                    found.append(Problem(ProblemSpec(Rule.DECLARATION_NOT_APP, path)))
            found.extend(
                Problem(ProblemSpec(Rule.REQUIREMENTS_OUTSIDE_APP, key))
                for key in sorted(self._requirements)
                if rows.get(key) != KIND_APP
            )
            undeclared = {
                REQUIRES_PYTHON: Rule.REQUIRES_PYTHON_UNDECLARED,
                TARGET_VERSION: Rule.TARGET_VERSION_UNDECLARED,
            }
            below = {
                REQUIRES_PYTHON: Rule.REQUIRES_PYTHON_BELOW_FLOOR,
                TARGET_VERSION: Rule.TARGET_VERSION_BELOW_FLOOR,
            }
            for path, floor_key, floor_state, value in sorted(self._floors):
                literal = FLOOR_LITERALS[floor_key]
                if floor_state == UNDECLARED:
                    found.append(Problem(ProblemSpec(undeclared[floor_key], path)))
                elif floor_state != READ:
                    found.append(Problem(ProblemSpec(Rule.FLOOR_FILE_UNAVAILABLE, path, floor_state)))
                elif value.replace(" ", "") != literal:
                    found.append(Problem(ProblemSpec(below[floor_key], path, value)))
            floor_parts = tuple(int(part) for part in FLOOR.split("."))
            found.extend(
                Problem(ProblemSpec(Rule.WORKFLOW_PIN_BELOW_FLOOR, WORKFLOW, token))
                for pin in PYTHON_PIN.finditer(workflow_text)
                for token in VERSION_TOKEN.findall(pin.group(1))
                if tuple(int(part) for part in token.split(".")) < floor_parts
            )
        self._problems = tuple(found)

    def health(self) -> Health:
        return Health.PROBLEMS if self._problems else Health.CLEAN

    def presence(self, spec: ProblemSpec) -> Presence:
        sought = Problem(spec)
        if sought not in self._problems:
            return Presence.ABSENT
        if all(problem == sought for problem in self._problems):
            return Presence.ONLY
        return Presence.AMONG

    def problems(self) -> tuple[Problem, ...]:
        return self._problems

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
