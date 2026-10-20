#!/usr/bin/env python3
"""
scripts/enrich_from_expansion.py
Enriches config/curated_companies.json with authoritative metrics from
expansion/empresas_expansion_500.json (Las 500 Empresas de Expansión).

New fields written to curated entries:
  expansion_rank  "#N"
  ceo             president/CEO name
  revenue_mdp     "$X,XXX.X MDP"

Existing fields updated only when currently blank:
  team_size       "XX,XXX empleados"
  hq              "{oficinas}, México"  (only when empty in curated)

Fields never overwritten: tagline, about, founded, ownership, stage, last_round, sector
"""
import json, re, unicodedata
from pathlib import Path

BASE      = Path(__file__).resolve().parents[1]
EXP_PATH  = BASE / "expansion" / "empresas_expansion_500.json"
CUR_PATH  = BASE / "config" / "curated_companies.json"

# ─── Explicit name mappings ───────────────────────────────────────────────────
# Maps Expansion nombre_empresa → curated catalog key.
# None = explicitly skip (subsidiary, wrong entity, or not in catalog).
MANUAL_MAP: dict[str, str | None] = {
    # ── TOP 100 ──────────────────────────────────────────────────────────────
    "Petróleos Mexicanos":                          "PEMEX",
    "Walmart de México y Centroamérica":            "Walmart",
    "América Móvil":                                "América Móvil",
    "FEMSA":                                        "FEMSA",
    "Comisión Federal de Electricidad":             "CFE",
    "General Motors de México":                     "General Motors",
    "BBVA México":                                  "BBVA",
    "Grupo Financiero Banorte":                     "Banorte",
    "Grupo Bimbo":                                  "Bimbo",
    "Grupo BAL":                                    None,
    "Grupo México":                                 "Grupo México",
    "FEMSA Comercio (Oxxo)":                        "OXXO",
    "Cemex":                                        "CEMEX",
    "Grupo Salinas":                                "Grupo Salinas",
    "Grupo Coppel":                                 "Coppel",
    "Grupo Comercial Chedraui":                     "Chedraui",
    "Coca-Cola FEMSA":                              "KOF",
    "Americas Mining Corporation":                  None,
    "Nissan Mexicana":                              None,
    "Arca Continental":                             "Arca Continental",
    "Infonavit":                                    None,
    "Banco Santander México":                       None,
    "Banamex":                                      "Citibanamex",
    "Liverpool":                                    "Liverpool",
    "Sam's Club":                                   None,
    "Grupo Elektra":                                "Elektra",
    "Volkswagen de México":                         None,
    "Grupo Modelo AB-InBev":                        "Grupo Modelo",
    "Grupo Carso":                                  "Grupo Carso",
    "Sigma Foods":                                  "Sigma Alimentos",
    "Organización Soriana":                         "Soriana",
    "Industrias Peñoles":                           None,
    "Orbia Advance Corporation":                    None,
    "Nestlé México":                                None,
    "Grupo Financiero Inbursa":                     "Inbursa",
    "Ternium":                                      "Ternium",
    "HEINEKEN México":                              "Heineken",
    "Jabil":                                        None,
    "Corporativo Fragua":                           "Fragua",
    "Flextronics Manufacturing Mex":                None,
    "GNP Seguros":                                  None,
    "Toyota Motor de México":                       None,
    "Grupo Financiero HSBC":                        "HSBC",
    "Alpek":                                        None,
    "PepsiCo Alimentos México":                     "PepsiCo",
    "Mercado Libre de México":                      "Mercado Libre",
    "Gruma":                                        "Gruma",
    "Cinépolis":                                    "Cinépolis",
    "KIA México":                                   None,
    "Banco Azteca":                                 "Banco Azteca",
    "Audi México":                                  "Audi",
    "Banobras":                                     None,
    "Grupo Bachoco":                                "Bachoco",
    "Grupo Lala":                                   "Grupo Lala",
    "Costco de México":                             "Costco",
    "Grupo Aeroméxico":                             "Aeroméxico",
    "Magna International México":                   None,
    "Nemak":                                        "Nemak",
    "Grupo Vazol (antes Grupo Empresarial Ángeles)": None,
    "Stellantis México":                            None,
    "BBVA Seguros México":                          None,
    "MetLife México":                               None,
    "Fresnillo PLC":                                None,
    "Grupo Financiero Scotiabank Inverlat":          "Scotiabank",
    "FEMSA División Salud":                         None,
    "Mabe":                                         "Mabe",
    "SuKarne":                                      None,
    "Alsea":                                        "Alsea",
    "AT&T México":                                  "AT &T",
    "Grupo Xignux":                                 "Xignux",
    "Robert Bosch México":                          None,
    "Tiendas Elektra":                              None,
    "Tiendas 3B":                                   "Tiendas 3B",
    "Supermercados Internacionales H-E-B":          "HEB",
    "Grupo Envases Universales":                    None,
    "DeAcero":                                      None,
    "Quálitas Controladora":                        None,
    "Softtek":                                      "Softtek",
    "Grupo Sanborns":                               "Grupo Sanborns",
    "Aeropuertos y Servicios Auxiliares":           None,
    "Casa Ley":                                     "Casa Ley",
    "Grupo Villacero":                              None,
    "Lear Corporation México":                      None,
    "Farmacias del Ahorro":                         "Farmacias del Ahorro",
    "AXA Seguros":                                  None,
    "FEMSA Combustibles":                           None,
    "Newmont Minera Peñasquito":                    None,
    "Grupo México División Transportes":            None,
    "Grupo Proeza":                                 None,
    "Grupo Palacio de Hierro":                      None,
    "P&G México":                                   None,
    "Sanmina-SCI de México":                        None,
    "Grupo Televisa":                               "Televisa",
    "Seguros Banorte":                              None,
    "Volaris":                                      "Volaris",
    "Valeo México":                                 None,
    "Mondelēz Snacking México":                     None,
    "Grupo Ángeles Servicios de Salud":             None,
    "Grupo Financiero Citi México":                 None,
    "Union Pacific de México":                      None,
    # ── RANKS 101-500 confirmed good matches ─────────────────────────────────
    "Kimberly-Clark de México":                     "Kimberly-Clark México",
    "Ford de México":                               "Ford",
    "ASUR (Grupo Aeroportuario de Sureste)":        "ASUR",
    "OMA (Grupo Aeroportuario del Centro Norte)":   "OMA",
    "Grupo Bolsa Mexicana de Valores":              "Bolsa Mexicana de Valores",
    "Jose Cuervo":                                  "Becle",
    "Hyundai Motor de México":                      "Hyundai",
    "Grupo Inditex México":                         "Inditex",
    "Seguros Banamex":                              None,
    "Grupo La Comer":                               "La Comer",
    "Unilever de México":                           "Unilever",
    "Megacable Holdings":                           "Megacable",
    "BorgWarner México":                            None,
    "Seguros Inbursa":                              None,
    "BanCoppel":                                    None,
    "Xignux Alimentos":                             None,
    "Casa de Bolsa Banorte":                        None,
    "Siemens México":                               "Siemens",
    "Grupo Pinsa":                                  "Pinsa",
    "Bank of America México":                       "Bank of America",
    "Pensiones Banorte":                            None,
    "Genomma Lab Internacional":                    "Genomma Lab",
    "Coeur Mining Mexicana":                        None,
    "Caja Popular Mexicana":                        None,
    "Betterware de México":                         "Betterware",
    "Grupo México Infraestructura":                 None,
    "Sandvik Mexicana":                             None,
    "Fábrica de Papel San Francisco":               None,
    "Afore XXI Banorte":                            None,
    "Mexicana de Industrias y Marcas":              None,
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def fmt_revenue(v: float | None) -> str:
    if v is None:
        return ""
    return f"${v:,.1f} MDP"


def fmt_employees(v: int | float | None) -> str:
    if v is None:
        return ""
    return f"{int(v):,} empleados"


def fmt_hq(oficinas: str, pais: str) -> str:
    if not oficinas:
        return ""
    if pais and pais.strip().lower() == "méxico":
        return f"{oficinas}, México"
    return oficinas


def resolve(nombre: str, curated_norm: dict[str, str]) -> str | None:
    """Return curated catalog key for an Expansion nombre_empresa, or None."""
    # 1. Explicit manual map
    if nombre in MANUAL_MAP:
        return MANUAL_MAP[nombre]
    # 2. Exact normalized match (fallback for 101-500 not in manual map)
    key = curated_norm.get(norm(nombre))
    return key


def run() -> None:
    with open(EXP_PATH, encoding="utf-8") as f:
        exp_list: list[dict] = json.load(f)
    with open(CUR_PATH, encoding="utf-8") as f:
        curated: dict[str, dict] = json.load(f)

    curated_norm = {norm(k): k for k in curated}

    matched: list[tuple[int, str, str]] = []
    skipped: list[tuple[int, str]] = []
    unmatched: list[tuple[int, str]] = []

    for entry in exp_list:
        rank    = entry["ranking"]
        nombre  = entry["nombre_empresa"]
        info_g  = entry.get("informacion_general", {})
        info_f  = entry.get("informacion_financiera", {})

        curated_key = resolve(nombre, curated_norm)

        if curated_key is None and nombre in MANUAL_MAP:
            skipped.append((rank, nombre))
            continue
        if curated_key is None:
            unmatched.append((rank, nombre))
            continue

        if curated_key not in curated:
            unmatched.append((rank, nombre))
            continue

        profile = curated[curated_key]

        # ── Always write new Expansion-sourced fields ─────────────────────
        profile["expansion_rank"] = f"#{rank}"

        ceo = (info_g.get("presidente_o_ceo") or "").strip()
        if ceo:
            profile["ceo"] = ceo

        ventas = info_f.get("ventas_mdp")
        if ventas is not None:
            profile["revenue_mdp"] = fmt_revenue(ventas)

        # ── Write only when currently blank ───────────────────────────────
        if not profile.get("team_size", "").strip():
            emp = info_f.get("empleados")
            if emp:
                profile["team_size"] = fmt_employees(emp)

        if not profile.get("hq", "").strip():
            profile["hq"] = fmt_hq(
                info_g.get("oficinas", ""),
                info_g.get("pais", ""),
            )

        matched.append((rank, nombre, curated_key))

    with open(CUR_PATH, "w", encoding="utf-8") as f:
        json.dump(curated, f, ensure_ascii=False, indent=2)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Expansión 500 → curated enrichment")
    print(f"{'='*60}")
    print(f"  ✓ Matched & enriched : {len(matched)}")
    print(f"  — Explicitly skipped : {len(skipped)}")
    print(f"  ? Unmatched          : {len(unmatched)}")
    print(f"{'='*60}")
    print(f"\n{'─'*60}")
    print("  MATCHED")
    print(f"{'─'*60}")
    for rank, nombre, key in matched:
        print(f"  #{rank:3d}  {nombre}  →  {key}")
    if unmatched:
        print(f"\n{'─'*60}")
        print("  UNMATCHED (no curated profile)")
        print(f"{'─'*60}")
        for rank, nombre in unmatched[:40]:
            print(f"  #{rank:3d}  {nombre}")
        if len(unmatched) > 40:
            print(f"  ... and {len(unmatched)-40} more")
    print(f"\n  ✓ Wrote {CUR_PATH.name}")


if __name__ == "__main__":
    run()
