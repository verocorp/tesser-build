from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.domain as domain
import tesser.errors as errors


@ts.helper
def call_spec(
    call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100", step: str = "ask_name"
) -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id, person=domain.PersonSpec(name=name, phone_number=phone_number), turns=(), step=step
    )


@ts.helper
def agent_turn_spec(text: str = "hi, may I have your name?", person_name: str = "") -> domain.AgentTurnSpec:
    return domain.AgentTurnSpec(text=text, person_names=(person_name,) if person_name else ())


class TestCall:

    def test_a_call_constructs_from_its_spec(self) -> None:
        person_spec = domain.PersonSpec(name="Ada", phone_number="+15555550100")
        call_spec = domain.CallSpec(call_id="c1", person=person_spec, turns=(), step="ask_name")

        call = domain.Call(call_spec)

        assert str(call.identity) == call_spec.call_id
        assert str(call.person.name) == person_spec.name
        assert str(call.person.phone_number) == person_spec.phone_number
        assert str(call.step) == "ask_name"

    def test_a_call_carries_the_turns_it_was_given_in_order(self) -> None:
        call_spec = domain.CallSpec(
            call_id="c1",
            person=domain.PersonSpec(name="Ada", phone_number="+15555550100"),
            turns=(
                domain.TurnSpec(speaker="agent", text="hi, may I have your name?"),
                domain.TurnSpec(speaker="person", text="my name is"),
            ),
            step="ask_name",
        )

        call = domain.Call(call_spec)

        assert [str(turn.utterance) for turn in call.conversation.turns] == ["hi, may I have your name?", "my name is"]

    def test_two_calls_placed_for_the_same_person_hold_an_equal_person(self) -> None:
        first = domain.Call(call_spec(call_id="c1"))
        second = domain.Call(call_spec(call_id="c2"))

        assert first.person == second.person

    def test_a_call_in_which_nothing_has_been_said_is_the_agents_turn(self) -> None:
        call = domain.Call(call_spec(step="ask_name"))

        assert call.progress() is domain.CallProgress.AGENTS_TURN

    def test_after_the_agent_speaks_it_is_the_persons_turn(self) -> None:
        call = domain.Call(call_spec())

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="hi, may I have your name?")))

        assert call.progress() is domain.CallProgress.PERSONS_TURN

    def test_after_the_person_speaks_it_is_the_agents_turn(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec(text="hi, may I have your name?")))

        call.person_said("my name is Grace")

        assert call.progress() is domain.CallProgress.AGENTS_TURN

    def test_an_agent_turn_with_nothing_said_leaves_it_the_agents_turn(self) -> None:
        call = domain.Call(call_spec())

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="   ")))

        assert call.progress() is domain.CallProgress.AGENTS_TURN

    def test_a_call_that_is_done_has_ended(self) -> None:
        call = domain.Call(call_spec(step="done"))

        assert call.progress() is domain.CallProgress.ENDED

    def test_what_the_agent_says_joins_the_conversation_as_the_agents_turn(self) -> None:
        call = domain.Call(call_spec())

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="hi, may I have your name?")))

        assert [(str(turn.speaker), str(turn.utterance)) for turn in call.conversation.turns] == [
            ("agent", "hi, may I have your name?")
        ]

    def test_what_the_person_says_joins_the_conversation_as_the_persons_turn(self) -> None:
        call = domain.Call(call_spec())

        call.person_said("my name is Grace")

        assert [(str(turn.speaker), str(turn.utterance)) for turn in call.conversation.turns] == [
            ("person", "my name is Grace")
        ]

    def test_an_agent_turn_with_nothing_said_adds_no_turn(self) -> None:
        call = domain.Call(call_spec())

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="   ")))

        assert call.conversation.turns == ()

    def test_a_name_the_agent_recorded_becomes_the_persons_name(self) -> None:
        call = domain.Call(call_spec(name="Ada"))

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="nice to meet you, Grace", person_name="Grace")))

        assert str(call.person.name) == "Grace"

    def test_a_name_the_agent_recorded_ends_the_call(self) -> None:
        call = domain.Call(call_spec())

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="nice to meet you, Grace", person_name="Grace")))

        assert call.progress() is domain.CallProgress.ENDED

    def test_an_agent_turn_with_no_name_recorded_keeps_asking(self) -> None:
        call = domain.Call(call_spec(name="Ada"))

        call.agent_said(domain.AgentTurn(agent_turn_spec(text="sorry, what was your name?")))

        assert (str(call.step), str(call.person.name)) == ("ask_name", "Ada")

    def test_the_instructions_follow_the_step(self) -> None:
        asking = domain.Call(call_spec(step="ask_name"))
        done = domain.Call(call_spec(step="done"))

        assert "person_gave_name" in str(asking.instructions)
        assert "Say nothing" in str(done.instructions)

    def test_a_step_the_domain_does_not_know_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as raised:
            domain.Call(call_spec(step="haggle"))

        assert raised.value.code == "invalid_step"


class TestTranscript:

    def test_words_are_an_utterance(self) -> None:
        assert domain.Transcript("my name is Grace").decide() is domain.Hearing.UTTERANCE

    def test_blank_text_is_silence(self) -> None:
        assert domain.Transcript("   ").decide() is domain.Hearing.SILENCE


class TestCallPresence:

    def test_a_call_the_store_found_decides_that_it_was_found(self) -> None:
        call_presence = domain.CallPresence(domain.CallPresenceSpec(presence="found"))

        assert call_presence.decide() is domain.CallLookup.FOUND

    def test_a_call_the_store_did_not_find_decides_that_it_was_not_found(self) -> None:
        call_presence = domain.CallPresence(domain.CallPresenceSpec(presence="not_found"))

        assert call_presence.decide() is domain.CallLookup.NOT_FOUND

    def test_a_presence_the_domain_does_not_know_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as raised:
            domain.CallPresence(domain.CallPresenceSpec(presence="maybe"))

        assert raised.value.code == "invalid_presence"


class TestCallId:

    def test_a_call_id_equals_by_value(self) -> None:
        first = domain.CallId("c1")
        second = domain.CallId("c1")

        assert first == second
        assert first != domain.CallId("c2")


class TestPersona:

    def test_a_persona_equals_by_value(self) -> None:
        first = domain.Persona("a friendly receptionist")
        second = domain.Persona("a friendly receptionist")

        assert first == second
        assert first != domain.Persona("a terse dispatcher")

    def test_a_persona_reads_back_as_the_words_it_was_given(self) -> None:
        persona = domain.Persona("  a friendly receptionist ")

        assert str(persona) == "a friendly receptionist"

    def test_a_blank_persona_is_refused(self) -> None:
        with pytest.raises(ValueError):
            domain.Persona("   ")


class TestSpeaker:

    def test_a_speaker_equals_by_value(self) -> None:
        first = domain.Speaker("agent")
        second = domain.Speaker("agent")

        assert first == second
        assert first != domain.Speaker("person")

    def test_someone_who_is_neither_the_agent_nor_the_person_is_refused(self) -> None:
        with pytest.raises(ValueError):
            domain.Speaker("operator")


class TestUtterance:

    def test_an_utterance_reads_back_as_the_words_said(self) -> None:
        utterance = domain.Utterance("  my name is Ada ")

        assert str(utterance) == "my name is Ada"

    def test_saying_nothing_is_refused(self) -> None:
        with pytest.raises(ValueError):
            domain.Utterance("   ")


class TestTurn:

    def test_a_turn_constructs_from_its_spec(self) -> None:
        turn_spec = domain.TurnSpec(speaker="person", text="my name is Ada")

        turn = domain.Turn(turn_spec)

        assert str(turn.speaker) == turn_spec.speaker
        assert str(turn.utterance) == turn_spec.text

    def test_turns_equal_by_value(self) -> None:
        first = domain.Turn(domain.TurnSpec(speaker="person", text="my name is Ada"))
        second = domain.Turn(domain.TurnSpec(speaker="person", text="my name is Ada"))

        assert first == second
        assert first != domain.Turn(domain.TurnSpec(speaker="agent", text="my name is Ada"))


class TestConversation:

    def test_a_conversation_holds_its_turns_in_order(self) -> None:
        conversation_spec = domain.ConversationSpec(
            turns=(
                domain.TurnSpec(speaker="agent", text="what is your name?"),
                domain.TurnSpec(speaker="person", text="Ada"),
            )
        )

        conversation = domain.Conversation(conversation_spec)

        assert [str(turn.utterance) for turn in conversation.turns] == ["what is your name?", "Ada"]

    def test_an_empty_conversation_has_no_turns(self) -> None:
        conversation = domain.Conversation(domain.ConversationSpec(turns=()))

        assert conversation.turns == ()

    def test_adding_a_turn_answers_a_longer_conversation_and_leaves_this_one_alone(self) -> None:
        conversation = domain.Conversation(
            domain.ConversationSpec(turns=(domain.TurnSpec(speaker="agent", text="what is your name?"),))
        )

        longer = conversation.with_turn(domain.TurnSpec(speaker="person", text="Ada"))

        assert [str(turn.speaker) for turn in longer.turns] == ["agent", "person"]
        assert len(conversation.turns) == 1

    def test_conversations_equal_by_their_turns(self) -> None:
        first = domain.Conversation(domain.ConversationSpec(turns=(domain.TurnSpec(speaker="person", text="Ada"),)))
        second = domain.Conversation(domain.ConversationSpec(turns=(domain.TurnSpec(speaker="person", text="Ada"),)))

        assert first == second
        assert first != domain.Conversation(domain.ConversationSpec(turns=()))
