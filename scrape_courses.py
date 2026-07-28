"""
McGill Course Catalogue Scraper
-------------------------------
Collects, for every McGill course:
    code, title, credits, description,
    prerequisites, corequisites, restrictions   (as RAW TEXT)

We deliberately store the requirement text verbatim rather than trying
to parse it. McGill's prerequisite prose is inconsistent enough that
naive parsing produces confidently wrong answers - store it now, parse
it later once you can see the real variety.

The catalogue is static HTML, so this is far more reliable than the
equivalency scraper. Still resumable: finished courses are skipped.

Run:  python scrape_courses.py
Out:  courses.csv
"""

import csv
import os
import re
import time
from playwright.sync_api import sync_playwright

INDEX_URL = "https://coursecatalogue.mcgill.ca/courses/"
BASE = "https://coursecatalogue.mcgill.ca/courses/"

OUT_FILE = "courses.csv"
DONE_FILE = "courses_done.txt"
LOG_FILE = "courses_log.txt"

DELAY = 0.4        # seconds between course pages - be polite
PAGE_WAIT = 400    # ms to let a page settle (static HTML)
RETRIES = 3
NET_WAIT = 30      # seconds between network-recovery checks
MAX_NET_WAIT = 60  # ~30 min of waiting before giving up on one page

# Labels the catalogue uses. Captured up to the next label or end.
FIELD_PATTERNS = {
    "prerequisites": r"Prerequisite\(?s?\)?\s*:\s*(.+?)(?=\n[A-Z][a-z]+(?:\(s\))?\s*:|\Z)",
    "corequisites":  r"Corequisite\(?s?\)?\s*:\s*(.+?)(?=\n[A-Z][a-z]+(?:\(s\))?\s*:|\Z)",
    "restrictions":  r"Restriction\(?s?\)?\s*:\s*(.+?)(?=\n[A-Z][a-z]+(?:\(s\))?\s*:|\Z)",
}


def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def load_done():
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE) as f:
        return {l.strip() for l in f if l.strip()}


def mark_done(slug):
    with open(DONE_FILE, "a") as f:
        f.write(slug + "\n")


def looks_like_network_error(err):
    s = str(err).upper()
    return any(sig in s for sig in (
        "ERR_NETWORK", "ERR_INTERNET", "ERR_NAME_NOT_RESOLVED",
        "ERR_CONNECTION", "ERR_TIMED_OUT", "NET::", "TIMEOUT"))


def wait_for_network(page):
    """Pause until the catalogue is reachable again."""
    log("  !! network down - pausing until it returns")
    for i in range(MAX_NET_WAIT):
        time.sleep(NET_WAIT)
        try:
            page.goto(INDEX_URL, timeout=20000)
            log(f"  .. back after ~{(i+1)*NET_WAIT}s")
            return True
        except Exception:
            log(f"  .. still down ({(i+1)*NET_WAIT}s)")
    return False


def get_course_slugs(page):
    """Pull every course slug (e.g. 'comp-251') off the index page."""
    log("Loading course index (large page, give it a moment)...")
    page.goto(INDEX_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(6000)
    html = page.content()
    log(f"  index is {len(html):,} characters")

    slugs = sorted(set(re.findall(r"/courses/([a-z0-9]{3,5}-\d[\w-]*)", html)))
    # strip any trailing path junk
    slugs = [s.rstrip("/") for s in slugs]
    log(f"  found {len(slugs)} course pages")
    return slugs


def parse_course(text, slug):
    """
    Extract fields from the page's plain text.

    The 2026-27 Course Catalogue lays a course page out as:

        ACCT 351. Intermediate Financial Accounting 1.
        Credits: 3
        Offered by: Management (Desautels Faculty Management)
        Terms offered: Summer 2026, Fall 2026, Winter 2027
        Description
        <prose>
        - Prerequisite: MGCR 211
        - Restrictions: Not open to U0 students.

    Note this differs from the retired eCalendar, which wrote the credit
    value inline as "(3 credits)". Matching the old shape silently
    returns nothing on every page.
    """
    row = {
        "slug": slug, "code": "", "title": "", "credits": "",
        "prerequisites": "", "corequisites": "", "restrictions": "",
        "description": "",
    }

    # "ACCT 351. Intermediate Financial Accounting 1."
    head = re.search(
        r"^[#\s]*([A-Z]{2,4}\s?\d{3}[A-Z0-9]*)\.\s*(.+?)\.\s*$",
        text, re.M)
    if head:
        row["code"] = head.group(1).replace(" ", "")
        row["title"] = head.group(2).strip()
    else:
        m = re.match(r"([a-z0-9]+)-(\d[\w]*)", slug)
        if m:
            row["code"] = (m.group(1) + m.group(2)).upper()

    # "Credits: 3"  (also tolerate the legacy "(3 credits)")
    m = re.search(r"Credits?\s*:\s*([\d.]+)", text, re.I)
    if not m:
        m = re.search(r"\((\d+(?:\.\d+)?)\s*credits?\)", text, re.I)
    if m:
        row["credits"] = m.group(1).rstrip(".")

    for field, pat in FIELD_PATTERNS.items():
        m = re.search(pat, text, re.S)
        if m:
            row[field] = re.sub(r"\s+", " ", m.group(1)).strip()[:600]

    # description sits under the "Description" heading
    d = re.search(r"Description\s*\n+(.+?)(?=\n\s*[-•]|\n\s*Most students|\Z)",
                  text, re.S)
    if d:
        row["description"] = re.sub(r"\s+", " ", d.group(1)).strip()[:800]

    return row


def scrape_one(page, slug):
    """Fetch and parse a single course page, with retries."""
    url = BASE + slug + "/"
    for attempt in range(RETRIES):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(PAGE_WAIT)
            text = page.locator("body").inner_text()
            return parse_course(text, slug)
        except Exception as e:
            if looks_like_network_error(e):
                wait_for_network(page)
                continue
            if attempt == RETRIES - 1:
                log(f"  {slug}: FAILED ({type(e).__name__})")
                return None
            time.sleep(3)
    return None



def wanted_codes():
    """
    Course codes that actually appear in your equivalency data.
    Scraping only these cuts ~10,000 pages down to ~2,000.
    Looks for clean.csv (or exchange_data.json). If neither exists,
    returns None meaning "scrape everything".
    """
    import json
    codes = set()
    if os.path.exists("clean.csv"):
        with open("clean.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                c = (r.get("mcgill_code") or "").strip().upper()
                if c:
                    codes.add(re.sub(r"[^A-Z0-9]", "", c))
    elif os.path.exists("exchange_data.json"):
        with open("exchange_data.json", encoding="utf-8") as f:
            for r in json.load(f):
                c = (r.get("mcgill_code") or "").strip().upper()
                if c:
                    codes.add(re.sub(r"[^A-Z0-9]", "", c))
    return codes or None


def slug_to_code(slug):
    """comp-251 -> COMP251"""
    m = re.match(r"([a-z0-9]+)-(\d[\w]*)", slug)
    return (m.group(1) + m.group(2)).upper() if m else slug.upper()


def main():
    done = load_done()
    new_file = not os.path.exists(OUT_FILE)
    fields = ["slug", "code", "title", "credits",
              "prerequisites", "corequisites", "restrictions", "description"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        slugs = get_course_slugs(page)

        want = wanted_codes()
        if want:
            before = len(slugs)
            slugs = [s for s in slugs if slug_to_code(s) in want]
            log(f"  filtered {before} -> {len(slugs)} "
                f"(only courses that have equivalencies)")
        else:
            log("  no clean.csv found - scraping ALL courses")

        todo = [s for s in slugs if s not in done]
        log(f"{len(todo)} to scrape, {len(done)} already done\n")

        with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if new_file:
                w.writeheader()

            for i, slug in enumerate(todo, 1):
                row = scrape_one(page, slug)
                if row:
                    w.writerow(row)
                    mark_done(slug)
                    pre = (row["prerequisites"][:45] + "...") \
                        if len(row["prerequisites"]) > 45 else row["prerequisites"]
                    log(f"[{i}/{len(todo)}] {row['code']:9} {pre or '(no prereq)'}")
                    if i % 25 == 0:
                        f.flush()
                time.sleep(DELAY)

        browser.close()

    log(f"\nDone -> {OUT_FILE}")


if __name__ == "__main__":
    main()
