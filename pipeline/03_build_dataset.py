#!/usr/bin/env python3
"""
pipeline/03_build_dataset.py
Transforms extracted_v4.json → market-intelligence-dashboard/data.json

Steps:
  1. Load raw extraction + investment data from extracted_v4.json
  2. Filter entities against config/blacklist.json
  3. Apply curated editorial data from config/curated_companies.json
  4. Nuke fabricated metrics on non-curated companies
  5. Build extractive 'about' summaries for long-tail companies
  6. Write final data.json
"""
import json, re
from pathlib import Path

BASE       = Path(__file__).resolve().parents[1]
SOURCE     = BASE / "extracted_v4.json"
BLACKLIST  = BASE / "config" / "blacklist.json"
CURATED    = BASE / "config" / "curated_companies.json"
DATA_OUT   = BASE / "market-intelligence-dashboard" / "data.json"

METRIC_FIELDS = ("hq", "team_size", "founded", "ownership", "stage", "last_round")


# ─── Load config ──────────────────────────────────────────────────────────────

def load_blacklist() -> tuple[set[str], list[re.Pattern]]:
    with open(BLACKLIST, encoding="utf-8") as f:
        bl = json.load(f)
    exact    = {s.lower() for s in bl.get("exact", [])}
    patterns = [re.compile(p, re.IGNORECASE) for p in bl.get("patterns", [])]
    return exact, patterns


def load_curated() -> dict[str, dict]:
    with open(CURATED, encoding="utf-8") as f:
        return json.load(f)


# ─── Filtering ────────────────────────────────────────────────────────────────

def is_structural_noise(name: str) -> bool:
    s = name.strip()
    if len(s) < 2:
        return True
    if re.fullmatch(r"[\d\s\-\+\.\,\%\$\/\\\*]+", s):
        return True
    return False


def should_remove(name: str, exact_bl: set[str], patterns: list[re.Pattern]) -> bool:
    if is_structural_noise(name):
        return True
    low = name.strip().lower()
    if low in exact_bl:
        return True
    for pat in patterns:
        if pat.search(name.strip()):
            return True
    return False


# ─── Extractive about for long-tail companies ─────────────────────────────────

def extractive_about(entries: list[dict]) -> str:
    snippets, seen = [], set()
    for e in entries[:8]:
        text = (e.get("body") or e.get("summary") or "").strip()
        if not text:
            continue
        snippet = text[:200].strip()
        snippet = re.sub(r"https?://\S+", "", snippet).strip()
        snippet = re.sub(r"\*\*|\*|__|##", "", snippet).strip()
        snippet = re.sub(r"\s{2,}", " ", snippet)
        key = snippet[:60].lower()
        if key not in seen and len(snippet) > 40:
            seen.add(key)
            snippets.append(snippet)
        if len(snippets) >= 3:
            break
    if not snippets:
        return ""
    combined = " ".join(snippets)
    return combined[:497] + "…" if len(combined) > 500 else combined


# ─── Main ─────────────────────────────────────────────────────────────────────

def run() -> int:
    if not SOURCE.exists():
        print(f"[03_build_dataset] ⚠ {SOURCE} not found — run step 02 first.")
        return 0

    print(f"[03_build_dataset] Loading {SOURCE.name}…")
    with open(SOURCE, encoding="utf-8") as f:
        raw = json.load(f)

    exact_bl, patterns = load_blacklist()
    curated = load_curated()

    # extracted_v4.json is a flat list of companies; investment data lives in
    # data.json (written separately by extractor_v4.py).  We preserve the
    # existing investment array so it survives subsequent step-3-only runs.
    if isinstance(raw, list):
        raw_companies = raw
        # Preserve investment from current data.json if it exists
        raw_investment = []
        if DATA_OUT.exists():
            with open(DATA_OUT, encoding="utf-8") as f:
                existing = json.load(f)
            raw_investment = existing.get("investment", [])
    else:
        raw_companies  = raw.get("companies", [])
        raw_investment = raw.get("investment", [])

    kept     = []
    removed  = 0
    enriched = 0
    nulled   = 0

    for co in raw_companies:
        name = co.get("name", "")

        # 1. Filter
        if should_remove(name, exact_bl, patterns):
            removed += 1
            continue

        # 2. Apply curated data (overrides everything if available)
        if name in curated:
            patch = curated[name]
            for field in ("tagline", "about", "hq",
                          "team_size", "founded", "ownership",
                          "stage", "last_round"):
                co[field] = patch.get(field, "")
            enriched += 1
        else:
            # 3. Nuke fabricated metrics, build extractive about
            for field in METRIC_FIELDS:
                co[field] = ""
            if not co.get("about") or "es una empresa del sector" in co.get("about", ""):
                co["about"] = extractive_about(co.get("entries", []))
            if not co.get("tagline") or "Empresa destacada" in co.get("tagline", ""):
                co["tagline"] = ""
            nulled += 1

        kept.append(co)

    output = {"companies": kept, "investment": raw_investment}
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    mb = DATA_OUT.stat().st_size / 1_000_000
    print(f"[03_build_dataset] Filtered:  {removed} entities removed")
    print(f"[03_build_dataset] Curated:   {enriched} companies with real editorial data")
    print(f"[03_build_dataset] Remaining: {nulled} companies with extractive/empty data")
    print(f"[03_build_dataset] ✓ {len(kept)} companies → {DATA_OUT}  ({mb:.1f} MB)")
    return len(kept)


if __name__ == "__main__":
    run()
