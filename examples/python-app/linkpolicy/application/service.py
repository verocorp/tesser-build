from __future__ import annotations

import tesser.application as ts

import linkpolicy.application.ports as ports
import linkpolicy.client as client
import linkpolicy.domain as domain
import tesser.errors as errors


class MapToRecordVerdictRequest(ts.Mapper, ports.RecordVerdictRequest):

    def __init__(self, verdict: domain.Verdict) -> None:
        super().__init__(
            target_url=str(verdict.target_url),
            decision=ports.VerdictDecision(str(verdict.allowed)),
            reason=str(verdict.reason),
        )


class MapToCheckResponse(ts.Mapper, client.CheckResponse):

    def __init__(self, verdict: domain.Verdict) -> None:
        super().__init__(decision=str(verdict.allowed), reason=str(verdict.reason))


class MapToVerdictView(ts.Mapper, client.VerdictView):

    def __init__(self, verdict_record: ports.VerdictRecord) -> None:
        super().__init__(
            verdict_record.target_url, verdict_record.decision.value, verdict_record.reason
        )


class MapToListVerdictsResponse(ts.Mapper, client.ListVerdictsResponse):

    def __init__(self, list_verdicts_response: ports.ListVerdictsResponse) -> None:
        super().__init__(
            verdicts=tuple(
                MapToVerdictView(record) for record in list_verdicts_response.verdicts
            )
        )


class LinkPolicyService(ts.ApplicationService):

    def __init__(self, verdict_repository: ports.VerdictRepository) -> None:
        self._verdict_repository = verdict_repository
        self._policy = domain.Policy(domain.PolicySpec())

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        try:
            target_url = domain.TargetURL(check_request.target_url)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        verdict = self._policy.evaluate(target_url)
        try:
            self._verdict_repository.record(MapToRecordVerdictRequest(verdict))
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the verdict store is unavailable"
            ) from store_error
        return MapToCheckResponse(verdict)

    def list_verdicts(
        self, list_verdicts_request: client.ListVerdictsRequest
    ) -> client.ListVerdictsResponse:
        try:
            list_verdicts_response = self._verdict_repository.all(ports.ListVerdictsRequest())
        except ports.StoreUnavailable as store_error:
            raise client.Unavailable(
                message="the verdict store is unavailable"
            ) from store_error
        return MapToListVerdictsResponse(list_verdicts_response=list_verdicts_response)
