# Whitepaper Market Intelligence Dashboard

Dashboard de inteligencia corporativa personal, construido sobre el acervo histórico
de newsletters de [Whitepaper.mx](https://whitepaper.mx).

> **Proyecto personal no oficial.** Los datos, artículos y marcas pertenecen a
> Whitepaper.mx y sus respectivos autores.

---

## Estructura del repositorio

```
Whitepaper/
├── config/
│   ├── blacklist.json          # Entidades a excluir (orgs, productos, ruido NLP)
│   └── curated_companies.json  # Datos verificados para ~73 empresas top
├── pipeline/
│   ├── 01_parse_mbox.py        # mbox → brief_year_md/*.md
│   ├── 02_extract_entities.py  # Markdown → extracted_v4.json  (spaCy NLP)
│   └── 03_build_dataset.py     # extracted_v4.json → data.json (filter + enrich)
├── market-intelligence-dashboard/
│   ├── data.json               # Dataset de producción (generado, ~10 MB)
│   ├── index.html              # SPA (Tailwind + Vanilla JS)
│   └── images/
├── brief_year_md/              # Emails convertidos a Markdown por año
├── extractor_v4.py             # Extractor NLP core (invocado por step 02)
├── run_pipeline.py             # Orquestador principal
└── mbox/                       # .mbox original (gitignored)
```

---

## Correr el servidor local

```bash
cd market-intelligence-dashboard
python3 -m http.server 5052
# Abrir: http://localhost:5052
```

---

## Actualizar los datos

### Sólo regenerar `data.json` (sin re-correr NLP):
```bash
python3 run_pipeline.py --step 3
```

### Pipeline completo (si el .mbox cambió):
```bash
python3 run_pipeline.py
```

### Forzar re-extracción NLP (~4 min):
```bash
python3 run_pipeline.py --force
```

---

## Modificar la lista negra o datos curados

- **Agregar entidades a excluir**: editar `config/blacklist.json` → campo `"exact"` o `"patterns"`.
- **Actualizar datos de una empresa**: editar `config/curated_companies.json` y correr `python3 run_pipeline.py --step 3`.

---

## Requisitos

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install spacy
python3 -m spacy download es_core_news_sm
```
