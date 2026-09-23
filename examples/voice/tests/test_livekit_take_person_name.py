from __future__ import annotations

import asyncio
import os

import pytest

import app as app
import calls.client as calls_client
import simulated.person as simulated_person


class TestTakePersonName:
    async def test_the_agent_asks_hears_and_greets_the_person_by_the_name_it_heard(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        voice_app = app.load()
        await voice_app.open()
        try:
            for person_name in ("Sarah", "David", "Michael"):
                person = simulated_person.Person(
                    url=os.environ["LIVEKIT_URL"],
                    api_key=os.environ["LIVEKIT_API_KEY"],
                    api_secret=os.environ["LIVEKIT_API_SECRET"],
                    agent_name=os.environ["LIVEKIT_AGENT_NAME"],
                    name=person_name,
                    answers=simulated_person.WHEN_ASKED,
                )
                answering = asyncio.create_task(person.answer())
                try:
                    place_call_response = await asyncio.wait_for(
                        voice_app.calls.client.place_call(calls_client.PlaceCallRequest()), 180.0
                    )
                    await asyncio.wait_for(answering, 30.0)
                finally:
                    answering.cancel()
                    await asyncio.gather(answering, return_exceptions=True)
                get_call_response = await voice_app.calls.client.get_call(
                    calls_client.GetCallRequest(call_id=place_call_response.call_id)
                )

                assert person.room_name == place_call_response.call_id
                assert get_call_response.call.person_name == person_name
                assert person.heard, person.said
                assert person_name.casefold() in person.heard[-1].casefold(), person.heard
        finally:
            await voice_app.close()

    async def test_the_person_hears_the_whole_goodbye_before_the_line_drops(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        voice_app = app.load()
        await voice_app.open()
        try:
            person = simulated_person.Person(
                url=os.environ["LIVEKIT_URL"],
                api_key=os.environ["LIVEKIT_API_KEY"],
                api_secret=os.environ["LIVEKIT_API_SECRET"],
                agent_name=os.environ["LIVEKIT_AGENT_NAME"],
                name="Sarah",
                answers=simulated_person.WHEN_ASKED,
            )
            answering = asyncio.create_task(person.answer())
            try:
                await asyncio.wait_for(
                    voice_app.calls.client.place_call(calls_client.PlaceCallRequest()), 180.0
                )
                await asyncio.wait_for(answering, 30.0)
            finally:
                answering.cancel()
                await asyncio.gather(answering, return_exceptions=True)

            heard_at = [at for at, (kind, _) in enumerate(person.events) if kind == simulated_person.HEARD]
            dropped_at = [at for at, (kind, _) in enumerate(person.events) if kind == simulated_person.DROPPED]
            assert heard_at and dropped_at, person.events
            assert heard_at[-1] < dropped_at[0], person.events
            assert "sarah" in person.events[heard_at[-1]][1].casefold(), person.events
            assert person.events[dropped_at[0]][1] == "ROOM_DELETED", person.events
        finally:
            await voice_app.close()

    async def test_an_answer_spoken_over_the_question_is_not_lost(self) -> None:
        if os.environ.get("VOICE_EVALS") != "1":
            pytest.skip("set VOICE_EVALS=1 and run scripts/verify voice with LiveKit credentials, Postgres and Restate")
        voice_app = app.load()
        await voice_app.open()
        try:
            person = simulated_person.Person(
                url=os.environ["LIVEKIT_URL"],
                api_key=os.environ["LIVEKIT_API_KEY"],
                api_secret=os.environ["LIVEKIT_API_SECRET"],
                agent_name=os.environ["LIVEKIT_AGENT_NAME"],
                name="Sarah",
                answers=simulated_person.OVER_THE_QUESTION,
            )
            answering = asyncio.create_task(person.answer())
            try:
                place_call_response = await asyncio.wait_for(
                    voice_app.calls.client.place_call(calls_client.PlaceCallRequest()), 180.0
                )
                await asyncio.wait_for(answering, 30.0)
            finally:
                answering.cancel()
                await asyncio.gather(answering, return_exceptions=True)
            get_call_response = await voice_app.calls.client.get_call(
                calls_client.GetCallRequest(call_id=place_call_response.call_id)
            )

            assert person.said == ["Sarah."], person.said
            assert get_call_response.call.person_name == "Sarah"
            assert "sarah" in person.heard[-1].casefold(), person.heard
        finally:
            await voice_app.close()
