from __future__ import annotations

import typing

import tesser.adapters as ts

import protocol
import tessercheck.client as client

_CHECK_USAGE: typing.Final[str] = "usage: check [tree]"

_RULES_USAGE: typing.Final[str] = "usage: rules [tree]"

_RENAME_USAGE: typing.Final[str] = "usage: rename [tree]"

_MARK_USAGE: typing.Final[str] = "usage: mark [tree]"

_HERE: typing.Final[str] = "."


class Handler(ts.Handler):

    def __init__(self, tessercheck_client: client.TessercheckClient) -> None:
        self._tessercheck_client = tessercheck_client

    def check(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _CHECK_USAGE)
        try:
            check_response = self._tessercheck_client.check(client.CheckRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(
            1 if check_response.findings else 0,
            stdout="\n".join(check_response.findings),
            stderr="",
        )

    def mark(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _MARK_USAGE)
        try:
            mark_response = self._tessercheck_client.mark(client.MarkRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        told = [f"marked {mark_response.files} file(s)"]
        if mark_response.remaining:
            told.append(
                f"{len(mark_response.remaining)} finding(s) this cannot mark:"
            )
            told.extend(mark_response.remaining)
        return protocol.CliResponse(
            1 if mark_response.remaining else 0, stdout="\n".join(told), stderr=""
        )

    def rename(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _RENAME_USAGE)
        try:
            rename_response = self._tessercheck_client.rename(client.RenameRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        told = [f"renamed {rename_response.files} file(s)"]
        if rename_response.remaining:
            told.append(
                f"{len(rename_response.remaining)} finding(s) this cannot repair:"
            )
            told.extend(rename_response.remaining)
        return protocol.CliResponse(
            1 if rename_response.remaining else 0, stdout="\n".join(told), stderr=""
        )

    def rulebook(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _RULES_USAGE)
        try:
            rulebook_response = self._tessercheck_client.rulebook(client.RulebookRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(0, stdout=rulebook_response.rendered, stderr="")
