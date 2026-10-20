# 🇲🇽📊 Market Intelligence Dashboard

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)

Un panel interactivo de **Inteligencia de Mercado (Market Intelligence)** impulsado por Procesamiento de Lenguaje Natural (NLP). Este proyecto ingesta correos electrónicos de boletines de negocios, extrae entidades corporativas mediante IA, y genera un directorio estructurado con métricas de inversión, alertas y movimientos estratégicos.

---

## 🚀 Características Principales

*   **Ingesta Multi-Fuente:** Pipeline de datos ETL capaz de parsear archivos `.mbox` y clasificar automáticamente las noticias provenientes de distintos emisores (actualmente **Whitepaper** y **Expresso Matutino**).
*   **Extracción de Entidades (NLP):** Uso avanzado de `spaCy` para identificar empresas, limpiar nombres comerciales (resolución de *Alias* dinámicos), y descartar falsos positivos y contenido publicitario/patrocinado.
*   **Filtros de Inferencia Dinámica (Frontend):** Lógica JavaScript en tiempo real para deducir propiedades sin backend activo:
    *   🌍 *Geografía:* Separa entre "Solo México" e "Internacionales" evaluando la sede global y local de la empresa.
    *   📊 *Sentimiento de Mercado:* Clasifica el contexto en "🔥 Positivas" (inversiones, crecimiento, unicornios) o "⚠️ Alertas" (deuda, cierres, huelgas) analizando el texto en vivo.
*   **Catálogo Corporativo 100% Verificado:** Base de datos depurada con 159+ perfiles corporativos exactos de multinacionales y entidades mexicanas (incluyendo diferenciación de sedes filiales).
*   **Radar de Inversión y Capex:** Módulo dedicado a la detección automática de proyectos de expansión, rondas de levantamiento de capital y construcción de infraestructura.

---

## 📂 Estructura del Directorio

```text
.
├── config/
│   ├── blacklist.json          # Falsos positivos, nombres de autores y palabras ignoradas por el NLP.
│   └── curated_companies.json  # Catálogo maestro de perfiles corporativos (tags, sedes, tamaño).
├── pipeline/
│   ├── 01_parse_mbox.py        # Lector del archivo .mbox e identificador de fuente (W vs EM).
│   ├── 02_extract_entities.py  # Motor NER con spaCy y limpieza de strings.
│   ├── 03_build_dataset.py     # Resolución de Alias y ensamble del JSON final.
│   └── run_pipeline.py         # Orquestador principal que ejecuta los pasos secuencialmente.
├── market-intelligence-dashboard/
│   ├── index.html              # Interfaz principal / Dashboard UI.
│   ├── data.json               # Base de datos estática consumida por el frontend (salida del pipeline).
│   └── images/                 # Assets estáticos (Logo, íconos).
└── README.md                   # Documentación del proyecto.
```

---

## ⚙️ Cómo ejecutar el proyecto (Instalación y Uso)

### 1. Requisitos Previos
*   Python 3.8+
*   Navegador Web moderno
*   Archivo de entrada `.mbox` con los boletines suscritos guardado en la raíz del proyecto.

### 2. Configuración del Entorno Virtual (Recomendado)
```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias (spaCy, BeautifulSoup, etc.)
pip install -r requirements.txt

# Descargar el modelo de lenguaje en español para spaCy
python -m spacy download es_core_news_md
```

### 3. Ejecución del Pipeline (Procesamiento de Datos)
Para extraer los correos, correr la IA, aplicar la curaduría y generar el archivo `data.json`:
```bash
python pipeline/run_pipeline.py --force
```
*Esto tomará la información de las fuentes, limpiará el texto y actualizará la base de datos del frontend.*

### 4. Ejecución del Dashboard (Frontend)
Dado que el frontend no usa un servidor backend complejo, solo necesitas servir los archivos estáticos:
```bash
cd market-intelligence-dashboard
python3 -m http.server 8000
```
Abre tu navegador y entra a `http://localhost:8000`.

---

## ⚖️ Aviso Legal y de Uso (Disclaimer)

**Aviso de uso privado y demostración técnica:**
Este panel es un proyecto técnico independiente de carácter exclusivamente personal y sin fines de lucro. Los textos y contenidos analizados son propiedad de sus respectivos emisores (**Whitepaper** y **Expresso Matutino**) y se procesan únicamente a partir de suscripciones legítimas. No constituye redistribución, afiliación ni respaldo oficial por parte de los autores.

Con el fin de respetar y valorar el trabajo de curaduría periodística de Whitepaper (whitepaper.mx) y Expresso Matutino (espressomatutino.com), la información visible en este panel está deliberadamente incompleta, resumida o desactualizada, y nos reservamos el acceso a la base de datos íntegra. Esta versión se comparte públicamente de forma exclusiva como un caso de estudio técnico de Arquitectura de Datos e Ingeniería Frontend. Su objetivo es ilustrar cómo la Inteligencia Artificial puede transformar datos en inteligencia de mercado —por ejemplo, identificando empresas en planes de expansión para ofrecerles soluciones B2B— mejorando la toma de decisiones estratégicas.
