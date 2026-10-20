#!/usr/bin/env python3
"""
pipeline/run_pipeline.py — Whitepaper Market Intelligence Pipeline

Usage:
  python3 pipeline/run_pipeline.py           # smart mode: skip up-to-date steps
  python3 pipeline/run_pipeline.py --force   # re-run all steps from scratch
  python3 pipeline/run_pipeline.py --step 3  # run only step N (1, 2, or 3)

Steps:
  1  mbox → brief_year_md/*.md        (parse emails)
  2  markdown → extracted_v4.json     (NLP entity extraction, ~4 min)
  3  extracted_v4.json → web/data.json (filter + enrich + export)
"""
import sys, time, importlib.util
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent   # pipeline/
ROOT         = PIPELINE_DIR.parent               # project root


def load_step(n: int):
    names = {1: "01_parse_mbox", 2: "02_extract_entities", 3: "03_build_dataset"}
    path  = PIPELINE_DIR / f"{names[n]}.py"
    spec  = importlib.util.spec_from_file_location(f"step{n}", path)
    mod   = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args      = sys.argv[1:]
    force     = "--force" in args
    only_step = None

    if "--step" in args:
        idx = args.index("--step")
        if idx + 1 < len(args):
            only_step = int(args[idx + 1])

    print("=" * 56)
    print("  Whitepaper Market Intelligence Pipeline")
    print("=" * 56)
    t_total = time.time()

    results = {}

    for step_n in (1, 2, 3):
        if only_step is not None and only_step != step_n:
            continue
        mod = load_step(step_n)
        t   = time.time()
        if step_n in (1, 2):
            result = mod.run(force=force)
        else:
            result = mod.run()
        results[step_n] = result
        print(f"  Step {step_n} done in {time.time()-t:.1f}s\n")

    elapsed = time.time() - t_total
    print("=" * 56)
    print(f"  Pipeline completado en {elapsed:.1f}s")
    if results.get(1):
        print(f"  Emails procesados  : {results[1]}")
    if results.get(2):
        print(f"  Eventos extraídos  : {results[2]}")
    if results.get(3):
        print(f"  Empresas en dataset: {results[3]}")
    data_path = ROOT / "web" / "data.json"
    if data_path.exists():
        mb = data_path.stat().st_size / 1_000_000
        print(f"  data.json          : {mb:.1f} MB  ✓")
    print("=" * 56)


if __name__ == "__main__":
    main()
