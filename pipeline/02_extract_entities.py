#!/usr/bin/env python3
"""
pipeline/02_extract_entities.py
Reads brief_year_md/*.md, runs spaCy NER, and outputs extracted_v4.json.

Blacklist is loaded from data/blacklist.json so it can be updated without
touching the NLP code.

Skips extraction if extracted_v4.json is newer than all markdown files.
"""
import sys, os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
JSON_OUT = ROOT_DIR / "extracted_v4.json"
MD_DIR   = ROOT_DIR / "brief_year_md"


def is_fresh() -> bool:
    if not JSON_OUT.exists():
        return False
    md_files = list(MD_DIR.glob("Whitepaper_*.md"))
    if not md_files:
        return True
    out_mtime = JSON_OUT.stat().st_mtime
    return all(out_mtime >= f.stat().st_mtime for f in md_files)


def run(force: bool = False) -> int:
    if not force and is_fresh():
        import json
        with open(JSON_OUT, encoding="utf-8") as f:
            data = json.load(f)
        # extracted_v4.json is a flat list of company dicts
        companies = data if isinstance(data, list) else data.get("companies", [])
        n = sum(len(c.get("entries", [])) for c in companies)
        print(f"[02_extract_entities] {JSON_OUT.name} is up-to-date ({len(companies)} companies, {n} events) — skipping.")
        return n

    # Delegate to extractor_v4.py — the full 1099-line spaCy NLP engine.
    # It writes extracted_v4.json itself; we trigger it and report.
    extractor_path = Path(__file__).resolve().parent / "extractor_v4.py"
    if not extractor_path.exists():
        print(f"[02_extract_entities] ⚠ extractor_v4.py not found — skipping NLP step.")
        return 0

    import importlib.util, time
    spec = importlib.util.spec_from_file_location("extractor_v4", extractor_path)
    mod  = importlib.util.module_from_spec(spec)

    t0 = time.time()
    print("[02_extract_entities] Running NLP extraction (may take ~4 min)…")
    spec.loader.exec_module(mod)
    mod.main()
    elapsed = time.time() - t0

    import json
    if JSON_OUT.exists():
        with open(JSON_OUT, encoding="utf-8") as f:
            data = json.load(f)
        companies = data if isinstance(data, list) else data.get("companies", [])
        n = sum(len(c.get("entries", [])) for c in companies)
        print(f"[02_extract_entities] ✓ {n} events extracted in {elapsed:.0f}s")
        return n
    return 0


if __name__ == "__main__":
    force = "--force" in sys.argv
    run(force=force)
