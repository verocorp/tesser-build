import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any

from linkcampaign import (
    AddShortLinkRequest,
    Client,
    CreateCampaignRequest,
    DeactivateShortLinkRequest,
    GetCampaignRequest,
    ShortLinkInput,
)

_CAMPAIGNS = re.compile(r"^/campaigns$")
_CAMPAIGN = re.compile(r"^/campaigns/(?P<id>[^/]+)$")
_LINKS = re.compile(r"^/campaigns/(?P<id>[^/]+)/links$")
_DEACTIVATE = re.compile(r"^/campaigns/(?P<id>[^/]+)/links/(?P<slug>[^/]+)/deactivate$")


def make_handler(client: Client) -> type[BaseHTTPRequestHandler]:

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 (stdlib dispatch name)
            if _CAMPAIGNS.match(self.path):
                self._create_campaign()
            elif (m := _LINKS.match(self.path)) is not None:
                self._add_short_link(m.group("id"))
            elif (m := _DEACTIVATE.match(self.path)) is not None:
                self._deactivate_short_link(m.group("id"), m.group("slug"))
            else:
                self._write_error(HTTPStatus.NOT_FOUND, "no such route")

        def do_GET(self) -> None:  # noqa: N802 (stdlib dispatch name)
            if (m := _CAMPAIGN.match(self.path)) is not None:
                self._get_campaign(m.group("id"))
            else:
                self._write_error(HTTPStatus.NOT_FOUND, "no such route")


        def _create_campaign(self) -> None:
            body = self._read_json()
            if body is None:
                return
            req = CreateCampaignRequest(
                name=str(body.get("name", "")),
                links=tuple(
                    ShortLinkInput(
                        slug=str(l.get("slug", "")),
                        target_url=str(l.get("target_url", "")),
                    )
                    for l in _as_list(body.get("links"))
                ),
            )
            try:
                resp = client.create_campaign(req)
            except ValueError as e:
                return self._write_error(HTTPStatus.UNPROCESSABLE_ENTITY, str(e))
            self._write_json(HTTPStatus.CREATED, resp)

        def _get_campaign(self, campaign_id: str) -> None:
            try:
                resp = client.get_campaign(GetCampaignRequest(campaign_id=campaign_id))
            except (ValueError, LookupError) as e:
                return self._write_error(HTTPStatus.NOT_FOUND, str(e))
            self._write_json(HTTPStatus.OK, resp)

        def _add_short_link(self, campaign_id: str) -> None:
            body = self._read_json()
            if body is None:
                return
            req = AddShortLinkRequest(
                campaign_id=campaign_id,
                slug=str(body.get("slug", "")),
                target_url=str(body.get("target_url", "")),
            )
            try:
                resp = client.add_short_link(req)
            except (ValueError, LookupError) as e:
                return self._write_error(HTTPStatus.UNPROCESSABLE_ENTITY, str(e))
            self._write_json(HTTPStatus.OK, resp)

        def _deactivate_short_link(self, campaign_id: str, slug: str) -> None:
            req = DeactivateShortLinkRequest(campaign_id=campaign_id, slug=slug)
            try:
                resp = client.deactivate_short_link(req)
            except (ValueError, LookupError) as e:
                return self._write_error(HTTPStatus.UNPROCESSABLE_ENTITY, str(e))
            self._write_json(HTTPStatus.OK, resp)


        def _read_json(self) -> dict[str, Any] | None:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                self._write_error(HTTPStatus.BAD_REQUEST, f"invalid JSON: {e}")
                return None
            if not isinstance(payload, dict):
                self._write_error(HTTPStatus.BAD_REQUEST, "expected a JSON object")
                return None
            return payload

        def _write_json(self, status: HTTPStatus, body: object) -> None:
            data = json.dumps(_as_jsonable(body)).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _write_error(self, status: HTTPStatus, message: str) -> None:
            self._write_json(status, {"error": message})

        def log_message(self, format: str, *args: Any) -> None:
            pass

    return Handler


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_jsonable(body: object) -> object:
    from dataclasses import asdict, is_dataclass

    if is_dataclass(body) and not isinstance(body, type):
        return asdict(body)
    return body
