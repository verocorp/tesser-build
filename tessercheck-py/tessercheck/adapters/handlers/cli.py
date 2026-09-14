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
            check_tree_response = self._tessercheck_client.check_tree(client.CheckTreeRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(
            1 if check_tree_response.findings else 0,
            stdout="\n".join(check_tree_response.findings),
            stderr="",
        )

    def mark(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _MARK_USAGE)
        try:
            mark_debt_response = self._tessercheck_client.mark_debt(client.MarkDebtRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        told = [f"marked {mark_debt_response.files} file(s)"]
        if mark_debt_response.remaining:
            told.append(
                f"{len(mark_debt_response.remaining)} finding(s) this cannot mark:"
            )
            told.extend(mark_debt_response.remaining)
        return protocol.CliResponse(
            1 if mark_debt_response.remaining else 0, stdout="\n".join(told), stderr=""
        )

    def rename(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _RENAME_USAGE)
        try:
            apply_renames_response = self._tessercheck_client.apply_renames(client.ApplyRenamesRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        told = [f"renamed {apply_renames_response.files} file(s)"]
        if apply_renames_response.remaining:
            told.append(
                f"{len(apply_renames_response.remaining)} finding(s) this cannot repair:"
            )
            told.extend(apply_renames_response.remaining)
        return protocol.CliResponse(
            1 if apply_renames_response.remaining else 0, stdout="\n".join(told), stderr=""
        )

    def rulebook(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        root = cli_request.arg(0, _HERE)
        cli_request.no_extra_args(1, _RULES_USAGE)
        try:
            render_rulebook_response = self._tessercheck_client.render_rulebook(client.RenderRulebookRequest(tree=root))
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.CliResponse(2, stdout="", stderr=error.message)
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse(0, stdout=render_rulebook_response.rendered, stderr="")
