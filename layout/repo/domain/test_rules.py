from __future__ import annotations

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
) -> rules.RepoSpec:
    return rules.RepoSpec(
        manifest=manifest,
        verify=verify,
        workflow=workflow,
        top=top,
        examples=examples,
        declarations=declarations,
        requirements=requirements,
    )


@ts.helper
def _texts(repo: rules.Repo) -> tuple[str, ...]:  # tessercheck:ignore TB073
    return tuple(str(problem.text()) for problem in repo.problems())


def test_a_consistent_repo_has_no_problems() -> None:
    assert _texts(rules.Repo(_spec())) == ()


def test_an_unknown_kind_is_a_problem() -> None:
    rows = _spec().manifest[1][:5] + (("libby", "python-library"), ("scripts", "ungated"))
    found = _texts(rules.Repo(_spec(manifest=("read", rows, ""))))
    assert any("unknown kind 'python-library'" in text for text in found), found


def test_a_top_level_dir_without_a_row_is_a_problem() -> None:
    top = _spec().top + (("utils", "directory"),)
    found = _texts(rules.Repo(_spec(top=top)))
    assert any("'utils' has no manifest.json row" in text for text in found), found


def test_a_row_without_a_dir_is_a_problem() -> None:
    rows = _spec().manifest[1] + (("ghost", "ungated"),)
    found = _texts(rules.Repo(_spec(manifest=("read", rows, ""))))
    assert any("'ghost' names no directory on disk" in text for text in found), found


def test_an_examples_dir_without_a_row_is_a_problem() -> None:
    found = _texts(
        rules.Repo(_spec(examples=(("demo", "directory"), ("newthing", "directory"))))
    )
    assert any("examples/newthing has no manifest.json row" in text for text in found), found


def test_an_examples_row_without_a_dir_is_a_problem() -> None:
    found = _texts(rules.Repo(_spec(examples=())))
    assert any(
        "'examples/demo' names no directory on disk" in text for text in found
    ), found


def test_a_symlinked_top_level_dir_is_a_problem() -> None:
    top = _spec().top[:1] + (("appone", "symlink"),) + _spec().top[2:]
    found = _texts(rules.Repo(_spec(top=top)))
    assert any("appone is a symlinked directory" in text for text in found), found


def test_an_app_row_without_a_verify_arm_is_a_problem() -> None:
    verify = ("read", _spec().verify[1].replace("libby)    run_libby ;;", ""))
    found = _texts(rules.Repo(_spec(verify=verify)))
    assert any(
        "libby has no scripts/verify case arm for 'libby'" in text for text in found
    ), found


def test_an_app_row_without_a_ci_job_is_a_problem() -> None:
    workflow = ("read", _spec().workflow[1].replace("run: scripts/verify libby", "run: echo no"))
    found = _texts(rules.Repo(_spec(workflow=workflow)))
    assert any(
        "libby has no CI job step 'run: scripts/verify libby'" in text for text in found
    ), found


def test_a_commented_ci_job_does_not_count() -> None:
    workflow = (
        "read",
        _spec().workflow[1].replace("run: scripts/verify libby", "# run: scripts/verify libby"),
    )
    found = _texts(rules.Repo(_spec(workflow=workflow)))
    assert any("libby has no CI job step" in text for text in found), found


def test_a_tessercheck_arm_without_a_declaration_is_a_problem() -> None:
    found = _texts(rules.Repo(_spec(declarations=())))
    assert any(
        "appone/.tesser-root is missing" in text for text in found
    ), found


def test_a_declaration_without_a_tessercheck_arm_is_a_problem() -> None:
    declarations = _spec().declarations + (("libby/.tesser-root", "read", "app\n"),)
    found = _texts(rules.Repo(_spec(declarations=declarations)))
    assert any(
        "libby/.tesser-root declares a tree whose scripts/verify steps "
        "do not run tessercheck" in text
        for text in found
    ), found


def test_a_wrong_declaration_first_line_is_a_problem() -> None:
    declarations = (("appone/.tesser-root", "read", "domain\n"),)
    found = _texts(rules.Repo(_spec(declarations=declarations)))
    assert any(
        "appone/.tesser-root does not declare 'app': first line is not 'app'" in text
        for text in found
    ), found


def test_an_unreadable_declaration_is_a_problem() -> None:
    declarations = (("appone/.tesser-root", "unreadable", ""),)
    found = _texts(rules.Repo(_spec(declarations=declarations)))
    assert any(
        "appone/.tesser-root does not declare 'app': unreadable" in text
        for text in found
    ), found


def test_a_skip_line_in_a_declaration_is_recognized() -> None:
    declarations = (("appone/.tesser-root", "read", "app\nskip testdata\n"),)
    assert _texts(rules.Repo(_spec(declarations=declarations))) == ()


def test_a_requirements_file_outside_an_app_row_is_a_problem() -> None:
    found = _texts(rules.Repo(_spec(requirements=("appone", "libby", "docs"))))
    assert any(
        "docs holds a requirements-dev.txt but is not an app row" in text
        for text in found
    ), found


def test_a_deep_requirements_file_is_caught() -> None:
    found = _texts(
        rules.Repo(_spec(requirements=("appone", "libby", "docs/buried/tree")))
    )
    assert any("docs/buried/tree holds a requirements-dev.txt" in text for text in found), found


def test_a_demoted_app_row_is_caught_by_the_requirements_rule() -> None:
    rows = _spec().manifest[1][:5] + (("libby", "ungated"), ("scripts", "ungated"))
    found = _texts(rules.Repo(_spec(manifest=("read", rows, ""))))
    assert any("libby holds a requirements-dev.txt" in text for text in found), found


def test_shared_app_directory_names_are_a_problem() -> None:
    rows = _spec().manifest[1] + (("examples/libby", "app"),)
    examples = (("demo", "directory"), ("libby", "directory"))
    requirements = ("appone", "libby", "examples/libby")
    found = _texts(
        rules.Repo(
            _spec(
                manifest=("read", rows, ""),
                examples=examples,
                requirements=requirements,
            )
        )
    )
    assert any("share the gate name 'libby'" in text for text in found), found


def test_a_malformed_manifest_is_the_only_problem() -> None:
    found = _texts(
        rules.Repo(_spec(manifest=("malformed", (), "Expecting value: line 1")))
    )
    assert found == ("manifest.json is unreadable: Expecting value: line 1",)


def test_a_misshapen_manifest_is_the_only_problem() -> None:
    found = _texts(rules.Repo(_spec(manifest=("misshapen", (), ""))))
    assert found == (
        "manifest.json is not a flat object of directory-path to kind strings",
    )


def test_a_missing_manifest_is_the_only_problem() -> None:
    found = _texts(rules.Repo(_spec(manifest=("missing", (), ""))))
    assert found == ("manifest.json is missing",)


def test_trees_lists_app_rows_in_manifest_order() -> None:
    repo = rules.Repo(_spec())
    assert tuple(str(tree) for tree in repo.trees()) == ("appone", "libby")


def test_counts_reports_rows_and_app_trees() -> None:
    repo = rules.Repo(_spec())
    assert tuple(str(count) for count in repo.counts()) == ("7", "2")


def test_a_missing_verify_file_is_a_problem_and_cascades() -> None:
    found = _texts(rules.Repo(_spec(verify=("missing", ""))))
    assert any("scripts/verify is missing" in text for text in found), found
    assert any("appone has no scripts/verify case arm" in text for text in found), found


def test_an_unreadable_workflow_file_is_a_problem() -> None:
    found = _texts(rules.Repo(_spec(workflow=("unreadable", ""))))
    assert any(
        ".github/workflows/test.yml is unreadable" in text for text in found
    ), found


def test_an_unreadable_manifest_is_the_only_problem() -> None:
    found = _texts(rules.Repo(_spec(manifest=("unreadable", (), ""))))
    assert found == ("manifest.json is unreadable",)


def test_trees_and_counts_degrade_when_the_manifest_cannot_be_read() -> None:
    repo = rules.Repo(_spec(manifest=("malformed", (), "boom")))
    assert repo.trees() == ()
    assert tuple(str(count) for count in repo.counts()) == ("0", "0")


def test_a_symlinked_examples_dir_reports_with_its_prefix() -> None:
    found = _texts(rules.Repo(_spec(examples=(("demo", "symlink"),))))
    assert any(
        "examples/demo is a symlinked directory" in text for text in found
    ), found


def test_text_rejects_the_empty_string() -> None:
    import pytest

    with pytest.raises(ValueError):
        rules.Text("")


def test_text_equality() -> None:
    assert rules.Text("a") == rules.Text("a")
    assert rules.Text("a") != rules.Text("b")


def test_problem_equality() -> None:
    assert rules.Problem("a b") == rules.Problem("a b")
    assert rules.Problem("a b") != rules.Problem("c d")


def test_a_trailing_slash_app_row_is_a_problem_and_trees_survives_it() -> None:
    rows = _spec().manifest[1] + (("ghost/", "app"),)
    repo = rules.Repo(_spec(manifest=("read", rows, "")))
    assert any("has no scripts/verify case arm" in str(p.text()) for p in repo.problems())
    assert tuple(str(tree) for tree in repo.trees()) == ("appone", "libby")
