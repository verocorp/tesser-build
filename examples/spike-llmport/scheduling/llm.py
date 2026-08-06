from __future__ import annotations

from typing import assert_never

import tesser.application as ts

from scheduling.domain import DomainError, DomainKind


@ts.function
def llm_visible_message(err: DomainError) -> str:
    match err.kind:
        case DomainKind.VALIDATION:
            return f"{err.message}; correct the arguments and call the tool again"
        case DomainKind.NOT_FOUND:
            return f"{err.message}; tell the caller and end the conversation"
        case DomainKind.CONFLICT:
            return f"{err.message}; offer the caller the updated slots"
    assert_never(err.kind)
