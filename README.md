# Market Intelligence Dashboard 🇲🇽📊

Un panel interactivo de Inteligencia de Mercado (Market Intelligence) impulsado por Procesamiento de Lenguaje Natural (NLP). Este proyecto procesa boletines de noticias de negocios, extrae entidades corporativas y genera un directorio estructurado con métricas de inversión, alertas y movimientos estratégicos.

## 🚀 Características Principales

*   **Ingesta Multi-Fuente:** Pipeline de datos capaz de parsear archivos `.mbox` y clasificar automáticamente las noticias provenientes de distintos emisores, integrando actualmente **Whitepaper** y **Expresso Matutino**.
*   **Extracción de Entidades (NLP):** Uso de `spaCy` para identificar empresas, limpiar nombres comerciales (resolución de *Alias*) y descartar falsos positivos y contenido patrocinado.
*   **Filtros de Inferencia Dinámica:** El frontend utiliza lógica de JavaScript para deducir propiedades en tiempo real:
    *   *Geografía:* Clasifica empresas entre "Solo México" e "Internacionales" analizando las ubicaciones de sus sedes globales y locales.
    *   *Sentimiento de Mercado:* Clasifica el contexto de las noticias en "🔥 Positivas" (inversiones, crecimiento, rondas) o "⚠️ Alertas" (deuda, cierres, despidos).
*   **Catálogo Corporativo 100% Verificado:** Base de datos depurada manualmente con perfiles precisos de empresas multinacionales y mexicanas, indicando su estatus de filial corporativa cuando aplica.
*   **Radar de Inversión y Capex:** Pestaña dedicada a la detección y seguimiento de proyectos de expansión, rondas de capital y construcción de nuevas plantas.

## 🛠️ Arquitectura y Tecnologías

1.  **Pipeline de Datos (Backend / ETL):**
    *   Python 3
    *   `mailbox` (Parseo de correos electrónicos originales)
    *   `spaCy` (NLP, NER y limpieza de texto)
    *   `BeautifulSoup` (Limpieza de HTML)
2.  **Dashboard (Frontend):**
    *   Vanilla JavaScript (ES6+)
    *   HTML5 & Tailwind CSS
    *   Arquitectura "Serverless" (Consume un `data.json` estático generado por el pipeline)

## ⚖️ Aviso Legal y de Uso

**Aviso de uso privado y demostración técnica:**
Este panel es un proyecto técnico independiente de carácter exclusivamente personal y sin fines de lucro. Los textos y contenidos analizados son propiedad de sus respectivos emisores (Whitepaper y Expresso Matutino) y se procesan únicamente a partir de suscripciones legítimas. No constituye redistribución, afiliación ni respaldo oficial por parte de los autores.

Con el fin de respetar y valorar el trabajo de curaduría periodística de Whitepaper (whitepaper.mx) y Expresso Matutino (espressomatutino.com), la información visible en este panel está deliberadamente incompleta, resumida o desactualizada, y nos reservamos el acceso a la base de datos íntegra. Esta versión se comparte públicamente de forma exclusiva como un caso de estudio técnico. Su objetivo es ilustrar cómo la Inteligencia Artificial puede transformar datos en inteligencia de mercado —por ejemplo, identificando empresas en planes de expansión para ofrecerles soluciones B2B— mejorando la toma de decisiones estratégicas.

---
*Desarrollado como proyecto de Ingeniería de Datos y Arquitectura Frontend.*
