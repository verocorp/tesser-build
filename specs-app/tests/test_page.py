from __future__ import annotations

import re
import threading

import playwright.sync_api as playwright_sync_api

import tesser.testing as ts

import app as app
import specification.component as specification_component
import srv.http as srv_http


@ts.helper
def app_spec(storage: str = "memory") -> app.Spec:
    return app.Spec(
        specification=specification_component.Config(specification_component.Spec(storage)),
        http=app.HttpConfig(app.HttpSpec(host="127.0.0.1", port=0)),
    )


class TestAddStoryOnThePage:

    def test_s1_1_a_saved_story_is_nested_under_its_jtbd_with_its_identifier_level_and_links(self) -> None:
        specs_app = app.SpecsApp(app.AppConfig(app_spec()))
        http_host = srv_http.HttpHost(("127.0.0.1", 0), specs_app)
        stop = threading.Event()
        thread = threading.Thread(target=http_host.run, args=(stop,))
        thread.start()
        try:
            with playwright_sync_api.sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{http_host.port}/")

                jtbd = page.locator('[data-label="J1"]')
                jtbd.hover()
                jtbd.locator("button", has_text="story").click()

                form = page.locator('form[data-compose="j-root"]')
                form.locator('[name="given"]').fill("I am on the product specification page and a jtbd exists")
                form.locator('[name="when"]').fill("I click add story on it, fill in given, when and then, and click save")
                form.locator('[name="then"]').fill("I see it nested under J1, typed from the page test")
                form.get_by_role("button", name="Save").click()

                story = page.locator(".card.story", has_text="typed from the page test")
                playwright_sync_api.expect(story).to_be_visible()
                playwright_sync_api.expect(story.locator(".tag")).to_have_text(re.compile(r"^S1\.\d+$"))
                playwright_sync_api.expect(story.locator("xpath=ancestor::div[contains(@class, 'node')][1]")).to_have_class(re.compile(r"\bl1\b"))
                story.hover()
                playwright_sync_api.expect(story.get_by_title("Move earlier")).to_be_visible()
                playwright_sync_api.expect(story.get_by_title("Move later")).to_be_visible()
                playwright_sync_api.expect(story.get_by_role("button", name="Delete")).to_be_visible()
                browser.close()
        finally:
            stop.set()
            thread.join(5)
            specs_app.close()
