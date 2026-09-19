from __future__ import annotations

import typing

import tesser.srv as ts
import livekit.rtc as livekit_rtc


class JobRequest(ts.Port, typing.Protocol):

    async def accept(self, *, identity: str) -> None: ...


class JobContext(ts.Port, typing.Protocol):

    @property
    def room(self) -> livekit_rtc.Room: ...

    async def connect(self) -> None: ...


class VoiceAcceptJobRequest(ts.Request):

    def __init__(self, job_request: JobRequest) -> None:
        super().__init__(job_request=job_request)

    job_request: JobRequest


class VoiceStartJobRequest(ts.Request):

    def __init__(self, job_context: JobContext) -> None:
        super().__init__(job_context=job_context)

    job_context: JobContext
