from __future__ import annotations

import http.client as client
import json
import threading

import tesser.testing as ts

import app as app
import specification.component as component
import srv.http as http


@ts.helper
def app_spec(storage: str = "memory") -> app.Spec:
    return app.Spec(
        specification=component.Config(component.Spec(storage)),
        http=app.HttpConfig(app.HttpSpec(host="127.0.0.1", port=0)),
    )


class TestAddStoryEndToEnd:

    def test_a_post_to_a_jtbds_stories_answers_the_storys_id_level_and_position(self) -> None:
        specs_app = app.SpecsApp(app.AppConfig(app_spec()))
        http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
        stop = threading.Event()
        thread = threading.Thread(target=http_host.run, args=(stop,))
        thread.start()
        try:
            conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
            conn.request(
                "POST",
                "/jtbd/j-root/stories",
                body=json.dumps({
                    "given": "I am on the product specification page and a jtbd exists",
                    "when": "I click add story on it, fill in given, when and then, and click save",
                    "then": "I see the story nested under the jtbd",
                }),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            payload = json.loads(resp.read())
            conn.close()
            assert resp.status == 201
            assert payload == {"story_id": "j-root-s0", "level": 1, "position": 0}
        finally:
            stop.set()
            thread.join(5)
            specs_app.close()

    def test_a_second_post_to_the_same_jtbd_takes_the_next_position(self) -> None:
        specs_app = app.SpecsApp(app.AppConfig(app_spec()))
        http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
        stop = threading.Event()
        thread = threading.Thread(target=http_host.run, args=(stop,))
        thread.start()
        try:
            body = json.dumps({"given": "g", "when": "w", "then": "t"})
            conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
            conn.request("POST", "/jtbd/j-root/stories", body=body, headers={"Content-Type": "application/json"})
            conn.getresponse().read()
            conn.close()
            conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
            conn.request("POST", "/jtbd/j-root/stories", body=body, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            payload = json.loads(resp.read())
            conn.close()
            assert resp.status == 201
            assert payload == {"story_id": "j-root-s1", "level": 1, "position": 1}
        finally:
            stop.set()
            thread.join(5)
            specs_app.close()

    def test_a_post_missing_a_line_is_a_malformed_request(self) -> None:
        specs_app = app.SpecsApp(app.AppConfig(app_spec()))
        http_host = http.HttpHost(("127.0.0.1", 0), specs_app)
        stop = threading.Event()
        thread = threading.Thread(target=http_host.run, args=(stop,))
        thread.start()
        try:
            conn = client.HTTPConnection("127.0.0.1", http_host.port, timeout=5)
            conn.request(
                "POST", "/jtbd/j-root/stories", body=json.dumps({"given": "g"}), headers={"Content-Type": "application/json"}
            )
            resp = conn.getresponse()
            payload = json.loads(resp.read())
            conn.close()
            assert resp.status == 400
            assert payload["type"] == "/problems/malformed_request"
        finally:
            stop.set()
            thread.join(5)
            specs_app.close()
