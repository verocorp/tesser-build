# Inspect Python test dependencies before choosing checks

Install `tessercheck-cli` and run:

```sh
tesser-inspect-tests --repo /path/to/checkout --base HEAD --json
```

The command inspects source without importing the target repository or running
its tests. It reports candidates for an agent to investigate, **not an automatic
test selection or a complete dependency graph**. Exit 0 means that inspection
produced a report, never that tests passed. An empty candidate list does not
establish that a change is safe.

The repository argument must name a Git working-tree root, including a linked
worktree root. The baseline must resolve to a commit. The command requires Git,
Python 3.12 or newer, and a POSIX platform supporting no-follow file opens. Keep
the checkout stationary during inspection: the Git facts and file reads are not
an atomic snapshot. The command does not invoke target scripts, plugins, hooks,
external diff drivers, text conversion commands or configured clean/process
filters. Submodules are rejected; inspect each checkout independently.

## Version 1 JSON

JSON is the default output; `--json` explicitly requests the same format.
Successful output has these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1`; consumers should reject unknown versions. |
| `status` | `"ok"` when inspection completed. |
| `baseline` | Resolved full Git commit object ID, not the supplied ref spelling. |
| `changes` | Sorted baseline-to-working-tree change facts: `path`, nullable `previous_path`, and Git `status` (`A`, `M`, `D`, `T`, `R` plus similarity score, or `?` for a non-ignored untracked file). |
| `working_tree_changes` | Sorted index/worktree facts relative to HEAD, with `path`, nullable `previous_path`, `index_status`, and `worktree_status` from Git porcelain v1. A space means unchanged on that side; `?` means untracked. These preserve staged/unstaged changes even when their net effect cancels against the baseline. |
| `changed_test_files` | Sorted distinct current or previous paths matching `test_*.py`, `*_test.py`, or `conftest.py`, from either set of change facts. Deleted and renamed-away test locations remain visible. |
| `candidates` | Sorted evidence objects with `kind`, repository-relative `path`, `line` (one-based, or zero for a file-level fact), `symbol`, and `reason`. |
| `limitations` | Explicit limits of the report; retain these when presenting candidates to an agent. |

Candidate kinds are `changed-test`, `helper`, `import-reference`,
`fixture-reference`, `fixture-definition`, `source-reader`, and `collection`.
Local helper references, imports and test parameters provide direct evidence.
Fixture aliases and class-based test methods are inspected. Ancestor conftests
and pytest configuration are collection candidates. Readers and fixture
definitions are deliberately repository-wide, including unchanged files, so
cross-file source constraints do not disappear merely because the new test does
not call them. A data-file reader may be irrelevant; inspect its body before
deciding. Aliases at import sites are followed, but dynamic rebinding is not.

Only tracked and non-ignored current files are considered. All such Python
sources are parsed, not only changed tests; malformed source therefore fails
the report rather than silently erasing possible evidence. Current UTF-8
configuration files are read but not executed. Source/configuration symlinks,
non-regular source files, non-UTF8 content, unreadable files, invalid refs,
unmerged checkouts and unsupported inputs return nonzero. Deleted source has
no current definitions to inspect. Git rename detection is heuristic; an
unstaged move may appear as deletion plus a new file instead.

Errors return exit 2 and JSON with `schema_version: 1`, `status: "error"`, and
`error: {"code": ..., "message": ...}`; they never include an apparently clean
candidate report. Codes include `usage_error`, `invalid_repo`, `invalid_base`,
`python_parse_error`, and `input_error` (Git/filesystem/encoding failures).
`--help` alone prints usage and exits 0. Unexpected process-level failures can
still terminate the command without a report; consumers must inspect its exit
status and validate the JSON, not treat missing output as success.

## Agent workflow

1. Read changed tests, the helpers and fixtures they use, and the candidate
   readers' bodies. A source-inspecting meta-test can reject a new helper's
   argument shape while that helper's own behavioral test passes.
2. Record which candidates apply, why ordinary data readers do not apply, and
   which bounded check establishes each relevant construction or collection
   contract. Include dynamic imports, plugins, custom test naming and non-Python
   consumers manually: this report cannot establish those dependencies.
3. Run the relevant bounded infrastructure and construction/type/import gates
   on the current source before justified broader suites. Refresh the report
   and the review whenever source, tests or configuration change.

This command neither runs the candidates nor decides that the review is
adequate. Static inspection improves the evidence available to that decision;
it does not replace it.

## Git metadata

Git may refresh index stat metadata while inspecting file changes, even with
optional index writes disabled. This does not change staged file contents;
the command is not a byte-for-byte read-only operation on Git metadata.
