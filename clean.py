"""
Turns raw.csv (from scrape.py) into clean.csv and clean.json.

Handles ZK's value-doubling and the two row shapes:
  - 18 cols: single host course. institution@15, country@16
  - wider:   host side has AND-linked courses; the host code/title
             cells hold "BIO1111 AND BIO1112", and institution/country
             sit in the LAST two non-empty cells.

Output columns:
  subject, status, mcgill_code, mcgill_title,
  host_code, host_title, institution, country
"""

import csv
import json
import re

IN_FILE = "raw.csv"
OUT_CSV = "clean.csv"
OUT_JSON = "clean.json"

VALID_STATUS = {"Equivalent", "Not Equivalent", "Expired"}


def tidy(s):
    """Collapse the AND-joins and whitespace into a clean string."""
    s = s.replace("\n", " ")
    s = re.sub(r"\s*AND\s*", " AND ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".")


def main():
    with open(IN_FILE, encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]

    seen = set()
    out = []
    skipped = 0

    for r in rows:
        if len(r) < 18 or r[1].strip() not in VALID_STATUS:
            skipped += 1
            continue

        status = r[1].strip()
        subject = r[0].strip()
        mcgill_code = tidy(r[3])
        mcgill_title = tidy(r[6])
        host_code = tidy(r[9])
        host_title = tidy(r[12])

        # institution + country are the last two non-empty cells,
        # which works for both 18-col and wider AND-rows
        nonempty = [c.strip() for c in r if c.strip()]
        country = ""
        institution = ""
        if len(nonempty) >= 2:
            # country is a short-ish geographic string; take last two
            institution = nonempty[-2]
            country = nonempty[-1]
            # guard: if "country" looks like a course artifact, blank it
            if "||" in country or len(country) > 40:
                country = ""

        if not mcgill_code or not institution or "||" in institution:
            skipped += 1
            continue

        key = (mcgill_code, host_code, institution, status)
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "subject": subject,
            "status": status,
            "mcgill_code": mcgill_code,
            "mcgill_title": mcgill_title,
            "host_code": host_code,
            "host_title": host_title,
            "institution": institution,
            "country": country,
        })

    out.sort(key=lambda x: (x["mcgill_code"], x["country"], x["institution"]))

    fields = ["subject", "status", "mcgill_code", "mcgill_title",
              "host_code", "host_title", "institution", "country"]

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    unis = {r["institution"] for r in out}
    countries = {r["country"] for r in out if r["country"]}
    approved = sum(1 for r in out if r["status"] == "Equivalent")
    rejected = sum(1 for r in out if r["status"] == "Not Equivalent")
    print(f"clean rows:   {len(out)}")
    print(f"  skipped:    {skipped}")
    print(f"  approved:   {approved}")
    print(f"  rejected:   {rejected}")
    print(f"universities: {len(unis)}")
    print(f"countries:    {len(countries)}")


if __name__ == "__main__":
    main()
