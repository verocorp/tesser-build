from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays


class CallOrchestratorApplicationClient(ts.Client, typing.Protocol):

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse: ...


class CallWorkflow[C](ts.Workflow, typing.Protocol):

    def invocation(self, context: C, /) -> typing.AsyncContextManager[CallOrchestratorApplicationClient]: ...


class CallOrchestratorFactory(ts.Factory, typing.Protocol):

    def __call__(
        self,
        dialing_actions_relay: relays.DialingActionsRelay,
        call_orchestrator_signal_relay: relays.CallOrchestratorSignalRelay,
        speech_actions_relay: relays.SpeechActionsRelay,
        call_actions_relay: relays.CallActionsRelay,
        /,
    ) -> CallOrchestratorApplicationClient: ...
