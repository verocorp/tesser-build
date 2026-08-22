from __future__ import annotations

import tesser.application as ts

import linkpolicy.application.ports.verdict_repository as verdict_repository
import linkpolicy.client.client as client
import linkpolicy.domain.policy as policy


@ts.do_not_use_function
def record_request(verdict: policy.Verdict) -> verdict_repository.RecordVerdictRequest:  # tesser:debt TB051
    return verdict_repository.RecordVerdictRequest(
        target_url=str(verdict.target_url), decision=_decision(verdict), reason=str(verdict.reason)
    )


@ts.do_not_use_function
def check_response(verdict: policy.Verdict) -> client.CheckResponse:  # tesser:debt TB051
    return client.CheckResponse(allowed=str(verdict.allowed) == "allowed", reason=str(verdict.reason))


@ts.do_not_use_function
def verdict_view(record: verdict_repository.VerdictRecord) -> client.VerdictView:  # tesser:debt TB051
    return client.VerdictView(
        record.target_url, record.decision == verdict_repository.VerdictDecision.ALLOWED, record.reason
    )


@ts.do_not_use_function
def _decision(verdict: policy.Verdict) -> verdict_repository.VerdictDecision:  # tesser:debt TB051
    return (
        verdict_repository.VerdictDecision.ALLOWED
        if str(verdict.allowed) == "allowed"
        else verdict_repository.VerdictDecision.DENIED
    )
