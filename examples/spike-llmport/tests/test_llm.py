from scheduling.domain import DomainError, DomainKind
from scheduling.llm import llm_visible_message


def test_every_kind_maps_to_a_model_visible_message() -> None:
    for kind in DomainKind:
        message = llm_visible_message(DomainError(kind, "code", "went wrong"))
        assert "went wrong" in message


def test_validation_guides_the_model_to_retry() -> None:
    message = llm_visible_message(
        DomainError(DomainKind.VALIDATION, "bad_argument", "slot is not available")
    )
    assert "call the tool again" in message


def test_conflict_guides_the_model_to_reoffer() -> None:
    message = llm_visible_message(
        DomainError(DomainKind.CONFLICT, "slot_taken", "slot was just taken")
    )
    assert "updated slots" in message
