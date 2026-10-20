# 🇲🇽📊 Market Intelligence Dashboard

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-NLP-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Thunderbird](https://img.shields.io/badge/Thunderbird-MBOX_Export-0A84FF?style=for-the-badge&logo=thunderbird&logoColor=white)

Plataforma integral de **Inteligencia de Mercado (Market Intelligence)** para el ecosistema empresarial mexicano y latinoamericano. El sistema ingesta newsletters de negocios mediante archivos `.mbox`, extrae menciones de empresas e inversiones usando Procesamiento de Lenguaje Natural (NLP), cruza los datos con el ranking institucional de **Las 500 Empresas de Expansión**, y genera un panel web interactivo de análisis sin dependencias externas de backend.

---

## 📂 Arquitectura del Proyecto

```text
.
├── web/                       # Dashboard cliente (interfaz estática autocontenida)
│   ├── index.html             # UI principal, grids analíticos y buscador
│   ├── data.json              # Dataset compilado por el pipeline
│   ├── images/                # Assets gráficos (logo institucional)
│   └── vendor/                # Dependencias locales (Tailwind bundle)
├── pipeline/                  # Pipeline ETL y enriquecimiento algorítmico
│   ├── 01_parse_mbox.py       # Parser de correo (segmenta Whitepaper vs Expresso Matutino)
│   ├── 02_extract_entities.py # Extractor NER con spaCy y sanitización de texto
│   ├── 03_build_dataset.py    # Unificación, resolución de alias y metadata de artículos
│   ├── enrich_from_expansion.py # Cruzador de métricas Expansión 500
│   └── run_pipeline.py        # Orquestador secuencial del pipeline
├── data/                      # Repositorio de datos maestros y configuraciones
│   ├── curated_companies.json # Perfiles maestros verificados (HQ, CEO, funding)
│   ├── blacklist.json         # Filtros y falsos positivos del extractor NER
│   └── expansion_500.json     # Dataset de Las 500 Empresas de Revista Expansión
├── docs/                      # Documentación interna y guías de referencia
│   ├── companies.md           # Notas y auditoría de entidades
│   └── estilo.md              # Lineamientos de diseño y UI
├── README.md
└── requirements.txt
```

---

## 🛠️ Guía de Uso Paso a Paso: De Cero a Producción

Sigue estos pasos para reproducir o desplegar el entorno completo en cualquier máquina:

### Paso 1: Ingesta y Extracción de Correos (`.mbox`)

El pipeline utiliza como entrada los correos crudos de las suscripciones a newsletters de negocios (e.g. Whitepaper.mx y Espresso Matutino):

1. **Configurar el cliente:** Configura tu cuenta de correo en [Mozilla Thunderbird](https://www.thunderbird.net/).

2. **Filtrar boletines:** Crea una carpeta dedicada en Thunderbird (ej. `Newsletters-Negocios`) y mueve allí todos los correos relevantes recibidos.

3. **Instalar Add-on:** Instala la extensión **ImportExportTools NG** desde el gestor de complementos de Thunderbird.

4. **Exportar a MBOX:**
   - Haz clic derecho sobre la carpeta `Newsletters-Negocios` en Thunderbird.
   - Selecciona `ImportExportTools NG > Exportar carpeta > Formato MBOX (un archivo)`.

5. **Ubicar el archivo:** Guarda el archivo exportado con el nombre `newsletters.mbox` directamente en la raíz del proyecto.

---

### Paso 2: Preparación del Entorno Python

Crea y activa un entorno virtual aislado para instalar las dependencias de extracción:

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En macOS/Linux:
source venv/bin/activate
# En Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Descargar modelo en español para spaCy
python -m spacy download es_core_news_md
```

---

### Paso 3: Enriquecimiento Institucional (Expansión 500)

Para incorporar ingresos, número de empleados, CEO y ranking de la revista Expansión a las empresas analizadas:

1. Asegúrate de contar con el archivo de scraping o catálogo en `data/expansion_500.json`.

2. Ejecuta el reconciliador de entidades:

```bash
python pipeline/enrich_from_expansion.py
```

Este script mapea nombres formales corporativos contra marcas comerciales y actualiza `data/curated_companies.json`.

---

### Paso 4: Ejecución del Pipeline ETL

Ejecuta el orquestador para procesar el `.mbox`, extraer entidades y generar el archivo de frontend `web/data.json`:

```bash
python pipeline/run_pipeline.py --force
```

El pipeline ejecutará automáticamente:

- **`01_parse_mbox.py`**: Lee `newsletters.mbox`, detecta si el remitente es Whitepaper o Expresso Matutino, limpia el HTML y normaliza fechas.
- **`02_extract_entities.py`**: Aplica el modelo NER de spaCy junto con `data/blacklist.json` para extraer nombres de empresas libres de falsos positivos y ruido editorial.
- **`03_build_dataset.py`**: Aplica el mapa de alias, enlaza los perfiles de `data/curated_companies.json` y compila el resultado final en `web/data.json`.

---

### Paso 5: Levantamiento del Dashboard

El frontend es estático y no requiere servidores pesados ni bases de datos activas:

```bash
cd web
python3 -m http.server 8000
```

Abre tu navegador en `http://localhost:8000`.

---

## 🧠 Lógica de Inferencia Dinámica (Frontend)

El dashboard resuelve clasificaciones clave directamente en el cliente mediante JavaScript sin llamadas a API:

- **Sedes (México vs. Internacional):** Analiza el valor del campo `hq`. Si incluye términos como EUA, España, Brasil, Reino Unido, etc., clasifica la entidad como internacional; de lo contrario, la identifica como sede nacional. Las filiales en México de multinacionales muestran el indicador `Sede Global (Filial MX)`.

- **Sentimiento en Tiempo Real:** Evalúa los resúmenes de las noticias para categorizar automáticamente:
  - 🔥 **Positivas:** Identifica palabras clave como `inversión`, `crece`, `récord`, `adquiere`, `expansión`, `ronda`.
  - ⚠️ **Alertas:** Detecta señales de riesgo como `caída`, `cierra`, `deuda`, `despide`, `quiebra`, `huelga`, `multa`.

- **Radar de Inversión & Capex:** Detecta proyectos de infraestructura, levantamientos de capital y capex analizando los montos monetarios (`mdd`, `mdp`, `millones`) y verbos de inversión.

---

## ⚖️ Aviso Legal, Atribución y Términos de Uso

**Aviso de uso privado y demostración técnica:**
Este panel es un proyecto técnico independiente de carácter exclusivamente personal y sin fines de lucro. Los textos y contenidos analizados son propiedad de sus respectivos emisores (**Whitepaper** y **Expresso Matutino**) y se procesan únicamente a partir de suscripciones legítimas. Los datos financieros y de ranking provienen de fuentes públicas e institucionales de Las 500 Empresas de Expansión (expansion.mx). Este software no constituye redistribución, afiliación, patrocinio ni respaldo oficial por parte de ninguno de los emisores o publicaciones mencionadas.

Con el fin de respetar y valorar el trabajo de curaduría periodística de Whitepaper (whitepaper.mx) y Expresso Matutino (espressomatutino.com), la información visible en este panel está deliberadamente incompleta, resumida o desactualizada, y nos reservamos el acceso a la base de datos íntegra. Esta versión se comparte públicamente de forma exclusiva como un caso de estudio técnico de Arquitectura de Datos e Ingeniería Frontend. Su objetivo es ilustrar cómo la Inteligencia Artificial puede transformar datos desestructurados en inteligencia de mercado mejorando la toma de decisiones estratégicas.
