from __future__ import annotations

import protocol


class TestPersonUtterance:

    def test_an_utterance_names_the_call_it_was_heard_on(self) -> None:
        person_utterance = protocol.PersonUtterance(call_id="c7", text="my name is Ada")

        assert (person_utterance.call_id, person_utterance.text) == ("c7", "my name is Ada")


class TestPersonAnswered:

    def test_an_answer_names_the_call_it_was_on(self) -> None:
        person_answered = protocol.PersonAnswered(call_id="c7")

        assert person_answered.call_id == "c7"
