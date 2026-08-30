from __future__ import annotations

import pytest
import tesser.testing as ts

import repo.domain.rules as rules


@ts.helper
def _spec(
    manifest: tuple[str, tuple[tuple[str, str], ...], str] = (
        "read",
        (
            (".github", "ungated"),
            ("appone", "app"),
            ("docs", "ungated"),
            ("examples", "ungated"),
            ("examples/demo", "ungated"),
            ("libby", "app"),
            ("scripts", "ungated"),
        ),
        "",
    ),
    verify: tuple[str, str] = (
        "read",
        "run_appone() {\n"
        "  tessercheck_tree . || return 1\n"
        "}\n"
        "run_libby() {\n"
        "  mypy || return 1\n"
        "}\n"
        "run_tree() {\n"
        '  case "$1" in\n'
        "    appone)   run_appone ;;\n"
        "    libby)    run_libby ;;\n"
        "  esac\n"
        "}\n",
    ),
    workflow: tuple[str, str] = (
        "read",
        "jobs:\n"
        "  appone:\n"
        "    steps:\n"
        "      - name: gate\n"
        "        run: scripts/verify appone\n"
        "  libby:\n"
        "    steps:\n"
        "      - name: gate\n"
        "        run: scripts/verify libby\n",
    ),
    top: tuple[tuple[str, str], ...] = (
        (".github", "directory"),
        ("appone", "directory"),
        ("docs", "directory"),
        ("examples", "directory"),
        ("libby", "directory"),
        ("scripts", "directory"),
    ),
    examples: tuple[tuple[str, str], ...] = (("demo", "directory"),),
    declarations: tuple[tuple[str, str, str], ...] = (
        ("appone/.tesser-root", "read", "app\n"),
    ),
    requirements: tuple[str, ...] = ("appone", "libby"),
    floors: tuple[tuple[str, str, str, str], ...] = (
        ("libby/pyproject.toml", "requires-python", "read", ">=3.12"),
        ("libby/ruff.toml", "target-version", "read", "py312"),
    ),
) -> rules.RepoSpec:
    return rules.RepoSpec(
        manifest=manifest,
        verify=verify,
        workflow=workflow,
        top=top,
        examples=examples,
        declarations=declarations,
        requirements=requirements,
        floors=floors,
    )


def test_a_consistent_repo_has_no_problems() -> None:
    assert rules.Repo(_spec()).health() is rules.Health.CLEAN


def test_an_unknown_kind_is_a_problem() -> None:
    rows = _spec().manifest[1][:5] + (("libby", "python-library"), ("scripts", "ungated"))
    repo = rules.Repo(_spec(manifest=("read", rows, "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.UNKNOWN_KIND, "libby", "python-library"))

    assert presence is rules.Presence.AMONG


def test_a_top_level_dir_without_a_row_is_a_problem() -> None:
    top = _spec().top + (("utils", "directory"),)
    repo = rules.Repo(_spec(top=top))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.UNREGISTERED_TOP_LEVEL, "utils"))

    assert presence is rules.Presence.ONLY


def test_a_row_without_a_dir_is_a_problem() -> None:
    rows = _spec().manifest[1] + (("ghost", "ungated"),)
    repo = rules.Repo(_spec(manifest=("read", rows, "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.ROW_WITHOUT_DIRECTORY, "ghost"))

    assert presence is rules.Presence.ONLY


def test_an_examples_dir_without_a_row_is_a_problem() -> None:
    repo = rules.Repo(_spec(examples=(("demo", "directory"), ("newthing", "directory"))))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.UNREGISTERED_EXAMPLE, "examples/newthing")
    )

    assert presence is rules.Presence.ONLY


def test_an_examples_row_without_a_dir_is_a_problem() -> None:
    repo = rules.Repo(_spec(examples=()))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.ROW_WITHOUT_DIRECTORY, "examples/demo")
    )

    assert presence is rules.Presence.ONLY


def test_a_symlinked_top_level_dir_is_a_problem() -> None:
    top = _spec().top[:1] + (("appone", "symlink"),) + _spec().top[2:]
    repo = rules.Repo(_spec(top=top))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.SYMLINKED_DIRECTORY, "appone"))

    assert presence is rules.Presence.ONLY


def test_an_app_row_without_a_verify_arm_is_a_problem() -> None:
    verify = ("read", _spec().verify[1].replace("libby)    run_libby ;;", ""))
    repo = rules.Repo(_spec(verify=verify))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.NO_VERIFY_ARM, "libby"))

    assert presence is rules.Presence.ONLY


def test_an_app_row_without_a_ci_job_is_a_problem() -> None:
    workflow = ("read", _spec().workflow[1].replace("run: scripts/verify libby", "run: echo no"))
    repo = rules.Repo(_spec(workflow=workflow))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.NO_CI_JOB, "libby"))

    assert presence is rules.Presence.ONLY


def test_a_commented_ci_job_does_not_count() -> None:
    workflow = (
        "read",
        _spec().workflow[1].replace("run: scripts/verify libby", "# run: scripts/verify libby"),
    )
    repo = rules.Repo(_spec(workflow=workflow))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.NO_CI_JOB, "libby"))

    assert presence is rules.Presence.ONLY


def test_a_tessercheck_arm_without_a_declaration_is_a_problem() -> None:
    repo = rules.Repo(_spec(declarations=()))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.DECLARATION_MISSING, "appone/.tesser-root")
    )

    assert presence is rules.Presence.ONLY


def test_a_declaration_without_a_tessercheck_arm_is_a_problem() -> None:
    declarations = _spec().declarations + (("libby/.tesser-root", "read", "app\n"),)
    repo = rules.Repo(_spec(declarations=declarations))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.DECLARATION_UNCHECKED, "libby/.tesser-root")
    )

    assert presence is rules.Presence.ONLY


def test_a_wrong_declaration_first_line_is_a_problem() -> None:
    declarations = (("appone/.tesser-root", "read", "domain\n"),)
    repo = rules.Repo(_spec(declarations=declarations))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.DECLARATION_NOT_APP, "appone/.tesser-root")
    )

    assert presence is rules.Presence.ONLY


def test_an_unreadable_declaration_is_a_problem() -> None:
    declarations = (("appone/.tesser-root", "unreadable", ""),)
    repo = rules.Repo(_spec(declarations=declarations))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.DECLARATION_UNAVAILABLE, "appone/.tesser-root", "unreadable")
    )

    assert presence is rules.Presence.ONLY


def test_a_skip_line_in_a_declaration_is_recognized() -> None:
    declarations = (("appone/.tesser-root", "read", "app\nskip testdata\n"),)

    assert rules.Repo(_spec(declarations=declarations)).health() is rules.Health.CLEAN


def test_a_requirements_file_outside_an_app_row_is_a_problem() -> None:
    repo = rules.Repo(_spec(requirements=("appone", "libby", "docs")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.REQUIREMENTS_OUTSIDE_APP, "docs"))

    assert presence is rules.Presence.ONLY


def test_a_deep_requirements_file_is_caught() -> None:
    repo = rules.Repo(_spec(requirements=("appone", "libby", "docs/buried/tree")))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.REQUIREMENTS_OUTSIDE_APP, "docs/buried/tree")
    )

    assert presence is rules.Presence.ONLY


def test_a_demoted_app_row_is_caught_by_the_requirements_rule() -> None:
    rows = _spec().manifest[1][:5] + (("libby", "ungated"), ("scripts", "ungated"))
    repo = rules.Repo(_spec(manifest=("read", rows, "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.REQUIREMENTS_OUTSIDE_APP, "libby"))

    assert presence is rules.Presence.ONLY


def test_shared_app_directory_names_are_a_problem() -> None:
    rows = _spec().manifest[1] + (("examples/libby", "app"),)
    examples = (("demo", "directory"), ("libby", "directory"))
    requirements = ("appone", "libby", "examples/libby")
    repo = rules.Repo(
        _spec(manifest=("read", rows, ""), examples=examples, requirements=requirements)
    )

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.SHARED_GATE_NAME, "libby", "examples/libby")
    )

    assert presence is rules.Presence.ONLY


def test_a_malformed_manifest_is_the_only_problem() -> None:
    repo = rules.Repo(_spec(manifest=("malformed", (), "Expecting value: line 1")))

    presence = repo.presence(
        rules.ProblemSpec(
            rules.Rule.MANIFEST_MALFORMED, "manifest.json", "Expecting value: line 1"
        )
    )

    assert presence is rules.Presence.ONLY


def test_a_misshapen_manifest_is_the_only_problem() -> None:
    repo = rules.Repo(_spec(manifest=("misshapen", (), "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.MANIFEST_MISSHAPEN, "manifest.json"))

    assert presence is rules.Presence.ONLY


def test_a_missing_manifest_is_the_only_problem() -> None:
    repo = rules.Repo(_spec(manifest=("missing", (), "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.MANIFEST_MISSING, "manifest.json"))

    assert presence is rules.Presence.ONLY


def test_an_absent_problem_is_absent() -> None:
    repo = rules.Repo(_spec(manifest=("missing", (), "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.MANIFEST_MISSHAPEN, "manifest.json"))

    assert presence is rules.Presence.ABSENT


def test_trees_lists_app_rows_in_manifest_order() -> None:
    repo = rules.Repo(_spec())
    assert tuple(str(tree) for tree in repo.trees()) == ("appone", "libby")


def test_counts_reports_rows_and_app_trees() -> None:
    repo = rules.Repo(_spec())
    assert tuple(str(count) for count in repo.counts()) == ("7", "2")


def test_a_missing_verify_file_is_a_problem_and_cascades() -> None:
    repo = rules.Repo(_spec(verify=("missing", "")))

    unavailable = repo.presence(
        rules.ProblemSpec(rules.Rule.VERIFY_UNAVAILABLE, "scripts/verify", "missing")
    )
    cascaded = repo.presence(rules.ProblemSpec(rules.Rule.NO_VERIFY_ARM, "appone"))

    assert unavailable is rules.Presence.AMONG
    assert cascaded is rules.Presence.AMONG


def test_an_unreadable_workflow_file_is_a_problem() -> None:
    repo = rules.Repo(_spec(workflow=("unreadable", "")))

    presence = repo.presence(
        rules.ProblemSpec(
            rules.Rule.WORKFLOW_UNAVAILABLE, ".github/workflows/test.yml", "unreadable"
        )
    )

    assert presence is rules.Presence.AMONG


def test_an_unreadable_manifest_is_the_only_problem() -> None:
    repo = rules.Repo(_spec(manifest=("unreadable", (), "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.MANIFEST_UNREADABLE, "manifest.json"))

    assert presence is rules.Presence.ONLY


def test_trees_and_counts_degrade_when_the_manifest_cannot_be_read() -> None:
    repo = rules.Repo(_spec(manifest=("malformed", (), "boom")))
    assert repo.trees() == ()
    assert tuple(str(count) for count in repo.counts()) == ("0", "0")


def test_a_symlinked_examples_dir_reports_with_its_prefix() -> None:
    repo = rules.Repo(_spec(examples=(("demo", "symlink"),)))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.SYMLINKED_DIRECTORY, "examples/demo"))

    assert presence is rules.Presence.ONLY


def test_text_rejects_the_empty_string() -> None:
    with pytest.raises(ValueError):
        rules.Text("")


def test_text_equality() -> None:
    assert rules.Text("a") == rules.Text("a")
    assert rules.Text("a") != rules.Text("b")


def test_problem_constructs_from_spec() -> None:
    spec = rules.ProblemSpec(rules.Rule.UNKNOWN_KIND, "libby", "python-library")

    problem = rules.Problem(spec)

    assert str(problem.subject()) == spec.subject
    assert str(problem.note()) == spec.note
    assert str(problem.text()) == (
        "manifest.json row 'libby' declares unknown kind 'python-library'; "
        "the kinds are 'app' and 'ungated'"
    )


def test_problem_equality() -> None:
    assert rules.Problem(rules.ProblemSpec(rules.Rule.NO_CI_JOB, "a")) == rules.Problem(
        rules.ProblemSpec(rules.Rule.NO_CI_JOB, "a")
    )
    assert rules.Problem(rules.ProblemSpec(rules.Rule.NO_CI_JOB, "a")) != rules.Problem(
        rules.ProblemSpec(rules.Rule.NO_VERIFY_ARM, "a")
    )
    assert rules.Problem(rules.ProblemSpec(rules.Rule.NO_CI_JOB, "a")) != rules.Problem(
        rules.ProblemSpec(rules.Rule.NO_CI_JOB, "b")
    )


def test_an_empty_manifest_key_is_a_row_without_a_directory_not_a_crash() -> None:
    rows = _spec().manifest[1] + (("", "ungated"),)
    repo = rules.Repo(_spec(manifest=("read", rows, "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.ROW_WITHOUT_DIRECTORY, ""))

    assert presence is rules.Presence.ONLY
    assert tuple(str(tree) for tree in repo.trees()) == ("appone", "libby")


@pytest.mark.parametrize(
    ("rule", "subject", "note", "sentence"),
    [
        (rules.Rule.MANIFEST_MISSING, "manifest.json", "", "manifest.json is missing"),
        (rules.Rule.MANIFEST_UNREADABLE, "manifest.json", "", "manifest.json is unreadable"),
        (
            rules.Rule.MANIFEST_MALFORMED,
            "manifest.json",
            "Expecting value",
            "manifest.json is unreadable: Expecting value",
        ),
        (
            rules.Rule.MANIFEST_MISSHAPEN,
            "manifest.json",
            "",
            "manifest.json is not a flat object of directory-path to kind strings",
        ),
        (
            rules.Rule.UNKNOWN_KIND,
            "libby",
            "python-library",
            "manifest.json row 'libby' declares unknown kind 'python-library'; "
            "the kinds are 'app' and 'ungated'",
        ),
        (
            rules.Rule.UNREGISTERED_TOP_LEVEL,
            "utils",
            "",
            "top-level directory 'utils' has no manifest.json row; "
            "every top-level directory declares what it is",
        ),
        (
            rules.Rule.UNREGISTERED_EXAMPLE,
            "examples/newthing",
            "",
            "examples/newthing has no manifest.json row",
        ),
        (
            rules.Rule.ROW_WITHOUT_DIRECTORY,
            "examples/demo",
            "",
            "manifest.json row 'examples/demo' names no directory on disk",
        ),
        (
            rules.Rule.SYMLINKED_DIRECTORY,
            "appone",
            "",
            "appone is a symlinked directory; a declared directory is a real one",
        ),
        (rules.Rule.VERIFY_UNAVAILABLE, "scripts/verify", "missing", "scripts/verify is missing"),
        (
            rules.Rule.WORKFLOW_UNAVAILABLE,
            ".github/workflows/test.yml",
            "unreadable",
            ".github/workflows/test.yml is unreadable",
        ),
        (
            rules.Rule.SHARED_GATE_NAME,
            "libby",
            "examples/libby",
            "'libby' and 'examples/libby' share the gate name 'libby'; scripts/verify "
            "picks its steps by that name, so app directory names must be unique",
        ),
        (
            rules.Rule.NO_VERIFY_ARM,
            "examples/libby",
            "",
            "examples/libby has no scripts/verify case arm for 'libby'",
        ),
        (
            rules.Rule.NO_CI_JOB,
            "libby",
            "",
            "libby has no CI job step 'run: scripts/verify libby'",
        ),
        (
            rules.Rule.DECLARATION_UNCHECKED,
            "libby/.tesser-root",
            "",
            "libby/.tesser-root declares a tree whose scripts/verify steps do not run tessercheck",
        ),
        (
            rules.Rule.DECLARATION_MISSING,
            "appone/.tesser-root",
            "",
            "appone/.tesser-root is missing; a tree that tessercheck runs on "
            "declares itself with .tesser-root",
        ),
        (
            rules.Rule.DECLARATION_UNAVAILABLE,
            "appone/.tesser-root",
            "unreadable",
            "appone/.tesser-root does not declare 'app': unreadable",
        ),
        (
            rules.Rule.DECLARATION_NOT_APP,
            "appone/.tesser-root",
            "",
            "appone/.tesser-root does not declare 'app': first line is not 'app'",
        ),
        (
            rules.Rule.REQUIREMENTS_OUTSIDE_APP,
            "docs",
            "",
            "docs holds a requirements-dev.txt but is not an app row; "
            "a Python tree cannot sit outside the gates",
        ),
        (
            rules.Rule.REQUIRES_PYTHON_UNDECLARED,
            "libby/pyproject.toml",
            "",
            "libby/pyproject.toml declares a distribution without requires-python; "
            "every distribution states the Python floor as '>=3.12'",
        ),
        (
            rules.Rule.TARGET_VERSION_UNDECLARED,
            "libby/ruff.toml",
            "",
            "libby/ruff.toml declares a distribution without target-version; "
            "every distribution states the Python floor as 'py312'",
        ),
        (
            rules.Rule.FLOOR_FILE_UNAVAILABLE,
            "libby/pyproject.toml",
            "malformed",
            "libby/pyproject.toml is malformed",
        ),
        (
            rules.Rule.REQUIRES_PYTHON_BELOW_FLOOR,
            "libby/pyproject.toml",
            ">=3.11",
            "libby/pyproject.toml states requires-python = '>=3.11'; the Python floor "
            "is 3.12, so it reads '>=3.12'",
        ),
        (
            rules.Rule.TARGET_VERSION_BELOW_FLOOR,
            "libby/ruff.toml",
            "py311",
            "libby/ruff.toml states target-version = 'py311'; the Python floor "
            "is 3.12, so it reads 'py312'",
        ),
        (
            rules.Rule.WORKFLOW_PIN_BELOW_FLOOR,
            ".github/workflows/test.yml",
            "3.11",
            ".github/workflows/test.yml pins python-version 3.11, below the Python floor 3.12",
        ),
    ],
)
def test_every_rule_renders_its_sentence(
    rule: rules.Rule, subject: str, note: str, sentence: str
) -> None:
    problem = rules.Problem(rules.ProblemSpec(rule, subject, note))

    assert str(problem.text()) == sentence


@pytest.mark.parametrize("rule", list(rules.Rule))
def test_every_rule_renders_a_sentence(rule: rules.Rule) -> None:
    problem = rules.Problem(rules.ProblemSpec(rule, "libby/thing", "note"))

    assert str(problem.text())


def test_a_trailing_slash_app_row_is_a_problem_and_trees_survives_it() -> None:
    rows = _spec().manifest[1] + (("ghost/", "app"),)
    repo = rules.Repo(_spec(manifest=("read", rows, "")))

    presence = repo.presence(rules.ProblemSpec(rules.Rule.NO_VERIFY_ARM, "ghost/"))

    assert presence is rules.Presence.AMONG
    assert tuple(str(tree) for tree in repo.trees()) == ("appone", "libby")


def test_a_requires_python_below_the_floor_is_a_problem() -> None:
    floors = (("libby/pyproject.toml", "requires-python", "read", ">=3.11"),)
    repo = rules.Repo(_spec(floors=floors))

    presence = repo.presence(
        rules.ProblemSpec(
            rules.Rule.REQUIRES_PYTHON_BELOW_FLOOR, "libby/pyproject.toml", ">=3.11"
        )
    )

    assert presence is rules.Presence.ONLY


def test_a_whitespaced_requires_python_at_the_floor_is_clean() -> None:
    floors = (("libby/pyproject.toml", "requires-python", "read", ">= 3.12"),)

    assert rules.Repo(_spec(floors=floors)).health() is rules.Health.CLEAN


def test_a_distribution_without_a_requires_python_is_a_problem() -> None:
    floors = (("libby/pyproject.toml", "requires-python", "undeclared", ""),)
    repo = rules.Repo(_spec(floors=floors))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.REQUIRES_PYTHON_UNDECLARED, "libby/pyproject.toml")
    )

    assert presence is rules.Presence.ONLY


def test_a_distribution_without_a_target_version_is_a_problem() -> None:
    floors = (("libby/ruff.toml", "target-version", "undeclared", ""),)
    repo = rules.Repo(_spec(floors=floors))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.TARGET_VERSION_UNDECLARED, "libby/ruff.toml")
    )

    assert presence is rules.Presence.ONLY


def test_a_target_version_below_the_floor_is_a_problem() -> None:
    floors = (("libby/ruff.toml", "target-version", "read", "py311"),)
    repo = rules.Repo(_spec(floors=floors))

    presence = repo.presence(
        rules.ProblemSpec(rules.Rule.TARGET_VERSION_BELOW_FLOOR, "libby/ruff.toml", "py311")
    )

    assert presence is rules.Presence.ONLY


def test_an_unparsable_config_file_is_a_problem() -> None:
    floors = (
        ("libby/pyproject.toml", "requires-python", "malformed", ""),
        ("libby/ruff.toml", "requires-python", "unreadable", ""),
    )
    repo = rules.Repo(_spec(floors=floors))

    malformed = repo.presence(
        rules.ProblemSpec(rules.Rule.FLOOR_FILE_UNAVAILABLE, "libby/pyproject.toml", "malformed")
    )
    unreadable = repo.presence(
        rules.ProblemSpec(rules.Rule.FLOOR_FILE_UNAVAILABLE, "libby/ruff.toml", "unreadable")
    )

    assert malformed is rules.Presence.AMONG
    assert unreadable is rules.Presence.AMONG


def test_a_workflow_pin_below_the_floor_is_a_problem() -> None:
    workflow = (
        "read",
        _spec().workflow[1] + "      - uses: actions/setup-python@v5\n"
        "        with:\n"
        "          python-version: '3.11'\n",
    )
    repo = rules.Repo(_spec(workflow=workflow))

    presence = repo.presence(
        rules.ProblemSpec(
            rules.Rule.WORKFLOW_PIN_BELOW_FLOOR, ".github/workflows/test.yml", "3.11"
        )
    )

    assert presence is rules.Presence.ONLY


def test_a_matrix_entry_below_the_floor_is_a_problem() -> None:
    workflow = (
        "read",
        _spec().workflow[1] + "        python-version: ['3.11', '3.12', '3.13']\n",
    )
    repo = rules.Repo(_spec(workflow=workflow))

    below = repo.presence(
        rules.ProblemSpec(
            rules.Rule.WORKFLOW_PIN_BELOW_FLOOR, ".github/workflows/test.yml", "3.11"
        )
    )
    at_floor = repo.presence(
        rules.ProblemSpec(
            rules.Rule.WORKFLOW_PIN_BELOW_FLOOR, ".github/workflows/test.yml", "3.12"
        )
    )

    assert below is rules.Presence.ONLY
    assert at_floor is rules.Presence.ABSENT


def test_a_matrix_at_and_above_the_floor_is_clean() -> None:
    workflow = (
        "read",
        _spec().workflow[1] + "        python-version: ['3.12', '3.13', '3.14']\n"
        "          python-version: ${{ matrix.python-version }}\n",
    )

    assert rules.Repo(_spec(workflow=workflow)).health() is rules.Health.CLEAN


def test_a_repeated_problem_is_still_the_only_problem() -> None:
    workflow = (
        "read",
        _spec().workflow[1] + "        python-version: ['3.11']\n"
        "          python-version: '3.11'\n",
    )
    repo = rules.Repo(_spec(workflow=workflow))

    presence = repo.presence(
        rules.ProblemSpec(
            rules.Rule.WORKFLOW_PIN_BELOW_FLOOR, ".github/workflows/test.yml", "3.11"
        )
    )

    assert presence is rules.Presence.ONLY
