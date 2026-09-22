# Adapter dependency shape — the analyzer changes ruled 2026-09-22

Status: **PLANNED.** Rulings by Chris on 2026-09-22, made while walking the
voice example's Restate and LiveKit adapters. Two of them are already in the
tree: relays are named for their far side and `await_` is a calling mode
(commit `3405869a`), and the LiveKit surface is a handler, not a runtime
(commit `66122f48`). Everything else here is owed. Each section gives the rule
in the form it will be written, what the analyzer reads to decide it, what
fires in the tree today, and what it waits on. The order at the end is the
build order. `TODOS.md` carries the same items as bullets; this page is the
one that says how they fit together.

## The shape the rules describe

The durable-execution layer changes so that no adapter constructs a
collaborator and no adapter imports another adapter. Voice names; every tree
with the shape follows.

| role | asyncpg store | engine side |
|---|---|---|
| scope-opener protocol | `ports.WidgetStore` | `ts.Workflow[restate.WorkflowContext, client.CallOrchestratorApplicationClient]`, annotated on the runtime |
| scope-opener implementation | `PostgresWidgetStore` | `RestateCallWorkflow`, in `component/` |
| yielded protocol | `ports.WidgetRepository` | `client.CallOrchestratorApplicationClient` |
| yielded implementation | `PostgresWidgetRepository` | `orchestrators.CallOrchestrator` |

The analogy is mirrored because the engine is the caller: with the store the
application holds the opener and the adapter is yielded, and the scope value
is acquired inside; with the engine the adapter holds the opener and the
application is yielded, and the scope value is handed in by the engine. That
is why `invocation()` takes the context as an argument where `transaction()`
takes nothing, and why the protocol is generic in the context type rather
than a port: a port cannot name the engine's type, and erasing it at the
crossing forces a narrowing the store never needs.

```python
# tesser-py: tesser/application/workflow.py — the kind
class Workflow(typing.Protocol[C, O]):
    def invocation(self, context: C) -> typing.AsyncContextManager[O]: ...


# calls/adapters/runtimes/restate_call_runtime.py — constructs nothing, uses the first argument
class RestateCallRuntime(ts.Runtime):
    def __init__(
        self,
        call_store_actions_application_client: client.CallStoreActionsApplicationClient,
        dialing_actions_application_client: client.DialingActionsApplicationClient,
        speech_actions_application_client: client.SpeechActionsApplicationClient,
        call_workflow: ts.Workflow[restate.WorkflowContext, client.CallOrchestratorApplicationClient],
    ) -> None:
        @self.call_orchestrator_workflow.main(input_serde=..., output_serde=...)
        async def conduct_call(restate_workflow_context, conduct_call_request):
            async with call_workflow.invocation(restate_workflow_context) as call_orchestrator:
                return await call_orchestrator.conduct_call(conduct_call_request)


# calls/component/call_workflow.py — the one package that directly-uses everything
class RestateCallWorkflow:
    @contextlib.asynccontextmanager
    async def invocation(self, restate_workflow_context: restate.WorkflowContext):
        yield orchestrators.CallOrchestrator(
            runners.RestateInvocationDialingActionsRelay(restate_workflow_context),
            runners.RestateInvocationCallOrchestratorSignalRelay(restate_workflow_context),
            runners.RestateInvocationSpeechActionsRelay(restate_workflow_context),
            runners.RestateInvocationCallStoreActionsRelay(restate_workflow_context),
        )


# calls/adapters/runners/restate_invocation_call_store_actions_relay.py — targets its far side by name
class RestateInvocationCallStoreActionsRelay(ts.Runner):
    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def run_record_call(self, record_call_request):
        answer = await self._restate_workflow_context.generic_call(
            "CallStoreActions", "record_call", relays.RecordCallRequestSnapshot().serialize(record_call_request)
        )
        return relays.RecordCallResponseSnapshot().deserialize(answer)
```

Runners speak bytes through the relay snapshots on both ends, so the serde
shims stay on the runtime and nothing in `runtimes/` is imported by a runner.
Promises use the SDK's bytes serde with the same snapshots.

## 1. The adapter import rule closes

**Rule.** *An adapters kind package reaches only the application packages its
kind is declared to reach, and never another package under `adapters/`.*

**Today.** TB060 is an allowlist per kind, and two entries are adapter
packages: a runner reaches "the runtimes package", a runtime reaches "the
runners". Both were written as permissions when the relay/runner/runtime
shape landed (PR #171), which is how the exception got in. Fifteen sites
carry it — voice 6, durable-execution 6, minimal 3 — plus the generator's
runner and runtime templates. A sibling test inherits its module's reach, so
the tests beside those runners fire too.

**Reads.** The import graph, as TB060 does now. Written as a closed rule, a
kind package added later inherits the ban without a row of its own.

**Waits on.** Section 2: until a runner targets by name it cannot stop
importing the runtime. Lands in the same build.

## 2. One name across the crossing, held by name and not by import

**Rule.** *A runner method reaches its far side by the service named for the
relay's far side and the handler named for the operation; a runtime registers
that service under that name with a handler under that name.* The far side of
`CallStoreActionsRelay` is `"CallStoreActions"`; `run_record_call` reaches
`"record_call"`.

**Today.** The row "a runner method reaches the handler of the operation it
carries" resolves `self._runtime.<op>_handler`, and the far-side derivation
landed on 2026-09-22 walks the same attribute to find the class the handler
invokes. Both are re-cut to read the two strings in `generic_call` (and the
ingress client's `generic_call`) on the runner side and the `restate.Service`
/ `restate.Workflow` name plus the handler name on the runtime side. The
promise name an `await_` method reads is checked the same way. The runtime's
"exposes each handler as `<op>_handler`" row stays, because the host still
mounts what the runtime registers.

**Reads.** String literals at the call site and the registration; the relay
registry already built per context.

**Waits on.** Nothing. This is the core of the dependency-shape build.

## 3. A runtime has us on both ends; a handler faces outsiders

**Rules.** Two TB085 rows.

*Every handler a runtime registers, and every promise it names, is the far
end of a relay operation in its context (`run_`, `start_`, or `await_` plus
the operation), because a runtime has us on both ends; a callback no runner
reaches is a handler, and its class belongs in `adapters/handlers/`.*

*A handler's public methods are never named for a relay operation in its
context, because a handler faces outsiders and a runner sends only to a
runtime.*

**Why.** The LiveKit class passed every permission a runtime has and had no
counterpart: nothing on our side sent `accept_job`, `start_job`, or a
completed turn. Permissions look at outgoing edges; this defect shows only in
the incoming ones. The move to a handler (commit `66122f48`) removed the
three TB081/TB082 markers on the class it reached and the four TB085 markers
on its hooks, with no widening of the actions rule, because a service may
hold a relay and an actions class may not.

**Reads.** The relay registry: for each `<op>_handler` a runtime exposes and
each promise it names, look for a relay method with that operation. The
mirror reads the same list against a handler's method names.

**Limit.** Whether an SDK is an engine or the outside world is not decidable.
Writing runners for it is the declaration that we are on both ends, and the
analyzer holds the tree to what it declared.

**Waits on.** Nothing. Independent of the build in sections 1, 2, and 4.

## 4. `ts.Workflow` and the orchestrator's client

**Rules.**

- *A runtime holds application clients and at most one workflow, and
  constructs nothing.* TB060's runtime row drops "the orchestrators" and "the
  runners"; a runtime module that names an orchestrator or a runner class is
  a finding.
- *An orchestrator is reachable only through a `tesser.application.Client`
  in `application/client/`*, as an actions class is. `client/call_orchestrator.py`
  declares `CallOrchestratorApplicationClient` with the orchestrator's
  operations.
- *A workflow implementation lives in `component/`* and is the one class
  there that directly-uses an orchestrator and runners. The component rows
  gain that kind.
- *`ts.Workflow[C, O]` is the one `ts.*` kind used as an annotation rather
  than a base.* Every other `ts.*` name in every tree appears only in a
  `class X(ts.Y)` line; this is the first generic kind and the first used as
  a type, chosen over subclassing it per binding. The totality rows say so
  explicitly so the exception cannot spread.

**Waits on.** Nothing, but it is one build with sections 1 and 2 because the
runtime cannot stop constructing runners until runners stop needing it.

## 5. Application clients keep the kind word

**Rule.** *An application client is named `<Class>ApplicationClient` for the
actions class or orchestrator it fronts.* `CallStoreActionsApplicationClient`,
`CallOrchestratorApplicationClient`.

**Why.** Today's convention drops the kind word (`CallActions` is fronted by
`CallApplicationClient`). With the orchestrator gaining a client on the same
far side the dropped form collides, so one of the two must keep its kind
word, and both keeping it is the symmetric choice. Renames the existing
actions clients in every tree.

## 6. An actions class is named for the one thing it holds

**Rule, leaning — confirm before enacting.** *A class of actions is named
for its one port plus `Actions`.* `DialingActions` holds `ports.Dialing`,
`SpeechActions` holds `ports.Speech`, so `CallActions`, which holds
`ports.CallStore`, is `CallStoreActions`. In durable-execution the derived
names are long, `ProductCatalogRepositoryActions` and
`PaymentProcessorActions`, because those ports are named for what they wrap;
either the derived names stand or the ports get shorter names first, which is
a separate naming call. Everything derived from the actions name moves with
it: the relay, the Restate service name, the runners, the client.

## 7. An `await_` request is named for the wait — built, awaiting a ruling

The 2026-09-22 relay re-cut had to name the request of `await_person_joined`,
and the uniform rule would give `PersonJoinedRequest`, which
`run_person_joined` already owns on the same far side. The subagent chose
`AwaitPersonJoinedRequest`, reasoning that an await sends nothing and its
request addresses a promise rather than crossing with a message. That clause
is in the rule text now and was not ruled.

## 8. Split a relay module into its protocol and its messages — considered

A runner implements a relay structurally and names only its messages, but
the messages and the protocol share one module, so a runner's import cannot
say whether it *implements* or *uses* the relay. Splitting them is what the
uses/implements/directly-uses taxonomy needs before the analyzer could
enforce "an implementer does not import its interface". Recorded in
`TODOS.md`; `ports/` has the identical shape and would follow.

## 9. Obligations, not only permissions

Every adapter row today says what a kind may hold. Section 3 adds the first
row that says what must exist elsewhere for a class to be its kind. The same
shape applies to the rest, and the build should verify which already exist:

| kind | must exist elsewhere |
|---|---|
| runtime | a runner that sends to every handler it registers and every promise it names |
| runner | a runtime handler that every method reaches |
| handler | the context client; no method named for a relay operation |
| gateway, repository | exactly one port in `application/ports/` whose methods it implements, checked by method set since an implementer never imports its protocol |

## Not analyzer work, but gating the build

- **minimal is non-conformant.** Its inline engine has no invocation
  context, so `C` has nothing to bind. It keeps its shape under a `TODOS.md`
  entry rather than getting a pretend context.
- **Runner tests.** A runner reaches its far side by its real name, so a
  test that serves a fake `CallStoreActions` displaces the app's endpoint on
  a shared Restate. Either the adapter tier gets its own Restate container,
  or the tests go through the app's real services, which works for every far
  side CI can run (the store actions and the orchestrator) and not for the
  two that call LiveKit. Unruled.
- **The worker.** The warmup fact the handler still invents, `say` on
  `CallAgent`, the SDK subclass carrying the one TB052 marker, and an empty
  turn raising a bare `ValueError` through a published client operation.
  Handler questions now; none blocks the analyzer work.

## Order

1. Section 3 and the mirror: independent, small, ships on its own.
2. Sections 1, 2, 4, 5 as one build: library kind, orchestrator clients,
   runners by name, runtime constructs nothing, workflow implementations in
   `component/`, the closed import rule, the far-side derivation re-cut,
   docs and skill, three trees and the generator, runner tests last.
3. Section 6 after its confirmation; section 7 needs only a ruling; section
   8 is its own design.

## Rejected on the way, with the reason

- Constructor protocols (`__call__` protocols the runtime is handed): correct
  under mypy, but a new kind of thing whose only job is satisfying the rule.
- The invocation passed as an argument through orchestrator and relay
  methods: a dependency in argument position, the *accepts* case; the
  application would carry an adapter's dependency in its signatures.
- An engine object of our own holding the context in task-local storage: no
  `ts.*` is ever instantiated, and the indirection was hard to follow.
- The SDK's `restate.server_context.current_context()`: one module below the
  public surface, returns the base type so a cast is needed, and leaves the
  handler ignoring its first argument.
- A port with an opaque `ts.Invocation` parameter: the inward-flowing handle
  forces a narrowing in the implementation that the store never needs.
- Reusing `ts.Store`: its rule text keys on `transaction()`, on the holder
  being application code, and on the yield being a repository.
