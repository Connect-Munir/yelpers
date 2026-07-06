"""
Yelp business scraper.

Collects business listings from a Yelp search and extracts:
    Business Niche, Company Name, Phone Number, Yelp URL, Website URL

Then writes the results to a CSV file.

Notes specific to Yelp:
  * "Website URL" is the external site Yelp links out to.
  * Most reliable data lives in the embedded JSON-LD (schema.org LocalBusiness)
    block, so we parse that instead of brittle CSS classes.
  * Yelp uses DataDome anti-bot protection that may show a "verify you are a
    human" CAPTCHA. Run non-headless (the default) and solve it once in the
    window when prompted — the cleared cookie is reused for the rest of the run.

Usage:
    python scraper.py                 # uses config.json
    python scraper.py --term "plumbers" --location "Austin, TX" --max 30
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import signal
import sys
import time
import types
from pathlib import Path
from urllib.parse import quote_plus, unquote, urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# --------------------------------------------------------------------------- #
# undetected-chromedriver compatibility shim for Python 3.12+
# --------------------------------------------------------------------------- #
def _install_distutils_shim() -> None:
    try:
        import distutils.version  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    _comp_re = re.compile(r"(\d+|[a-z]+|\.)")

    class LooseVersion:
        def __init__(self, vstring=None):
            self.vstring = ""
            self.version = []
            if vstring is not None:
                self.parse(str(vstring))

        def parse(self, vstring):
            self.vstring = vstring
            comps = [x for x in _comp_re.split(vstring) if x and x != "."]
            for i, obj in enumerate(comps):
                try:
                    comps[i] = int(obj)
                except ValueError:
                    pass
            self.version = comps

        @staticmethod
        def _coerce(other):
            return other if isinstance(other, LooseVersion) else LooseVersion(other)

        def __str__(self):
            return self.vstring

        def __repr__(self):
            return "LooseVersion ('%s')" % self.vstring

        def __eq__(self, other):
            return self.version == self._coerce(other).version

        def __lt__(self, other):
            return self.version < self._coerce(other).version

        def __le__(self, other):
            return self.version <= self._coerce(other).version

        def __gt__(self, other):
            return self.version > self._coerce(other).version

        def __ge__(self, other):
            return self.version >= self._coerce(other).version

    dist = sys.modules.get("distutils") or types.ModuleType("distutils")
    ver_mod = types.ModuleType("distutils.version")
    ver_mod.LooseVersion = LooseVersion
    dist.version = ver_mod
    sys.modules.setdefault("distutils", dist)
    sys.modules["distutils.version"] = ver_mod


_install_distutils_shim()

try:
    import undetected_chromedriver as uc
except Exception as _uc_exc:
    uc = None
    _UC_IMPORT_ERROR = _uc_exc
else:
    _UC_IMPORT_ERROR = None

BASE_URL = "https://www.yelp.com"
CONFIG_PATH = Path(__file__).with_name("config.json")
PROFILE_DIR = str(Path(__file__).with_name(".chrome-profile"))

PHONE_RE = re.compile(r"\(?\+?\d[\d\s().\-]{7,}\d")

CSV_FIELDS = [
    "Business Niche",
    "Company Name",
    "Location: USA",
    "Phone Number",
    "Yelp URL",
    "Website URL",
]

# Injected into every page before any page scripts run.
# Patches the properties DataDome / PerimeterX fingerprint.
_STEALTH_JS = """
(function() {
    // Hide webdriver flag
    try {
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    } catch(e) {}

    // Realistic browser properties
    try { Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8}); } catch(e) {}
    try { Object.defineProperty(navigator, 'deviceMemory', {get: () => 8}); } catch(e) {}
    try { Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']}); } catch(e) {}

    // Remove ChromeDriver CDP artifact variables
    const cdcKeys = Object.keys(window).filter(k => k.startsWith('cdc_'));
    cdcKeys.forEach(k => { try { delete window[k]; } catch(e) {} });

    // Ensure window.chrome looks real
    if (!window.chrome) window.chrome = {};
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            connect: function() {
                return {
                    onMessage: { addListener: function() {} },
                    postMessage: function() {},
                    disconnect: function() {}
                };
            },
            sendMessage: function() {},
            onMessage: { addListener: function() {} }
        };
    }

    // Patch permissions so queries don't throw
    if (navigator.permissions && navigator.permissions.query) {
        const _origQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(params) {
            if (params && params.name === 'notifications') {
                return Promise.resolve({
                    state: (typeof Notification !== 'undefined') ? Notification.permission : 'default',
                    onchange: null
                });
            }
            return _origQuery(params);
        };
    }

    // Patch plugins to look non-empty
    if (navigator.plugins && navigator.plugins.length === 0) {
        Object.defineProperty(navigator, 'plugins', {
            get: function() {
                return {0: {filename: 'internal-pdf-viewer'}, length: 1};
            }
        });
    }
})();
"""


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    defaults = {
        "search_term": "restaurants",
        "location": "San Francisco, CA",
        "max_results": 20,
        "max_all": False,
        "headless": False,
        "output_csv": "output.csv",
        "append": True,
        "page_load_timeout": 30,
        "delay_min": 4.0,
        "delay_max": 8.0,
        "page_settle_delay": 10.0,
    }
    if CONFIG_PATH.exists():
        try:
            defaults.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            sys.exit(f"config.json is not valid JSON: {exc}")

    parser = argparse.ArgumentParser(description="Scrape business details from Yelp.")
    parser.add_argument("--term", dest="search_term", help="What to search for.")
    parser.add_argument("--location", dest="location", help="Where to search.")
    parser.add_argument("--max", dest="max_results", type=int, help="Max businesses.")
    parser.add_argument("--max-all", dest="max_all", action="store_true", default=None,
                        help="Scrape every result Yelp returns (ignores --max).")
    parser.add_argument("--out", dest="output_csv", help="Output CSV path.")
    parser.add_argument("--headless", action="store_true", default=None,
                        help="Run without a window.")
    parser.add_argument("--no-append", dest="append", action="store_false",
                        default=None,
                        help="Overwrite the output CSV instead of merging.")
    args = parser.parse_args()

    for key, value in vars(args).items():
        if value is not None:
            defaults[key] = value
    return defaults


# --------------------------------------------------------------------------- #
# Browser
# --------------------------------------------------------------------------- #
def build_driver(headless: bool, page_load_timeout: int):
    """Build a Chrome driver with maximum stealth against Yelp's bot detection."""
    if uc is not None:
        try:
            # Keep options MINIMAL. undetected-chromedriver already patches the
            # automation fingerprint (navigator.webdriver, window.chrome, the
            # cdc_ artifacts, etc.). Piling on --disable-blink-features=
            # AutomationControlled, --no-sandbox, excludeSwitches or a manual
            # stealth-JS override fights those patches and creates the exact
            # inconsistencies DataDome fingerprints on. Less is more here.
            options = uc.ChromeOptions()
            options.page_load_strategy = "eager"
            options.add_argument("--window-size=1366,900")
            options.add_argument("--lang=en-US,en;q=0.9")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            # Disable extensions — security extensions (e.g. ESET) in the
            # saved profile can intercept requests and alter fingerprints.
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")

            driver = uc.Chrome(
                options=options,
                user_data_dir=PROFILE_DIR,
                headless=headless,
                use_subprocess=True,
            )
            driver.set_page_load_timeout(page_load_timeout)

            # NOTE: deliberately NOT injecting _STEALTH_JS here — UC handles the
            # fingerprint, and re-patching it makes detection more likely.

            print("[driver] Using undetected-chromedriver.")
            return driver
        except Exception as exc:
            print(
                f"[driver] undetected-chromedriver failed ({exc}); "
                "falling back to plain Selenium Chrome."
            )
    elif _UC_IMPORT_ERROR is not None:
        print(
            f"[driver] undetected-chromedriver unavailable ({_UC_IMPORT_ERROR}); "
            "using plain Selenium Chrome (more likely to be blocked)."
        )

    options = Options()
    options.page_load_strategy = "eager"
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(page_load_timeout)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": _STEALTH_JS},
    )
    return driver


def polite_sleep(cfg: dict) -> None:
    time.sleep(random.uniform(cfg["delay_min"], cfg["delay_max"]))


def human_scroll(driver) -> None:
    """Scroll the page over ~10 seconds simulating a human reading the listing.

    Keeps the natural down -> pause -> drift-up shape (which is what looks
    human to DataDome) but compressed: the bottom "reading" pause is kept
    intact and the scroll/drift steps are trimmed.
    """
    try:
        total_height = driver.execute_script("return document.body.scrollHeight") or 1200
        view_height = driver.execute_script("return window.innerHeight") or 600
        target = min(total_height - view_height, random.randint(700, 1100))

        # Phase 1 — scroll down in 4 steps with reading pauses (~3 s)
        for i in range(1, 5):
            driver.execute_script(f"window.scrollTo(0, {int(target * i / 4)});")
            time.sleep(random.uniform(0.6, 0.9))

        # Phase 2 — pause at the bottom as if reading (~4 s, kept intact)
        time.sleep(random.uniform(3.5, 4.5))

        # Phase 3 — natural drift: scroll back up slowly (~2 s)
        drift_back = random.randint(150, 300)
        for i in range(1, 3):
            driver.execute_script(
                f"window.scrollTo(0, {int(target - drift_back * i / 2)});"
            )
            time.sleep(random.uniform(0.8, 1.1))
    except WebDriverException:
        pass


def is_hard_blocked(driver) -> bool:
    """Detect DataDome's *unsolvable* block page ("You have been blocked").

    Unlike the CAPTCHA challenge, this page has no iframe to solve — DataDome
    has blacklisted the IP/network. Code can't get past it; the user must
    change networks (mobile hotspot / VPN / proxy) or wait it out. We match the
    page's distinctive copy, which never appears on a normal Yelp page."""
    try:
        body = (driver.find_element(By.TAG_NAME, "body").text or "").lower()
    except WebDriverException:
        return False
    signals = (
        "you have been blocked",
        "something about the behaviour of the browser",
        "there is a robot on the same network",
    )
    hits = sum(s in body for s in signals)
    # Require 1 strong signal AND that the page has no real Yelp content.
    if hits >= 1:
        try:
            has_content = bool(driver.find_elements(By.CSS_SELECTOR, 'a[href*="/biz/"]'))
        except WebDriverException:
            has_content = False
        return not has_content
    return False


def looks_blocked(driver) -> bool:
    """Detect Yelp's DataDome / PerimeterX bot wall via CAPTCHA iframe, not
    page text (DataDome script is embedded in every normal Yelp page too)."""
    try:
        for frame in driver.find_elements(By.TAG_NAME, "iframe"):
            src = (frame.get_attribute("src") or "").lower()
            if (
                "captcha-delivery.com" in src
                or "px-captcha" in src
                or "perimeterx" in src
                or "/interstitial/" in src
                or "geo.captcha" in src
            ):
                return True
    except WebDriverException:
        pass

    try:
        title = (driver.title or "").strip().lower()
    except WebDriverException:
        return False
    if title in ("", "yelp.com", "just a moment...", "access denied", "attention required"):
        try:
            has_content = bool(driver.find_elements(By.CSS_SELECTOR, "h1")) or bool(
                driver.find_elements(By.CSS_SELECTOR, 'a[href*="/biz/"]')
            )
        except WebDriverException:
            has_content = False
        if not has_content:
            return True
    return False


def clear_browsing_data(driver) -> None:
    """Wipe ALL browsing data for all time — the manual "clear browsing data"
    trick that often shakes off a DataDome block: browsing history, cookies and
    other site data, cached images/files, download history, autofill form data,
    site settings and hosted app data.

    Driven entirely through the Chrome DevTools Protocol so it needs no UI
    clicks and works in the existing window. Every call is best-effort — a
    single unsupported command must not abort the wipe."""
    # 1. Selenium's own cookie clear for the current domain (belt-and-braces).
    try:
        driver.delete_all_cookies()
    except WebDriverException:
        pass

    # 2. CDP cache + every-domain cookie wipe.
    for cmd, params in (
        ("Network.clearBrowserCache", {}),    # cached images and files
        ("Network.clearBrowserCookies", {}),  # cookies and other site data
    ):
        try:
            driver.execute_cdp_cmd(cmd, params)
        except WebDriverException:
            pass

    # 3. CDP per-origin wipe of every storage class. "all" covers cookies,
    #    local/session storage, IndexedDB, service workers, cache storage,
    #    websql, file systems and (where present) site settings — i.e. the rest
    #    of "site data", "hosted app data", "autofill" and "site settings".
    for origin in (BASE_URL, "https://geo.captcha-delivery.com"):
        try:
            driver.execute_cdp_cmd(
                "Storage.clearDataForOrigin",
                {"origin": origin, "storageTypes": "all"},
            )
        except WebDriverException:
            pass

    # 4. Browsing history + download history live in profile-wide CDP domains.
    for cmd in ("History.clearBrowsingHistory", "Browser.clearBrowsingData"):
        try:
            driver.execute_cdp_cmd(cmd, {})
        except WebDriverException:
            pass


def wait_until_unblocked(driver, cfg: dict, what: str, max_wait: int = 240) -> bool:
    """Wait for the user to solve a human-verification challenge in the visible
    Chrome window. Auto-detects when it clears by polling — no keypress needed.
    Once solved the DataDome clearance cookie persists in the Chrome profile for
    the rest of the run."""
    if not looks_blocked(driver):
        return True

    # Automatic recovery first: wipe all browsing data and refresh the same
    # page — the manual trick that often clears a DataDome block outright,
    # before we ever need a human to solve a CAPTCHA.
    blocked_url = driver.current_url
    print("[block] Detected a block — clearing ALL browsing data "
          "(history, cookies, cache, site data) and refreshing...")
    clear_browsing_data(driver)
    navigate(driver, blocked_url, cfg)
    time.sleep(random.uniform(2, 4))
    if not looks_blocked(driver):
        print("[block] Block cleared after wiping browsing data — continuing.")
        return True

    if cfg["headless"]:
        print(f"[block] Bot challenge on {what}; can't solve in headless mode.")
        print("        Re-run with \"headless\": false to solve it once.")
        return False

    print("\n" + "=" * 64)
    print("  Yelp is showing a 'verify you are human' challenge.")
    print(f"  Page: {what}")
    print("  -> Solve it in the Chrome window (press & hold / pick images).")
    print("     The scraper will detect it automatically and continue —")
    print("     you do NOT need to press anything here.")
    print(f"     Waiting up to {max_wait}s... (only needed once per run)")
    print("=" * 64)

    deadline = time.time() + max_wait
    last_reload = 0.0
    while time.time() < deadline:
        time.sleep(3)
        if not looks_blocked(driver):
            print("[block] Challenge cleared — continuing.")
            return True
        # Periodically wipe browsing data and reload so we evaluate the genuine
        # post-challenge page (the iframe sometimes clears but leaves the stale
        # DOM behind), and to keep retrying the clear-data trick.
        if time.time() - last_reload > 20:
            clear_browsing_data(driver)
            navigate(driver, driver.current_url, cfg)
            last_reload = time.time()
            time.sleep(2)
            if not looks_blocked(driver):
                print("[block] Challenge cleared — continuing.")
                return True
        remaining = int(deadline - time.time())
        print(f"[block] Waiting for you to solve the challenge... ({remaining}s left)")
    print("[block] Timed out waiting for the challenge to be solved.")
    return False


def navigate(driver, url: str, cfg: dict | None = None) -> None:
    """driver.get that handles eager-load timeouts gracefully.

    After a successful load it pauses for ``page_settle_delay`` seconds (plus a
    little jitter) so every page-to-page transition looks human to DataDome.
    Pass ``cfg`` to enable the pause; without it the navigation is immediate
    (used where the caller adds its own delay)."""
    timed_out = False
    try:
        driver.get(url)
    except TimeoutException:
        timed_out = True
        try:
            driver.execute_script("window.stop();")
        except WebDriverException:
            pass

    # Settle pause after the page transition. Skipped on a timeout, which has
    # already burned the full page_load_timeout waiting.
    if cfg and not timed_out:
        base = cfg.get("page_settle_delay", 10.0)
        if base > 0:
            time.sleep(random.uniform(base, base + 2.0))


def wait_for(driver, css: str, cfg: dict, what: str, timeout: int = 15) -> bool:
    """Wait for a CSS element; if blocked let the user solve the challenge first."""
    locator = (By.CSS_SELECTOR, css)
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
        return True
    except TimeoutException:
        pass

    if looks_blocked(driver) and wait_until_unblocked(driver, cfg, what):
        try:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False
    return False


# --------------------------------------------------------------------------- #
# Search results -> business URLs
# --------------------------------------------------------------------------- #
def collect_business_urls(driver, cfg: dict) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    start = 0
    unlimited = bool(cfg.get("max_all"))
    limit = float("inf") if unlimited else cfg["max_results"]

    while len(urls) < limit:
        search_url = (
            f"{BASE_URL}/search?find_desc={quote_plus(cfg['search_term'])}"
            f"&find_loc={quote_plus(cfg['location'])}&start={start}"
        )
        print(f"[search] {search_url}")
        navigate(driver, search_url, cfg)

        if not wait_for(driver, 'a[href*="/biz/"]', cfg, "search results"):
            if is_hard_blocked(driver):
                print("[search] DataDome HARD-BLOCKED the network mid-run — "
                      "switch network / VPN / proxy and re-run. Stopping.")
            elif looks_blocked(driver):
                print("[search] Bot challenge not cleared. Stopping.")
            else:
                print("[search] No business links found on this page. Stopping.")
            break

        human_scroll(driver)

        anchors = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/biz/"]')
        new_on_page = 0
        for a in anchors:
            href = a.get_attribute("href") or ""
            path = urlparse(href).path
            if not path.startswith("/biz/"):
                continue
            # Strip the slug down to /biz/<name> — drop any trailing /xyz parts
            # that are just internal Yelp tracking sub-paths.
            clean = urljoin(BASE_URL, path)
            if clean not in seen:
                seen.add(clean)
                urls.append(clean)
                new_on_page += 1
                if len(urls) >= limit:
                    break

        print(f"[search] +{new_on_page} new (total {len(urls)})")
        if new_on_page == 0:
            break
        start += 10
        polite_sleep(cfg)

    return urls if unlimited else urls[: cfg["max_results"]]


# --------------------------------------------------------------------------- #
# Business page -> details
# --------------------------------------------------------------------------- #
def extract_json_ld(driver) -> dict:
    """Return the first schema.org business object found in JSON-LD blocks."""
    scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
    for script in scripts:
        raw = script.get_attribute("textContent") or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for obj in _iter_objects(data):
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type", "")
            types_list = t if isinstance(t, list) else [t]
            if any(
                "Restaurant" in x or "Business" in x or "Store" in x
                or "Food" in x or "Service" in x
                for x in types_list
            ):
                return obj
            if "name" in obj and ("telephone" in obj or "address" in obj):
                return obj
    return {}


def _iter_objects(data):
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            yield from _iter_objects(data["@graph"])
        yield data
        for value in data.values():
            if isinstance(value, (dict, list)):
                yield from _iter_objects(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_objects(item)


def _plausible_phone(text: str) -> str:
    for match in PHONE_RE.finditer(text or ""):
        candidate = match.group(0).strip()
        if 7 <= sum(c.isdigit() for c in candidate) <= 15:
            return candidate
    return ""


def find_phone_fallback(driver) -> str:
    """Look for a phone number near the 'Phone number' label in the sidebar."""
    try:
        el = driver.find_element(
            By.XPATH,
            "//*[normalize-space(text())='Phone number']"
            "/following::*[string-length(normalize-space(text()))>0][1]",
        )
        phone = _plausible_phone(el.text)
        if phone:
            return phone
    except NoSuchElementException:
        pass
    # Last resort: regex scan on full page source
    return _plausible_phone(driver.page_source)


def find_website(driver) -> str:
    """Yelp links out to the business site via a /biz_redir?url=... anchor."""
    try:
        el = driver.find_element(
            By.XPATH,
            "//*[normalize-space(text())='Business website']"
            "/following::a[contains(@href,'biz_redir')][1]",
        )
        href = el.get_attribute("href") or ""
        m = re.search(r"[?&]url=([^&]+)", href)
        if m:
            return unquote(m.group(1))
        return el.text.strip()
    except NoSuchElementException:
        pass

    try:
        for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="biz_redir"]'):
            m = re.search(r"[?&]url=([^&]+)", a.get_attribute("href") or "")
            if m:
                return unquote(m.group(1))
    except WebDriverException:
        pass
    return ""


def format_address(data: dict) -> str:
    address = data.get("address") or {}
    if isinstance(address, list) and address:
        address = address[0]
    if not isinstance(address, dict):
        return ""
    parts = [
        address.get("streetAddress"),
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("postalCode"),
    ]
    return ", ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())


def scrape_business(driver, url: str, cfg: dict, niche: str) -> dict:
    row = {field: "" for field in CSV_FIELDS}
    row["Yelp URL"] = url
    row["Business Niche"] = niche

    navigate(driver, url, cfg)

    if not wait_for(driver, "h1", cfg, url):
        if looks_blocked(driver) and not wait_until_unblocked(driver, cfg, url):
            print(f"[biz] Bot challenge not cleared on {url} — skipping.")
            return row
        wait_for(driver, "h1", cfg, url)

    human_scroll(driver)

    data = extract_json_ld(driver)

    row["Company Name"] = (data.get("name") or "").strip()
    if not row["Company Name"]:
        try:
            row["Company Name"] = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
        except NoSuchElementException:
            pass

    row["Location: USA"] = format_address(data)

    phone = (data.get("telephone") or "").strip()
    row["Phone Number"] = phone or find_phone_fallback(driver)

    row["Website URL"] = find_website(driver)

    return row


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def load_existing(path: str) -> dict[str, dict]:
    out = Path(path)
    if not out.exists():
        return {}
    existing: dict[str, dict] = {}
    try:
        with out.open("r", newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                key = (row.get("Yelp URL") or "").strip()
                if key:
                    existing[key] = {f: row.get(f, "") for f in CSV_FIELDS}
    except (OSError, csv.Error) as exc:
        print(f"[csv] Could not read {out} ({exc}); it will be overwritten.")
    return existing


def write_csv(rows: list[dict], path: str, append: bool) -> None:
    out = Path(path)
    merged = load_existing(path) if append else {}
    before = len(merged)

    added, refreshed = 0, 0
    for row in rows:
        key = (row.get("Yelp URL") or "").strip()
        if not key:
            continue
        if key in merged:
            refreshed += 1
        else:
            added += 1
        merged[key] = row

    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(merged.values())

    if append and before:
        print(
            f"\nMerged into {out.resolve()}: {before} existing + {added} new "
            f"({refreshed} refreshed) = {len(merged)} total rows."
        )
    else:
        print(f"\nSaved {len(merged)} rows to {out.resolve()}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _raise_keyboard_interrupt(signum, frame):
    """Turn a signal into KeyboardInterrupt so the normal save-and-quit path runs."""
    raise KeyboardInterrupt


def _install_signal_handlers() -> None:
    """Allow a graceful, CSV-saving shutdown when asked to stop.

    The GUI's Stop button sends CTRL_BREAK_EVENT (SIGBREAK) on Windows; treating
    it like Ctrl+C lets main()'s ``except KeyboardInterrupt`` write out whatever
    rows were collected before stopping, instead of being hard-killed."""
    if hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, _raise_keyboard_interrupt)
        except (ValueError, OSError):
            pass


def main() -> None:
    _install_signal_handlers()
    cfg = load_config()
    niche = cfg["search_term"]
    limit_desc = (
        "all available" if cfg.get("max_all") else f"up to {cfg['max_results']}"
    )
    print(
        f"Searching Yelp for '{niche}' in '{cfg['location']}' "
        f"({limit_desc} businesses)\n"
    )

    driver = None
    rows: list[dict] = []
    try:
        driver = build_driver(cfg["headless"], cfg["page_load_timeout"])

        # Warm up: visit Google first so the session starts with natural history,
        # then open Yelp. If a CAPTCHA appears, the user solves it once and the
        # clearance cookie persists in the reused Chrome profile.
        print("[warmup] Opening google.com...")
        navigate(driver, "https://www.google.com/", cfg)
        time.sleep(random.uniform(2, 4))

        print("[warmup] Opening yelp.com...")
        navigate(driver, BASE_URL + "/", cfg)
        time.sleep(random.uniform(2, 4))

        if is_hard_blocked(driver):
            print("\n" + "=" * 64)
            print("  DataDome has HARD-BLOCKED this network (not a solvable CAPTCHA).")
            print("  The block page blames your IP — no browser tweak gets past it.")
            print("  Fix the network, then re-run:")
            print("    1. Switch networks: phone hotspot, a VPN, or a residential")
            print("       proxy. This is the single most effective fix.")
            print("    2. Or wait several hours — DataDome IP blocks expire.")
            print("    3. Then delete the .chrome-profile/ folder for a clean slate.")
            print("=" * 64)
            return

        if not wait_until_unblocked(driver, cfg, "yelp.com home"):
            print("Could not get past Yelp's bot challenge. Exiting.")
            return

        human_scroll(driver)
        time.sleep(random.uniform(1, 2))

        urls = collect_business_urls(driver, cfg)
        if not urls:
            print("No business URLs collected. Exiting.")
            return

        if cfg["append"]:
            already = load_existing(cfg["output_csv"])
            skipped = [u for u in urls if u in already]
            urls = [u for u in urls if u not in already]
            if skipped:
                print(f"\nSkipping {len(skipped)} URL(s) already in {cfg['output_csv']}.")
            if not urls:
                print("All collected URLs are already scraped. Nothing to do.")
                return

        print(f"\nCollected {len(urls)} business URLs. Visiting each...\n")
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url}")
            try:
                row = scrape_business(driver, url, cfg, niche)
                rows.append(row)
                print(
                    f"    -> {row['Company Name'] or '(no name)'} | "
                    f"{row['Phone Number'] or '-'} | "
                    f"web: {row['Website URL'] or '-'}"
                )
            except WebDriverException as exc:
                print(f"    !! error: {exc.__class__.__name__}: {exc}")
            polite_sleep(cfg)

    except KeyboardInterrupt:
        print("\nInterrupted — saving what we have so far.")
    finally:
        if rows:
            write_csv(rows, cfg["output_csv"], cfg["append"])
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
