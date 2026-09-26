# Bounded local agent trials

`trial` executes one caller-supplied local agent process, then verifies the edited
candidate under **one whole-task deadline**. It uses no provider client and has
no aggregator. This is a renewable local runner interface, not a claim that any
particular provider or autonomous agent has been measured.

```
tesser-experiment trial \
  --scenario /oracle/scenario.json --candidate /work/prepared-candidate \
  --agent-json '["/opt/local-agent-runner", "--mode", "implement"]' \
  --command-json '["python3", "-B", "main.py"]' \
  --gate-json '[]' --deadline 10m --arm local-arm-a \
  --result /results/trial.json
```

The candidate must already exist. `--agent-json` is a literal argv array, with no
implicit shell. The agent runs in the original candidate directory and receives
one disclosure-safe brief JSON object on stdin, followed by EOF. Its stdout is
bounded and discarded; stderr and its actual exit status are retained. It may
edit the candidate. Only a zero-exit agent proceeds to verification, which then
copies the edited tree. `--followup` and scenario-authored `base_expected` work
as in `verify`. An oracle changed during agent execution fails closed.

`RunTrial(context.Context, TrialOptions) TrialResult` is the package interface.
`TrialOptions.Verification` holds the existing verifier options, but its
`Deadline` is the whole-task budget here. `Agent`, `Arm`, and optional
`InterventionsPath` provide the other inputs. The unchanged `Verify` API still
reports verification-only timing.

The release timestamp is recorded before validation and agent execution; the
deadline starts there and includes contract loading, initial source hashing,
agent work, snapshot preparation, gates, and probes. Results record the agent
span, nested verifier span, verified timestamp on success, and task end on every
outcome. The verifier receives only the remaining budget. Process-group cleanup
can finish after the deadline, so observed elapsed time can exceed the budget.

Every eligible attempted run is retained, including agent failures, wrong
behavior, timeouts, and infrastructure errors. `capped_completion_ms` is the
release-to-verified-end duration for success, capped at the budget; unsuccessful
eligible runs receive the whole budget. Invalid preflight inputs are ineligible
and have null completion duration. A zero agent exit never establishes success
without correct verification. `usage` and `cost` remain `"unknown"`.

Optional `--interventions /results/events.json` reads caller-reported event input
after the run:

```json
[{"at":"2026-09-25T12:00:00Z","kind":"human_instruction","description":"Clarified the requested behavior."}]
```

Absent input is `human_intervention.status: "unknown"` with null events. Supplied
valid events are preserved verbatim as `"reported"`, including their timestamps;
setup events may precede release. Even an explicit empty array does **not** claim
autonomy or complete surveillance. Invalid evidence is retained as an error and
cannot produce a successful trial result. Event files and stderr must not contain
secrets. Event input is caller-reported, not authenticated or independently observed.

The result records the scenario digest, initial source digest, arm identifier,
and a configuration digest over that identifier, both argv arrays, gates,
followup, and exact duration budget. None of these alone establishes experimental
comparability: repetitions, baseline preparation, environment, and intervention
coverage still need a declared experiment design. This command deliberately does
not pool or aggregate trials.

**Current Capy-task trials are separate.** Their real release, agent, and verified
end timestamps come from recorded platform events. Running this command later
does not retroactively measure those tasks or replace their platform records.

The same disposable-cloud-only safety boundary as `verify` applies: this is not
a hostile-code sandbox, and same-user agents can access files and environment
outside their working directory. Do not provide production credentials.
