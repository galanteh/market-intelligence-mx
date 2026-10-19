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

# Aliases that should be merged into a single canonical entity.
# Applied before blacklist filtering and curated data lookup.
ALIAS_MAP: dict[str, str] = {
    "Walmart México":        "Walmart",
    "Walmart Mexico":        "Walmart",
    "Walmart de México":     "Walmart",
    "Walmart de Mexico":     "Walmart",
    "Walmex":                "Walmart",
    "BBVA México":           "BBVA",
    "BBVA Mexico":           "BBVA",
    "BBVA Bancomer":         "BBVA",
    "Bancomer":              "BBVA",
    "Citibanamex":           "Citibanamex",
    "Santander México":      "Santander",
    "Santander Mexico":      "Santander",
    "Heineken México":       "Heineken",
    "Heineken Mexico":       "Heineken",
    "Amazon México":         "Amazon",
    "Amazon Mexico":         "Amazon",
    "Aeroméxico":            "Aeroméxico",
    "Aeromexico":            "Aeroméxico",
    "Grupo Aeroméxico":      "Aeroméxico",
    "Grupo Aeromexico":      "Aeroméxico",
    "América Móvil":         "América Móvil",
    "America Movil":         "América Móvil",
    "Viva Aerobus":          "Viva Aerobus",
    "VivaAerobus":           "Viva Aerobus",
    "Vivaaerobus":           "Viva Aerobus",
    "Grupo México":          "Grupo México",
    "Grupo Mexico":          "Grupo México",
    "Mercado Libre":         "Mercado Libre",
    "MercadoLibre":          "Mercado Libre",
    "Grupo Salinas":         "Grupo Salinas",
    "Salinas":               "Grupo Salinas",
    # Warner aliases → canonical "Warner Bros"
    "Warner":                "Warner Bros",
    "Warner Bros Discovery": "Warner Bros",
    "WarnerMedia":           "Warner Bros",
    # CEMEX variants
    "Cemex":                 "CEMEX",
    "Cementos Mexicanos":    "CEMEX",
    # Pemex variants
    "Pemex":                 "PEMEX",
    "Petróleos Mexicanos":   "PEMEX",
    # DiDi / inDrive
    "Didi":                  "DiDi",
    "DIDI":                  "DiDi",
    # Cornershop
    "Cornershop by Uber":    "Cornershop",
    # Retail / pharmacy
    "H-E-B":                 "HEB",
    # Steel
    "Altos Hornos":          "AHMSA",
    "Altos Hornos de México":"AHMSA",
    # Media
    "HBO":                   "Warner Bros",
    # Banking
    "HSBC México":           "HSBC",
    # Press
    "El New York Times":     "The New York Times",
    # VC
    "DILA":                  "DILA Capital",
    # FEMSA variants
    "Femsa":                 "FEMSA",
    # Farmacias Guadalajara → parent entity
    "Farmacias Guadalajara": "Fragua",
    # Case / typo normalization
    "Ikea":                  "IKEA",
    "Hubspot":               "HubSpot",
    "Oppo":                  "OPPO",
    "DirectTV":              "DirecTV",
    "UNited Airlines":       "United Airlines",
    # Chili’s variants (canonical uses U+2019 right single quotation mark to match extractor)
    "Chili’s":               "Chili’s",
    "Chilis":                "Chili’s",
    "Chili’s Grill & Bar": "Chili’s",
    # Santos Laguna articles → Charly (the sportswear brand that sponsors the team)
    "Santos":                "Charly",
    # EssilorLuxottica → consumer brand name
    "EssilorLuxottica":      "Luxottica",
}


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

    # ── Entity resolution: merge aliases into canonical names ─────────────────
    # Build a lookup by name so we can append entries to the canonical company.
    by_name: dict[str, dict] = {}
    for co in raw_companies:
        original = co.get("name", "")
        canonical = ALIAS_MAP.get(original, original)
        co["name"] = canonical
        if canonical in by_name:
            # Merge entries into the existing record; keep first record's metadata
            by_name[canonical]["entries"] = (
                by_name[canonical].get("entries", []) + co.get("entries", [])
            )
        else:
            by_name[canonical] = co
    merged = list(by_name.values())
    alias_merges = len(raw_companies) - len(merged)
    if alias_merges:
        print(f"[03_build_dataset] Aliases:   {alias_merges} duplicates merged via ALIAS_MAP")

    kept     = []
    removed  = 0
    enriched = 0
    nulled   = 0

    for co in merged:
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
            # 3. Non-curated: clear all editorial fields — no extractive or
            #    generated text; only verified data from curated_companies.json
            #    is shown. Articles (entries) are preserved for the timeline.
            for field in METRIC_FIELDS:
                co[field] = ""
            co["about"]   = ""
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
