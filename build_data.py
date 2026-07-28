"""
Builds planner_data.json  (v3)

Fixes applied in this version
----------------------------
* scrubs leaked DELETE* test records and placeholder host codes
* repairs rows where host code and host title were swapped
* flags compound ("X AND Y") equivalencies instead of silently
  breaking exact-match logic
* 500-level courses are JOINT undergrad/graduate at McGill and are NOT
  blocked; only 600+ is treated as graduate-only
* placeholder codes (ACCTXXX) get lvl:null, not 0, so degree-audit
  logic can tell "unknown level" from "level zero"
* prerequisite trees are normalised: always an object, never a bare
  string, so consumers never need a typeof check
* three-state status (A / N / E) rather than a boolean
* credits carried through when known, null when not
"""
import csv, json, re

CODE = re.compile(r"\b([A-Z]{2,4})\s?(\d{3}[A-Z0-9]{0,2})\b")
norm = lambda c: re.sub(r"[^A-Z0-9]", "", c.upper())
looks_code = lambda s: bool(re.match(r"^[A-Z]{2,6}\s?\d", s.strip().upper()))

STATUS = {"Equivalent": "A", "Not Equivalent": "N", "Expired": "E"}


def parse_prereq(text, self_code):
    if not text:
        return None
    t = re.sub(r"\bEither\b", "", text, flags=re.I)
    t = re.sub(r"\(([^)]*)\)", r" \1 ", t)
    t = re.sub(r"\s+", " ", t).strip()

    def leaf(s):
        codes = [a + b for a, b in CODE.findall(s)]
        codes = [c for c in codes if c != self_code]
        if not codes:
            return None
        return codes[0] if len(codes) == 1 else {"op": "or", "kids": codes}

    def split_or(s):
        kids = [k for k in (leaf(p) for p in re.split(r"\bor\b", s, flags=re.I)) if k]
        return None if not kids else (kids[0] if len(kids) == 1 else {"op": "or", "kids": kids})

    def split_and(s):
        kids = [k for k in (split_or(p) for p in re.split(r";|\band\b", s, flags=re.I)) if k]
        return None if not kids else (kids[0] if len(kids) == 1 else {"op": "and", "kids": kids})

    return split_and(t)


def normalise_tree(t):
    """Always return an object or None - never a bare string."""
    if t is None:
        return None
    if isinstance(t, str):
        return {"op": "and", "kids": [t]}
    return {"op": t["op"], "kids": [normalise_tree(k) if not isinstance(k, str) else k
                                    for k in t["kids"]]}


def course_flags(code):
    """
    Level from the McGill code. 'AFRI3XX' is a 300-level slot.
    'ACCTXXX' has no stated level -> None, not 0.
    """
    m = re.match(r"([A-Z]+)\s?(\d)(XX|\d{2})", code)
    if m:
        subj = m.group(1)
        lvl = int(m.group(2)) * 100 if m.group(3) == "XX" else int(m.group(2) + m.group(3))
    else:
        subj = (re.match(r"([A-Z]+)", code) or [None, ""])[1] if re.match(r"([A-Z]+)", code) else ""
        subj = re.match(r"([A-Z]+)", code).group(1) if re.match(r"([A-Z]+)", code) else ""
        lvl = None
    return {
        "subj": subj,
        "lvl": lvl,
        # 500-level at McGill is joint undergrad/grad and open to U3s.
        # Only 600+ is graduate-only and barred from transfer.
        "grad": lvl is not None and lvl >= 600,
        "joint": lvl is not None and 500 <= lvl < 600,
        "research": bool(re.search(r"(396|496|499|490)$", code)),
        "multiterm": bool(re.search(r"(D1|D2|N1|N2)$", code)),
    }


def main():
    # --- course catalogue: prereqs, credits, titles ---
    courses = {}
    for r in csv.DictReader(open("courses_clean.csv", encoding="utf-8")):
        code = norm(r["code"])
        courses[code] = {
            "tree": normalise_tree(parse_prereq(r["prereq_text"], code)),
            "cr": (r.get("credits") or "").strip() or None,
        }

    eq = json.load(open("clean.json", encoding="utf-8"))
    out, dropped, repaired = [], 0, 0

    for r in eq:
        hc, ht = r["host_code"].strip(), r["host_title"].strip()
        mc, mt = r["mcgill_code"].strip(), r["mcgill_title"].strip()

        # --- scrub leaked test records ---
        if "DELETE" in (hc + ht + mc + mt).upper():
            dropped += 1
            continue
        # --- placeholder host codes carry no information ---
        if hc.upper() in ("XXX", "X", "TBD", "N/A", "-"):
            hc = ""
        # --- repair swapped host code / title ---
        if hc and ht and not looks_code(hc) and looks_code(ht):
            hc, ht = ht, hc
            repaired += 1

        f = course_flags(mc)
        c = courses.get(norm(mc), {})
        credits = c.get("cr")

        out.append({
            "st": STATUS.get(r["status"], "N"),
            "mc": mc,
            "mt": mt,
            "hc": hc,
            "ht": ht,
            "in": r["institution"],
            "co": r["country"],
            "sub": f["subj"],
            "lvl": f["lvl"],
            "cr": int(float(credits)) if credits else None,
            "gr": 1 if f["grad"] else 0,
            "jt": 1 if f["joint"] else 0,
            "rs": 1 if f["research"] else 0,
            "mt2": 1 if f["multiterm"] else 0,
            "cmp": 1 if (" AND " in mc.upper() or " AND " in hc.upper()) else 0,
            "tree": c.get("tree"),
        })

    json.dump(out, open("planner_data.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    from collections import Counter
    st = Counter(o["st"] for o in out)
    print(f"rows {len(out)}   dropped {dropped} test records   repaired {repaired} swapped")
    print(f"status  approved {st['A']}  not-approved {st['N']}  expired {st['E']}")
    print(f"graduate-only (600+) blocked : {sum(1 for o in out if o['gr'])}")
    print(f"joint 500-level (allowed)    : {sum(1 for o in out if o['jt'])}")
    print(f"compound equivalencies       : {sum(1 for o in out if o['cmp'])}")
    print(f"with known credits           : {sum(1 for o in out if o['cr'])}")
    print(f"lvl unknown (generic XXX)    : {sum(1 for o in out if o['lvl'] is None)}")


if __name__ == "__main__":
    main()
