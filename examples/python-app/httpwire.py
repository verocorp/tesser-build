from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from errors import DomainError, InfraError, status_for

JSONObject = dict[str, object]


class BadRequest(Exception):
    pass


@dataclass(frozen=True)
class Response:
    status: int
    body: JSONObject


def problem(code: str, detail: str) -> JSONObject:
    return {"type": f"/problems/{code}", "detail": detail}


def respond(run: Callable[[], Response]) -> Response:
    try:
        return run()
    except BadRequest as e:
        return Response(400, problem("malformed_request", str(e)))
    except DomainError as e:
        return Response(status_for(e.kind), problem(e.code, e.message))
    except InfraError:
        return Response(503, problem("unavailable", "a dependency is unavailable; please retry"))
    except Exception:
        return Response(500, problem("internal", "unexpected error"))
