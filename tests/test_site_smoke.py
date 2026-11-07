"""The one browser smoke test (Q26, #11): the site built from tests/fixtures/standin/loader_sample/, served on localhost, in headless Chromium.

Needs the dev requirements and Chromium:
  uv run --no-project --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt python -m playwright install chromium
Without Playwright the test is skipped, so the main suite still runs on requirements.txt alone.
Run from the repo root: python3 -m unittest discover tests
"""
import importlib.util
import re
import sys
import threading
import unittest
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_build import loaded
from test_site_data import CAREER_BAR, CREDIT, DATA_TO, FINISHING_LABEL, HOW_IT_WORKS, ON_SCREEN_LINE, SEASON_TWINS, SMALL_SAMPLE, STYLE_LABEL, TAKEDOWN, career_bar
from twin.application import build, site_data

HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None
SEASON_PERCENTILE_LABEL = "Percentile within ENG 2017/18, from 0 to 100"  # D30-14, for Salah's ENG 2017/18


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextmanager
def site_page(bar=None):
    """The site built from the sample (with the career bar at `bar` if given), served, in headless Chromium: (page, errors)."""
    from playwright.sync_api import sync_playwright

    with TemporaryDirectory() as folder:
        if bar is None:
            site = site_data.write_site(build.run(loaded(), Path(folder)), Path(folder) / "private" / "site")
        else:
            with career_bar(bar):
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
                yield page, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()


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

                    # Real: Mohamed Salah holds two Pool seasons in the sample and no career at 6,000 minutes:
                    # one search row (D30-13), which opens his latest season, with a link to each of his seasons.
                    page.fill("#search", "salah")
                    results = page.locator("#results button")
                    expect(results).to_have_count(1)
                    self.assertRegex(results.first.inner_text(), r"^Mohamed Salah · 2017/18-2023/24 · [\d,]+ min · \S")
                    results.first.click()
                    meta = page.locator("#player-meta")
                    expect(meta).to_contain_text("ENG 2023/24")
                    links = page.locator("#player-seasons button")
                    expect(links).to_have_count(2)
                    links.filter(has_text="2017/18").click()
                    expect(meta).to_contain_text("ENG 2017/18")

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
                    # D30-14: the season Fingerprint is in Build percentiles within its league-season.
                    fingerprint = page.locator("svg#fingerprint")
                    expect(fingerprint).to_have_count(1)
                    expect(fingerprint.locator("rect.bar")).to_have_count(10)
                    expect(page.locator("#player")).to_contain_text(SEASON_PERCENTILE_LABEL)
                    self.assertEqual(fingerprint.get_attribute("aria-label"), SEASON_PERCENTILE_LABEL)
                    values = fingerprint.locator("text.value").all_text_contents()
                    self.assertEqual(len(values), 10)
                    self.assertTrue(all(value.isdigit() and 0 <= int(value) <= 100 for value in values), values)
                    self.assertEqual(fingerprint.locator("text.scale").all_text_contents(), ["0", "50", "100"])
                    expect(page.locator("svg#display-stats")).to_have_count(1)

                    body = page.locator("body")
                    for text in (ON_SCREEN_LINE, STYLE_LABEL, DATA_TO, CREDIT, TAKEDOWN):
                        expect(body).to_contain_text(text)
                    self.assertEqual(page.locator("a", has_text="Understat").get_attribute("href"), "https://understat.com")

                    # Real: Darwin Núñez ENG 2023/24, 934 minutes. Search ignores accents.
                    # No career: 1 row, which opens his latest season.
                    page.fill("#search", "nunez")
                    expect(results).to_have_count(1)
                    results.first.click()
                    expect(page.locator("#player-meta")).to_contain_text("ENG 2023/24")
                    expect(page.locator("#player")).to_contain_text("Darwin Núñez")
                    expect(page.locator("#player")).to_contain_text(SMALL_SAMPLE)
                    # D30-8: under 6,000 career minutes, so the season view, headed "Season twins".
                    expect(page.locator("#player h3", has_text=SEASON_TWINS)).to_be_visible()
                    expect(page.locator("#career")).to_be_hidden()
                    for text in HOW_IT_WORKS:
                        expect(page.locator("#how-it-works")).to_contain_text(text)

                    # Two fast season clicks: the first season's file lands last, the screen still shows the second.
                    held = []
                    page.route("**/data/ENG_2017.json", lambda route: held.append(route))
                    page.reload()  # empties the page's file cache, so both seasons are fetched
                    page.fill("#search", "salah")
                    results.first.click()
                    expect(meta).to_contain_text("ENG 2023/24")
                    links.filter(has_text="2017/18").click()
                    links.filter(has_text="2023/24").click()
                    expect(meta).to_contain_text("ENG 2023/24")
                    held[0].continue_()
                    page.wait_for_function("files.has('ENG_2017.json')")  # the late file is read and its render step ran
                    expect(meta).to_contain_text("ENG 2023/24")
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
            self.assertEqual(errors, [])

    def test_career_view_with_role_filter_percentile_fingerprint_and_season_links(self):
        from playwright.sync_api import expect

        twin_line = re.compile(r"^(.+) · (Forward|Wide|Central AM) · \d{4}/\d{2}(-\d{4}/\d{2})? · [\d,]+ min · (closer than \d+(\.\d)?% of all careers)$")
        with site_page(CAREER_BAR) as (page, errors):
            # Real: Mohamed Salah, ENG 2017/18 and 2023/24, 3,611 Pool minutes: a career once the bar is at 900.
            # D30-13: one search row, in the career format, which opens the career view.
            page.fill("#search", "salah")
            results = page.locator("#results button")
            expect(results).to_have_count(1)
            self.assertRegex(results.first.inner_text(), r"^Mohamed Salah · Wide · 2017/18-2023/24 · 3,611 min · \S")
            results.first.click()
            career = page.locator("#career")
            expect(career).to_be_visible()
            expect(page.locator("#player")).to_be_hidden()
            expect(page.locator("#career-name")).to_have_text("Mohamed Salah")
            for text in ("Wide", "Seasons covered: 2017/18-2023/24", "3,611 min"):
                expect(page.locator("#career-meta")).to_contain_text(text)

            same_role = page.locator("#same-role")
            expect(same_role).to_be_checked()  # on by default (D30-5)
            twins = page.locator("#career-twins li")
            expect(twins).to_have_count(5)
            on = {}
            for text in twins.all_inner_texts():
                found = twin_line.match(text)
                self.assertTrue(found, text)
                self.assertEqual(found.group(2), "Wide")
                on[found.group(1)] = found.group(4)
            same_role.uncheck()
            expect(twins).to_have_count(5)
            page.click("#career-show-more")
            expect(twins).to_have_count(10)
            off = {twin_line.match(text).group(1): twin_line.match(text).group(4) for text in twins.all_inner_texts()}
            self.assertTrue(any(twin_line.match(text).group(2) != "Wide" for text in twins.all_inner_texts()))
            shared = set(on) & set(off)
            self.assertTrue(shared)
            for name in shared:
                self.assertEqual(on[name], off[name], name)  # D30-9: closeness holds when the filter toggles
            same_role.check()
            expect(twins).to_have_count(5)
            self.assertEqual({twin_line.match(text).group(1): twin_line.match(text).group(4) for text in twins.all_inner_texts()}, on)

            fingerprint = page.locator("svg#career-fingerprint")
            expect(fingerprint).to_have_count(1)
            self.assertIn("percentile", fingerprint.get_attribute("aria-label"))
            expect(fingerprint.locator("rect.bar")).to_have_count(10)
            values = fingerprint.locator("text.value").all_text_contents()
            self.assertEqual(len(values), 10)
            self.assertTrue(all(value.isdigit() and 0 <= int(value) <= 100 for value in values), values)
            self.assertEqual(fingerprint.locator("text.scale").all_text_contents(), ["0", "50", "100"])
            labels = fingerprint.locator("text.metric").all_text_contents()
            self.assertIn(FINISHING_LABEL, labels)
            self.assertFalse([label for label in labels if "_" in label])  # D30-12: plain English, no metric keys
            for text in HOW_IT_WORKS:
                expect(page.locator("#how-it-works")).to_contain_text(text)

            # Every season is a link under "Seasons covered" (D30-13); each opens its season view, which keeps "Same league only".
            expect(page.locator("#career h3", has_text="Seasons covered")).to_be_visible()
            links = page.locator("#career-seasons button")
            expect(links).to_have_count(2)
            for season in ("2017/18", "2023/24"):
                if not career.is_visible():
                    page.fill("#search", "salah")
                    results.first.click()
                    expect(career).to_be_visible()
                links.filter(has_text=season).click()
                expect(page.locator("#player")).to_be_visible()
                expect(career).to_be_hidden()
                expect(page.locator("#player-meta")).to_contain_text(f"ENG {season}")
                expect(page.locator("#player h3", has_text=SEASON_TWINS)).to_be_visible()
                expect(page.locator("#same-league")).to_be_visible()
                expect(page.locator("#twins li")).to_have_count(5)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
