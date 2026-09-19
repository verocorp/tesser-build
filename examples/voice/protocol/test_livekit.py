from __future__ import annotations

import tesser.testing as ts
import livekit.rtc as livekit_rtc

import protocol


@ts.fake
class FakeJobRequest(protocol.JobRequest):

    async def accept(self, *, identity: str) -> None:
        return None


@ts.fake
class FakeJobContext(protocol.JobContext):

    def __init__(self) -> None:
        self._room = livekit_rtc.Room()

    @property
    def room(self) -> livekit_rtc.Room:
        return self._room

    async def connect(self) -> None:
        return None


class TestVoiceAcceptJobRequest:

    def test_carries_the_job_offer_that_can_be_accepted(self) -> None:
        fake_job_request = FakeJobRequest()

        voice_accept_job_request = protocol.VoiceAcceptJobRequest(fake_job_request)

        assert voice_accept_job_request.job_request is fake_job_request


class TestVoiceStartJobRequest:

    async def test_carries_the_assigned_jobs_connection(self) -> None:
        fake_job_context = FakeJobContext()

        voice_start_job_request = protocol.VoiceStartJobRequest(fake_job_context)

        assert voice_start_job_request.job_context is fake_job_context
