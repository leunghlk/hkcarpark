#!/usr/bin/env python3
"""Build data/carparks.json — TD open-data carpark master + curated mall fee rules.

Sources:
  - https://resource.data.one.gov.hk/td/carpark/basic_info_all.json (TD, 560 parks, UTF-8 BOM!)
  - research/mall_free_parking.json (curated mall hourly + consumption-free rules)
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import date

TD_BASIC = "https://resource.data.one.gov.hk/td/carpark/basic_info_all.json"
HERE = os.path.dirname(os.path.abspath(__file__))
MALL = os.path.join(HERE, "research", "mall_free_parking.json")
OUT = os.path.join(HERE, "data", "carparks.json")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "hkcarpark-build/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def norm(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[^a-z0-9一-鿿]", "", s)


def slug(s: str) -> str:
    s = norm(s) or "x"
    return "cur-" + s[:40]


def main() -> None:
    raw = fetch(TD_BASIC).decode("utf-8-sig")  # TD file starts with a UTF-8 BOM
    parks = json.loads(raw)["car_park"]
    recs = []
    for p in parks:
        website = p.get("website_en") or p.get("website_tc") or None
        recs.append({
            "id": p["park_id"],
            "name_en": p.get("name_en") or "",
            "name_tc": p.get("name_tc") or "",
            "addr_en": p.get("displayAddress_en") or "",
            "addr_tc": p.get("displayAddress_tc") or "",
            "lat": p.get("latitude"),
            "lng": p.get("longitude"),
            "district_en": p.get("district_en") or "",
            "district_tc": p.get("district_tc") or "",
            "height": p.get("height") or None,
            "contact": p.get("contactNo") or None,
            "website": website,
            "opening_status": (p.get("opening_status") or "").lower() or None,
            "mall": False,          # heuristic / curated flag
            "hourly": None,         # curated text
            "consumptionFree": None,
            "freeRulesText": None,
            "mallNotes": None,
            "mallSource": None,
            "mallVerified": None,
            "mallAsOf": None,
            "source": "td",
        })
    print(f"TD parks: {len(recs)}")

    # mall heuristic on TD names
    mall_re = re.compile(r"shopping|plaza|mall|商場|廣場", re.I)
    for r in recs:
        if mall_re.search(r["name_en"] or "") or mall_re.search(r["name_tc"] or ""):
            r["mall"] = True

    # merge curated rules
    rules = []
    if os.path.exists(MALL):
        with open(MALL, encoding="utf-8") as f:
            rules = json.load(f)
        print(f"Curated entries: {len(rules)}")
    else:
        print(f"WARN: {MALL} not found — building TD-only master")

    # index TD recs by normalized names (en + tc)
    td_by_norm = {}
    for r in recs:
        for k in (norm(r["name_en"]), norm(r["name_tc"])):
            if k:
                td_by_norm.setdefault(k, []).append(r)

    matched_td_ids = set()
    unmatched = []
    for c in rules:
        keys = [norm(c.get(k, "")) for k in ("nameEn", "nameZh")]
        cands = []
        for k in keys:
            if not k:
                continue
            for nk, rs in td_by_norm.items():
                if k and nk and (k in nk or nk in k):
                    cands.extend(rs)
        cands = [r for r in cands if r["id"] not in matched_td_ids] or cands
        if cands:
            best = min(cands, key=lambda r: abs(len(norm(r["name_en"])) - len(keys[0])))
            matched_td_ids.add(best["id"])
            best["mall"] = True
            best["hourly"] = c.get("hourly")
            best["consumptionFree"] = c.get("consumptionFree")
            best["freeRulesText"] = c.get("freeRulesText")
            best["mallNotes"] = c.get("notes")
            best["mallSource"] = c.get("sourceUrl")
            best["mallVerified"] = c.get("verified")
            best["mallAsOf"] = c.get("asOf")
        else:
            # curated-only mall (no TD record → no live vacancy)
            recs.append({
                "id": slug(c.get("nameEn") or c.get("nameZh")),
                "name_en": c.get("nameEn") or "",
                "name_tc": c.get("nameZh") or "",
                "addr_en": "", "addr_tc": c.get("addressZh") or "",
                "lat": c.get("lat"), "lng": c.get("lng"),
                "district_en": "", "district_tc": c.get("district") or "",
                "height": None, "contact": None, "website": c.get("sourceUrl"),
                "opening_status": None,
                "mall": True,
                "hourly": c.get("hourly"),
                "consumptionFree": c.get("consumptionFree"),
                "freeRulesText": c.get("freeRulesText"),
                "mallNotes": c.get("notes"),
                "mallSource": c.get("sourceUrl"),
                "mallVerified": c.get("verified"),
                "mallAsOf": c.get("asOf"),
                "source": "curated",
            })
            unmatched.append(c.get("nameZh") or c.get("nameEn"))

    matched = len(matched_td_ids)
    print(f"Curated matched to TD: {matched}; curated-only appended: {len(unmatched)}")
    for u in unmatched:
        print(f"  curated-only: {u}")

    recs = [r for r in recs if r["lat"] and r["lng"]]
    recs.sort(key=lambda r: (r["district_tc"] or r["district_en"], r["name_tc"] or r["name_en"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": str(date.today()), "carparks": recs}, f,
                  ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(OUT)
    print(f"Wrote {OUT}: {len(recs)} carparks, {size/1024:.0f} KB")


if __name__ == "__main__":
    sys.exit(main())
