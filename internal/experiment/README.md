# Executable contract verification

This standard-library-only package and `cmd/tesser-experiment` verify an already
prepared candidate. They do not invoke a provider, create a candidate, or measure
an agent's time to completion.

```
go run ./cmd/tesser-experiment brief --scenario /oracle/scenario.json
go run ./cmd/tesser-experiment brief --scenario /oracle/scenario.json --followup change-1
go run ./cmd/tesser-experiment verify \
  --scenario /oracle/scenario.json --candidate /work/candidate \
  --command-json '["python3", "-B", "main.py"]' \
  --gate-json '[["python3", "-B", "check.py"]]' \
  --result /results/trial.json --deadline 30s
```

`verify` exits zero only for `correct`. Invalid CLI syntax exits 2 without running
anything; verification failures, missing contracts, and result-write failures exit
1. The result's parent directory must already exist. Results are written by atomic
rename, outside the candidate and without overwriting the scenario.

## Contract

```json
{
  "version": 1,
  "id": "example",
  "family": "example-family",
  "requirements": ["Echo each object unchanged."],
  "vocabulary": {"object": "A JSON object."},
  "probes": [
    {"id": "echo", "inputs": [{"value": 1}], "expected": [{"value": 1}]}
  ],
  "followups": []
}
```

A followup has `id`, nonempty `requirements`, and nonempty `probes` of the same
shape as base probes. Probe IDs are globally unique; followup IDs are unique.
Selecting a followup verifies **base plus selected followup** probes. A brief
contains only the base requirements, vocabulary, protocol, and safety notice,
plus selected followup requirements when explicitly requested. It contains no
probe data or undisclosed followup IDs or requirements.

A followup may declare `"base_expected":{"base-probe-id":[{"new":"response"}]}`
when its requirements change the correct behavior for existing inputs. Every key
must name an existing base probe, and its object-response array must exactly
match that probe's input cardinality. An explicitly supplied empty or null map is
invalid. All base inputs still run: declared overrides replace only their expected
responses, and other base probes retain the original expectations. These overrides
belong to the predeclared scenario oracle and are never included in a brief.

The loader rejects unknown fields, duplicate object keys, unsupported versions,
empty IDs/requirements/probes, non-object messages, mismatched response counts,
missing required fields, and trailing JSON. Contracts and captured stdout are
limited to 4 MiB each. JSON object keys are unordered; arrays are ordered; numbers
compare exactly by mathematical decimal value without floating-point rounding.

## Execution and evidence

`Verify(context.Context, Options) Result` loads the oracle, copies the candidate
into an owned temporary directory, compares source and snapshot SHA-256 digests,
and runs gates followed by probes in that same tree. Every probe starts a fresh
process, receives newline-delimited input objects, and must produce exactly one
object per input line. Extra lines, malformed objects, wrong answers, nonzero
exits, and timeouts fail. The command and gates are argv arrays, not shell strings.
An explicitly supplied shell is just another executable. Absolute argv elements
inside the candidate are remapped into the snapshot; relative paths are resolved
from the snapshot working directory. External interpreters and tools are not
included in the source digest.

Symlinks, hard-linked files, and special files anywhere in the candidate are rejected.
Hard links cannot be copied independently without changing file identity. File
and directory modification times are preserved and checked against the source.
The oracle,
temporary directory, and result must be outside the candidate, preventing copy
recursion or accidental oracle inclusion. Tree content, paths, types, and modes
contribute to the source digest; exact scenario bytes contribute to the contract
digest. Integrity checks after each stage also include modification timestamps.
Linux inotify and macOS kqueue watches reject mutation events, including writes
that restore the original content; unavailable watches fail closed.
Gates must be read-only: compilation output, Python bytecode caches, and test
caches must be disabled or written outside the tree. A stage failure stops the
run and cannot be replaced by a later successful probe.

The overall positive deadline covers verification setup, gates, probes, and
integrity checks. Linux and macOS processes run in separate process groups;
cancellation kills the group, and cleanup also kills remaining group members.
Process/pipe cleanup may extend measured elapsed time slightly beyond the budget.
Filesystem calls are cooperative, not a hard real-time timeout for stalled mounts.

Results record `correct`, `incorrect`, `timeout`, or `infra_error`, actual exit
codes (null if no process started), per-stage errors, and at most 16 KiB of stderr
per stage with an explicit truncation flag. A signal termination has exit code
`-1` and the process error names the signal. No environment dump is collected.
`eligible` means contract/options validation and snapshot preparation succeeded;
it does not mean the run was autonomous or its agent effort was measured.

`verification_started_at`, `verification_ended_at`, `verification_elapsed_ms`, and
`verification_budget_ms` describe **verification only**. They are not task
completion time or speed. `usage`, `cost`, and `human_intervention` are `"unknown"`,
not zero. End-to-end completion metrics require independent orchestration with a
real task start, task deadline, and verified end; this package cannot supply them.

## Safety boundary

This is **not a hostile-code sandbox**. Run it only on disposable cloud machines
without secrets. Children inherit the process environment and same-user access;
they can read files outside their working directory, escape a process group, or
try to evade integrity checks. The oracle is not copied into the
candidate, but same-user filesystem access does not hide it from adversarial
code. Filesystem notifications improve mutation detection, but do not create a
security boundary. A stronger threat model needs an external OS/container
isolation boundary and independently protected oracle.
