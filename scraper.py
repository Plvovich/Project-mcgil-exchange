"""
McGill Course Equivalency Scraper
---------------------------------
Loops over McGill subject codes, searches the equivalency database,
and saves every result row to results.csv.

Safe to stop and restart: it skips subjects already done.

Run:  python scraper.py
"""

import csv
import os
import time
from playwright.sync_api import sync_playwright

URL = "https://nimbus-ssl.mcgill.ca/exsa/search/searchEquivalency"
OUT_FILE = "results.csv"
DONE_FILE = "done.txt"
DELAY_SECONDS = 2          # pause between searches - be polite
WAIT_AFTER_SEARCH = 8000   # ms to wait for results to load

# Candidate places the results table might live.
# The script tries each and uses whichever finds the most rows.
ROW_SELECTORS = [".z-listitem", ".z-row", ".z-grid tr", ".z-listbox tr", "tr"]

# McGill subject codes. This is a starter list, NOT complete.
# Full list: mcgill.ca/study  ->  Course Catalogue  ->  browse by subject.
SUBJECTS = [
    "ANTH", "BIOL", "CHEM", "CLAS", "COMP", "ECON", "ENGL", "FREN",
    "GEOG", "HIST", "MATH", "MGCR", "PHIL", "PHYS", "POLI", "PSYC",
    "SOCI", "STAT",
]


def load_done():
    """Which subjects have we already scraped?"""
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def mark_done(subject):
    with open(DONE_FILE, "a") as f:
        f.write(subject + "\n")


def find_row_selector(page):
    """Try each candidate selector, return whichever finds the most rows."""
    best, best_count = None, 0
    for sel in ROW_SELECTORS:
        try:
            count = page.locator(sel).count()
        except Exception:
            continue
        print(f"    {sel:18} -> {count} rows")
        if count > best_count:
            best, best_count = sel, count
    return best, best_count


def clear_form(page):
    """Empty every text box we're allowed to edit."""
    boxes = page.get_by_role("textbox")
    for i in range(boxes.count()):
        b = boxes.nth(i)
        try:
            if b.is_visible() and b.is_enabled() and b.is_editable():
                b.fill("")
        except Exception:
            pass


def scrape_subject(page, subject, writer):
    """Search one subject code and write every row found."""
    print(f"\n[{subject}] searching...")

    page.goto(URL)
    page.wait_for_timeout(3000)

    clear_form(page)
    page.get_by_role("textbox").nth(0).fill(subject)
    page.get_by_role("button", name="Search").click()
    page.wait_for_timeout(WAIT_AFTER_SEARCH)

    selector, count = find_row_selector(page)
    if not selector or count == 0:
        print(f"[{subject}] no results found")
        return 0

    print(f"[{subject}] using '{selector}' ({count} rows)")

    written = 0
    page_num = 1

    while True:
        rows = page.locator(selector)
        for i in range(rows.count()):
            try:
                text = rows.nth(i).inner_text().strip()
            except Exception:
                continue
            if not text:
                continue
            # Save the raw text plus split-by-newline columns.
            # Clean this up later once we see the real shape.
            cells = [c.strip() for c in text.split("\n") if c.strip()]
            writer.writerow([subject, page_num, text] + cells)
            written += 1

        # try to advance to the next page of results
        try:
            next_btn = page.locator(".z-paging-next, .z-paging button").first
            if next_btn.count() == 0 or not next_btn.is_enabled():
                break
            next_btn.click()
            page.wait_for_timeout(WAIT_AFTER_SEARCH)
            page_num += 1
            print(f"    -> page {page_num}")
        except Exception:
            break

    print(f"[{subject}] wrote {written} rows")
    return written


def main():
    done = load_done()
    todo = [s for s in SUBJECTS if s not in done]

    if not todo:
        print("Everything already scraped. Delete done.txt to start over.")
        return

    print(f"{len(todo)} subjects to scrape, {len(done)} already done.")

    new_file = not os.path.exists(OUT_FILE)
    total = 0

    with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["subject", "page", "raw_text", "col1", "col2",
                             "col3", "col4", "col5", "col6"])

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            for subject in todo:
                try:
                    total += scrape_subject(page, subject, writer)
                    mark_done(subject)
                    f.flush()
                except Exception as e:
                    print(f"[{subject}] ERROR: {e}")
                time.sleep(DELAY_SECONDS)

            browser.close()

    print(f"\nDone. {total} rows written to {OUT_FILE}")


if __name__ == "__main__":
    main()
