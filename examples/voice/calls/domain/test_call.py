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
def agent_turn_spec(text: str = "hi, may I have your name?") -> domain.AgentTurnSpec:
    return domain.AgentTurnSpec(text=text)


@ts.helper
def person_input_spec(kind: str = "turn_completed", text: str = "my name is Grace") -> domain.PersonInputSpec:
    return domain.PersonInputSpec(kind=kind, text=text)


class TestCall:
    def test_a_call_constructs_from_its_spec(self) -> None:
        call_spec = domain.CallSpec(
            call_id="c1", person=domain.PersonSpec(name="Ada", phone_number="+15555550100"), turns=(), step="ask_name"
        )
        call = domain.Call(call_spec)
        assert str(call.identity) == call_spec.call_id
        assert str(call.person.name) == call_spec.person.name
        assert str(call.person.phone_number) == call_spec.person.phone_number
        assert str(call.step) == call_spec.step
        assert call.conversation == domain.Conversation(domain.ConversationSpec(call_spec.turns))

    def test_after_agent_playback_the_call_waits_for_a_response(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        assert call.progress() is domain.CallProgress.AWAITING_RESPONSE

    def test_speech_start_changes_the_wait_without_needing_a_transcript(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        call.receive(domain.PersonInput(person_input_spec(kind="speech_started", text="")))
        assert call.progress() is domain.CallProgress.PERSON_SPEAKING
        assert len(call.conversation.turns) == 1

    def test_a_completed_turn_is_ready_for_interpretation_immediately(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        call.receive(domain.PersonInput(person_input_spec(text="my name is Grace")))
        assert call.progress() is domain.CallProgress.INTERPRETING_TURN
        assert call.conversation.turns[-1] == domain.Turn(
            domain.TurnSpec(speaker="person", utterances=("my name is Grace",))
        )

    def test_no_response_is_distinct_from_a_completed_turn(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        call.receive(domain.PersonInput(person_input_spec(kind="no_response", text="")))
        assert call.progress() is domain.CallProgress.NO_RESPONSE
        assert len(call.conversation.turns) == 1

    def test_a_late_deadline_does_not_end_active_speech(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        call.receive(domain.PersonInput(person_input_spec(kind="speech_started", text="")))
        call.receive(domain.PersonInput(person_input_spec(kind="no_response", text="")))
        assert call.progress() is domain.CallProgress.PERSON_SPEAKING

    def test_no_response_allows_a_followup_prompt(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        call.receive(domain.PersonInput(person_input_spec(kind="no_response", text="")))
        call.response_missing()
        assert call.progress() is domain.CallProgress.AGENTS_TURN

    def test_interpretation_records_a_name_before_the_farewell_is_spoken(self) -> None:
        call = domain.Call(call_spec(name="Ada"))
        call.receive(domain.PersonInput(person_input_spec()))
        call.interpreted(domain.InterpretedTurn(domain.InterpretedTurnSpec(person_names=("Grace",))))
        assert str(call.person.name) == "Grace"
        assert call.progress() is domain.CallProgress.AGENTS_TURN
        assert "Grace" in str(call.instructions)
        call.agent_said(domain.AgentTurn(agent_turn_spec(text="Goodbye Grace")))
        assert call.progress() is domain.CallProgress.ENDED

    def test_an_unrecognized_name_allows_another_question(self) -> None:
        call = domain.Call(call_spec())
        call.receive(domain.PersonInput(person_input_spec(text="What?")))
        call.interpreted(domain.InterpretedTurn(domain.InterpretedTurnSpec(person_names=())))
        assert call.progress() is domain.CallProgress.AGENTS_TURN
        assert str(call.step) == "ask_name"

    def test_empty_agent_output_does_not_start_the_response_window(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec(text=" ")))
        assert call.progress() is domain.CallProgress.AGENTS_TURN
        assert call.conversation.turns == ()

    def test_listening_and_speaking_have_different_instructions(self) -> None:
        call = domain.Call(call_spec())
        assert call.listening_instructions != call.instructions
        assert "JSON" in str(call.listening_instructions)
        assert "ask for their name" in str(call.instructions)

    def test_a_step_the_domain_does_not_know_is_refused(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Call(call_spec(step="haggle"))

    def test_an_empty_completed_turn_releases_the_speech_wait_without_an_interpretation(self) -> None:
        call = domain.Call(call_spec())
        call.agent_said(domain.AgentTurn(agent_turn_spec()))
        call.receive(domain.PersonInput(person_input_spec(kind="speech_started", text="")))
        call.receive(domain.PersonInput(person_input_spec(text="")))
        assert call.progress() is domain.CallProgress.AGENTS_TURN


class TestPersonInput:
    def test_completed_input_preserves_the_normalized_text_and_kind(self) -> None:
        person_input_spec = domain.PersonInputSpec(kind="turn_completed", text=" Grace ")
        person_input = domain.PersonInput(person_input_spec)
        assert person_input.utterances == (domain.Utterance(person_input_spec.text),)
        assert person_input.decide() is domain.PersonInputDecision.TURN_COMPLETED
        assert person_input == domain.PersonInput(domain.PersonInputSpec(kind="turn_completed", text="Grace"))

    def test_empty_completed_turn_preserves_the_boundary_without_an_utterance(self) -> None:
        person_input = domain.PersonInput(person_input_spec(text=" "))
        assert person_input.decide() is domain.PersonInputDecision.TURN_COMPLETED
        assert person_input.utterances == ()

    def test_unknown_kind_is_invalid(self) -> None:
        with pytest.raises(ValueError):
            domain.PersonInput(person_input_spec(kind="static"))


class TestInterpretedTurn:
    def test_names_are_normalized_and_empty_names_ignored(self) -> None:
        interpreted_turn = domain.InterpretedTurn(domain.InterpretedTurnSpec(person_names=(" Grace ", " ")))
        assert interpreted_turn.person_names == (domain.PersonName("Grace"),)
        assert interpreted_turn == domain.InterpretedTurn(domain.InterpretedTurnSpec(person_names=("Grace",)))


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
    def test_a_turn_holds_its_utterances_in_order(self) -> None:
        turn_spec = domain.TurnSpec(speaker="person", utterances=("my name is", "Ada"))

        turn = domain.Turn(turn_spec)

        assert str(turn.speaker) == turn_spec.speaker
        assert [str(utterance) for utterance in turn.utterances] == ["my name is", "Ada"]

    def test_a_turn_in_which_nothing_is_said_is_refused(self) -> None:
        with pytest.raises(ValueError):
            domain.Turn(domain.TurnSpec(speaker="person", utterances=()))

    def test_turns_equal_by_value(self) -> None:
        first = domain.Turn(domain.TurnSpec(speaker="person", utterances=("my name is Ada",)))
        second = domain.Turn(domain.TurnSpec(speaker="person", utterances=("my name is Ada",)))

        assert first == second
        assert first != domain.Turn(domain.TurnSpec(speaker="agent", utterances=("my name is Ada",)))


class TestConversation:
    def test_a_conversation_holds_its_turns_in_order(self) -> None:
        conversation_spec = domain.ConversationSpec(
            turns=(
                domain.TurnSpec(speaker="agent", utterances=("what is your name?",)),
                domain.TurnSpec(speaker="person", utterances=("Ada",)),
            )
        )

        conversation = domain.Conversation(conversation_spec)

        assert [str(turn.speaker) for turn in conversation.turns] == ["agent", "person"]

    def test_an_empty_conversation_has_no_turns(self) -> None:
        conversation = domain.Conversation(domain.ConversationSpec(turns=()))

        assert conversation.turns == ()

    def test_adding_a_turn_answers_a_longer_conversation_and_leaves_this_one_alone(self) -> None:
        conversation = domain.Conversation(
            domain.ConversationSpec(turns=(domain.TurnSpec(speaker="agent", utterances=("what is your name?",)),))
        )

        longer = conversation.with_turn(domain.TurnSpec(speaker="person", utterances=("Ada",)))

        assert [str(turn.speaker) for turn in longer.turns] == ["agent", "person"]
        assert len(conversation.turns) == 1

    def test_adding_an_utterance_extends_the_last_turn(self) -> None:
        conversation = domain.Conversation(
            domain.ConversationSpec(turns=(domain.TurnSpec(speaker="person", utterances=("my name is",)),))
        )

        longer = conversation.with_utterance("Ada")

        assert [[str(u) for u in turn.utterances] for turn in longer.turns] == [["my name is", "Ada"]]

    def test_an_utterance_cannot_extend_a_conversation_with_no_turn(self) -> None:
        conversation = domain.Conversation(domain.ConversationSpec(turns=()))

        with pytest.raises(ValueError):
            conversation.with_utterance("Ada")

    def test_conversations_equal_by_their_turns(self) -> None:
        first = domain.Conversation(
            domain.ConversationSpec(turns=(domain.TurnSpec(speaker="person", utterances=("Ada",)),))
        )
        second = domain.Conversation(
            domain.ConversationSpec(turns=(domain.TurnSpec(speaker="person", utterances=("Ada",)),))
        )

        assert first == second
        assert first != domain.Conversation(domain.ConversationSpec(turns=()))


@ts.helper
def _user_turn_completed_spec(
    call_id: str = "c7", text: str | None = "my name is Grace"
) -> domain.UserTurnCompletedSpec:
    return domain.UserTurnCompletedSpec(call_id=call_id, text=text)


class TestUserTurnCompleted:
    def test_a_completed_turn_preserves_the_call_and_normalizes_the_utterance(self) -> None:
        user_turn_completed_spec = _user_turn_completed_spec(text=" \tmy name is Grace\n")

        user_turn_completed = domain.UserTurnCompleted(user_turn_completed_spec)

        assert user_turn_completed.call_id == domain.CallId(user_turn_completed_spec.call_id)
        assert user_turn_completed.utterances == (domain.Utterance("my name is Grace"),)

    def test_a_turn_without_text_produces_no_deliverable_utterance(self) -> None:
        user_turn_completed = domain.UserTurnCompleted(_user_turn_completed_spec(text=None))

        assert user_turn_completed.utterances == ()

    def test_a_blank_turn_produces_no_deliverable_utterance(self) -> None:
        user_turn_completed = domain.UserTurnCompleted(_user_turn_completed_spec(text=" \t\n"))

        assert user_turn_completed.utterances == ()

    def test_events_with_the_same_normalized_utterance_and_call_are_equal(self) -> None:
        first = domain.UserTurnCompleted(_user_turn_completed_spec(text=" Grace "))
        second = domain.UserTurnCompleted(_user_turn_completed_spec(text="Grace"))

        assert first == second

    def test_events_for_different_calls_are_not_equal(self) -> None:
        first = domain.UserTurnCompleted(_user_turn_completed_spec(call_id="c1"))
        second = domain.UserTurnCompleted(_user_turn_completed_spec(call_id="c2"))

        assert first != second


class TestUserStateChanged:
    def test_speaking_delivers_the_call_identity(self) -> None:
        user_state_changed_spec = domain.UserStateChangedSpec(call_id="c7", new_state="speaking")
        user_state_changed = domain.UserStateChanged(user_state_changed_spec)

        assert user_state_changed.call_id == domain.CallId(user_state_changed_spec.call_id)
        assert user_state_changed.decide() is domain.InputDeliveryDecision.DELIVER

    @pytest.mark.parametrize("new_state", ["listening", "away"])
    def test_other_known_states_are_ignored(self, new_state: str) -> None:
        user_state_changed = domain.UserStateChanged(domain.UserStateChangedSpec(call_id="c7", new_state=new_state))

        assert user_state_changed.decide() is domain.InputDeliveryDecision.IGNORE

    def test_unknown_state_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            domain.UserStateChanged(domain.UserStateChangedSpec(call_id="c7", new_state="thinking"))

    def test_equality_includes_the_call_and_state(self) -> None:
        user_state_changed = domain.UserStateChanged(domain.UserStateChangedSpec(call_id="c7", new_state="speaking"))

        assert user_state_changed == domain.UserStateChanged(domain.UserStateChangedSpec(call_id="c7", new_state="speaking"))
        assert user_state_changed != domain.UserStateChanged(domain.UserStateChangedSpec(call_id="c8", new_state="speaking"))
        assert user_state_changed != domain.UserStateChanged(domain.UserStateChangedSpec(call_id="c7", new_state="listening"))
