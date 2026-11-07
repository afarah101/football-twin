"""The one browser smoke test (Q26, #11): the site built from tests/fixtures/standin/loader_sample/, served on localhost, in headless Chromium.

Needs the dev requirements and Chromium:
  uv run --no-project --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m playwright install chromium
Without Playwright the test is skipped, so the main suite still runs on requirements.txt alone.
Run from the repo root: python3 -m unittest discover tests
"""
import importlib.util
import sys
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_build import loaded
from test_site_data import CREDIT, DATA_TO, ON_SCREEN_LINE, SMALL_SAMPLE, STYLE_LABEL, TAKEDOWN
from twin.application import build, site_data

HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright is in requirements-dev.txt only")
class SiteSmoke(unittest.TestCase):
    def test_search_pick_a_season_and_see_twins_and_fingerprint(self):
        from playwright.sync_api import expect, sync_playwright

        with TemporaryDirectory() as folder:
            site = site_data.write_site(build.run(loaded(), Path(folder)), Path(folder) / "private" / "site")
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            errors = []
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    page = browser.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                    page.goto(f"http://127.0.0.1:{server.server_address[1]}/")

                    # Real: Mohamed Salah holds two Pool seasons in the sample, so search offers both.
                    page.fill("#search", "salah")
                    results = page.locator("#results button")
                    expect(results).to_have_count(2)
                    results.filter(has_text="2017/18").click()

                    twins = page.locator("#twins li")
                    expect(twins).to_have_count(5)
                    page.click("#show-more")
                    expect(twins).to_have_count(10)
                    for index in range(10):
                        text = twins.nth(index).inner_text()
                        self.assertRegex(text, r"(ENG|ESP|FRA|GER|ITA) \d{4}/\d{2}")
                        self.assertRegex(text, r"[\d,]+ min")
                        self.assertRegex(text, r"closer than \d+(\.\d)?% of all pairs")
                    # Same league only: the closeness is against same-league pairs, so the label says so.
                    page.check("#same-league")
                    expect(twins).to_have_count(5)
                    for index in range(5):
                        self.assertRegex(twins.nth(index).inner_text(), r"closer than \d+(\.\d)?% of same-league pairs")
                    page.uncheck("#same-league")
                    expect(twins.first).to_contain_text("of all pairs")
                    expect(page.locator("svg#fingerprint")).to_have_count(1)
                    expect(page.locator("svg#fingerprint rect.bar")).to_have_count(10)
                    expect(page.locator("svg#display-stats")).to_have_count(1)

                    body = page.locator("body")
                    for text in (ON_SCREEN_LINE, STYLE_LABEL, DATA_TO, CREDIT, TAKEDOWN):
                        expect(body).to_contain_text(text)
                    self.assertEqual(page.locator("a", has_text="Understat").get_attribute("href"), "https://understat.com")

                    # Real: Darwin Núñez ENG 2023/24, 934 minutes. Search ignores accents.
                    page.fill("#search", "nunez")
                    page.locator("#results button").first.click()
                    expect(page.locator("#player")).to_contain_text("Darwin Núñez")
                    expect(page.locator("#player")).to_contain_text(SMALL_SAMPLE)

                    # Two fast season clicks: the first season's file lands last, the screen still shows the second.
                    held = []
                    page.route("**/data/ENG_2017.json", lambda route: held.append(route))
                    page.reload()  # empties the page's file cache, so both seasons are fetched
                    page.fill("#search", "salah")
                    expect(results).to_have_count(2)
                    results.filter(has_text="2017/18").click()
                    results.filter(has_text="2023/24").click()
                    meta = page.locator("#player-meta")
                    expect(meta).to_contain_text("ENG 2023/24")
                    held[0].continue_()
                    page.wait_for_function("files.has('ENG_2017.json')")  # the late file is read and its render step ran
                    expect(meta).to_contain_text("ENG 2023/24")
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
