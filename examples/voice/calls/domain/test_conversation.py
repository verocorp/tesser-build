from __future__ import annotations

import pytest

import calls.domain as domain


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
