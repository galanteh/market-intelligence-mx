# Guía de estilo — Directorio de empresas (directorio.whitepaper.mx)

Extraído del sitio en vivo el 2026-10-19 (CSS compilado `assets/index-BGZ7qoY7.css`, DOM renderizado y estilos computados).

---

## 1. Stack y librerías

| Pieza | Detalle |
|---|---|
| Plataforma | **Base44** (app id `6a3bfda35d920db5e38e3f60`; API en `/api/apps/{id}/functions/*`, assets en `media.base44.com`) |
| Build | **Vite** (bundle único `assets/index-[hash].js` + `assets/index-[hash].css`, favicon `vite.svg`) |
| UI | **React** SPA con React Router (`/` y `/empresa/:id`) |
| CSS | **Tailwind CSS v3** (variables `--tw-*`, preflight v3) |
| Tokens / componentes | Convención **shadcn/ui** (variables HSL `--background`, `--foreground`, `--muted-foreground`, etc.; Toaster de shadcn montado) |
| Animaciones | **tailwindcss-animate** (keyframes `enter`, `exit`, `accordion-up/down`, más `pulse` y `spin` de Tailwind) |
| Íconos | **lucide-react** (`menu`, `search`, `users`, `dollar-sign`, `arrow-up-right`, `arrow-left`, `map-pin`, `calendar`, `building2`, `trending-up`, `coins`, `mail`) |
| Fuentes | **Google Fonts**: `Instrument Serif` (ital 0;1) + `Inter` (300, 400, 500, 600, 700), `display=swap` |

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

---

## 2. Tipografía

```css
--font-heading: "Instrument Serif", ui-serif, Georgia, serif;
--font-display: "Instrument Serif", ui-serif, Georgia, serif;
--font-body:    "Inter", ui-sans-serif, system-ui, sans-serif;
--font-mono:    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
```

- `body` usa `--font-body`, 16px / 24px, peso 400, `-webkit-font-smoothing: antialiased`.
- Todos los `h1–h6` usan `--font-heading` (Instrument Serif, peso 400 — nunca bold).
- Excepción: los subtítulos de la ficha (`Acerca de`, `Artículos Whitepaper`) son `h2` con `font-body font-bold text-lg` (Inter 700, 18px).

### Escala usada

| Elemento | Clases Tailwind | Valor resultante |
|---|---|---|
| H1 home | `font-heading text-5xl sm:text-6xl lg:text-7xl tracking-tight leading-[1.05]` | 48 → 60 → 72px, line-height 1.05, letter-spacing -0.025em (−1.8px a 72px) |
| H1 ficha (nombre empresa) | `font-heading text-5xl tracking-tight leading-tight` | 48px, lh 1.25 |
| Nombre en card | `font-heading text-3xl leading-tight truncate` | 30px, lh 1.25 |
| CTA "¿Quieres proponer…?" | `font-heading text-2xl sm:text-3xl tracking-tight` | 24 → 30px |
| "Sobre nuestra investigación" | `font-heading text-xl sm:text-2xl tracking-tight` | 20 → 24px |
| Subtítulo hero | `text-base sm:text-lg leading-relaxed text-muted-foreground` | 16 → 18px, lh 1.625 |
| Resumen en ficha | `text-lg text-muted-foreground leading-relaxed` | 18px |
| Cuerpo / descripciones | `text-sm leading-relaxed text-muted-foreground` | 14px, lh 1.625 |
| Badge de sector (card) | `text-[11px] font-medium uppercase tracking-wider` | 11px, 500, +0.05em |
| Badge de sector (ficha) | `text-xs font-medium uppercase tracking-wider` | 12px |
| Nav / footer / meta | `text-xs font-medium` | 12px |
| Sufijo "(est.)" | `text-[10px] font-normal text-muted-foreground ml-1` | 10px |

---

## 3. Color

### Tokens (`:root`, formato HSL sin `hsl()`, estilo shadcn)

```css
:root {
  --background: 0 0% 97%;          /* #F7F7F7 — fondo de página */
  --foreground: 0 0% 4%;           /* #0A0A0A — texto principal */
  --card: 0 0% 100%;               /* #FFFFFF */
  --card-foreground: 0 0% 4%;
  --popover: 0 0% 100%;
  --popover-foreground: 0 0% 4%;
  --primary: 0 0% 4%;              /* #0A0A0A */
  --primary-foreground: 0 0% 98%;
  --secondary: 0 0% 96%;
  --secondary-foreground: 0 0% 9%;
  --muted: 0 0% 96%;
  --muted-foreground: 0 0% 45%;    /* #737373 — texto secundario */
  --accent: 0 74% 61%;             /* ≈ #E84A4A (ver nota) */
  --accent-foreground: 0 0% 100%;
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 0 0% 98%;
  --border: 0 0% 91%;              /* #E8E8E8 */
  --input: 0 0% 91%;
  --ring: 0 74% 61%;
  --radius: .75rem;                /* 12px */
  --chart-1: 12 76% 61%;  --chart-2: 173 58% 39%;  --chart-3: 197 37% 24%;
  --chart-4: 43 74% 66%;  --chart-5: 27 87% 67%;
  --sidebar-background: 0 0% 98%; --sidebar-foreground: 240 5.3% 26.1%;
  --sidebar-primary: 240 5.9% 10%; --sidebar-primary-foreground: 0 0% 98%;
  --sidebar-accent: 240 4.8% 95.9%; --sidebar-accent-foreground: 240 5.9% 10%;
  --sidebar-border: 220 13% 91%;   --sidebar-ring: 217.2 91.2% 59.8%;
}
```

**Nota sobre el acento:** en el CSS compilado las utilidades `bg-accent` / `text-accent` NO usan la variable; están fijadas como `rgb(255 56 56)` = **`#FF3838`**. Ese rojo es el que se ve en pantalla (link "whitepaper.mx", punto pulsante, hover de títulos y flechas). La variable `--accent` (0 74% 61%) sólo aplica a `--ring`.

No hay tema oscuro (no existe `.dark` en el CSS).

### Paleta efectiva

| Uso | Color |
|---|---|
| Fondo página | `#F7F7F7` |
| Texto principal | `#0A0A0A` |
| Texto secundario | `#737373` |
| Acento / hover | `#FF3838` |
| Bordes por defecto (`*`) | `#E8E8E8` |
| Bordes sutiles | `rgba(0,0,0,.05)` (`border-black/5`) |
| Fondos sutiles (badges, chip contador) | `rgba(0,0,0,.05)` (`bg-black/5`) |
| Fondo input / caja CTA | `rgba(0,0,0,.03)` (`bg-black/[0.03]`) |
| Cards | blanco 85% + blur (ver `.glass-dark`) |

---

## 4. Efectos personalizados (CSS propio, fuera de Tailwind)

```css
.glass {            /* barra de navegación fija */
  background: #ffffffb3;                 /* blanco 70% */
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,.3);
}

.glass-dark {       /* cards del grid y tarjetas de datos de la ficha */
  background: #ffffffd9;                 /* blanco 85% */
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,.9);
  box-shadow: 0 1px 2px #0000000a, 0 8px 16px -4px #00000014, inset 0 1px #fff;
}
```

Base layer:

```css
* { border-color: hsl(var(--border)); outline-color: hsl(var(--ring) / .5); }
body {
  background-color: hsl(var(--background));
  font-family: var(--font-body);
  color: hsl(var(--foreground));
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
h1,h2,h3,h4,h5,h6 { font-family: var(--font-heading); }
```

---

## 5. Radios, sombras, movimiento

| Token | Valor |
|---|---|
| `rounded-lg` | `var(--radius)` = 12px |
| `rounded-md` | 10px |
| `rounded-xl` | 12px (logo en card, tarjetas de datos) |
| `rounded-2xl` | 16px (cards, input de búsqueda, logo en ficha) |
| `rounded-3xl` | 24px (caja CTA) |
| `rounded-full` | badges, chip contador, punto pulsante |
| Hover de card | `transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10` → sube 4px, sombra `0 20px 25px -5px / 0 8px 10px -6px` en negro 10% |
| Transiciones de color | `transition-colors` (150ms, `cubic-bezier(.4,0,.2,1)`) |
| Punto "en vivo" | `w-1.5 h-1.5 rounded-full bg-accent animate-pulse` (pulse 2s, opacidad 1 → .5) |

---

## 6. Layout y breakpoints

Breakpoints Tailwind por defecto: `sm` 640px, `md` 768px, `lg` 1024px.

- Contenedor general: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` (1280px máx).
- Hero y ficha: `max-w-3xl` (768px). Párrafo hero e input: `max-w-xl` (576px).
- Grid de empresas: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5`.
- Grid de datos en ficha: `grid grid-cols-2 sm:grid-cols-4 gap-4`.
- Nav fija de 64px (`h-16`), por eso el hero arranca con `pt-32` y la ficha con `pt-28`.
- Footer: `mt-24`, `py-12`, fila en `sm:` y columna en mobile.

---

## 7. Componentes (markup de referencia)

### Navbar
```html
<nav class="fixed top-0 left-0 right-0 z-50 glass">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-center h-16 relative">
      <a class="absolute left-4 sm:left-6 lg:left-8 hidden sm:block text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">whitepaper.mx →</a>
      <a class="flex items-center h-8 overflow-hidden"><img class="h-20 max-w-none mix-blend-multiply" alt="Whitepaper"></a>  <!-- wordmark "WHITEPAPER" (PNG) -->
      <button class="absolute right-4 sm:right-6 lg:right-8 hidden sm:block text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">Salir</button>
      <button class="absolute right-4 sm:hidden flex items-center justify-center w-10 h-10 -mr-2"><!-- lucide Menu w-5 h-5 --></button>
    </div>
  </div>
</nav>
```
El logo es un PNG con fondo blanco recortado con `overflow-hidden` + `mix-blend-multiply` para que se funda con el fondo.

### Hero
```html
<section class="pt-32 pb-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-3xl mx-auto text-center">
    <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/5 text-xs font-medium text-muted-foreground mb-6">
      <span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>50 empresas en el directorio
    </div>
    <h1 class="font-heading text-5xl sm:text-6xl lg:text-7xl tracking-tight leading-[1.05] mb-4">
      El directorio de empresas mexicanas<br><span class="text-muted-foreground">que tienes que conocer</span>
    </h1>
    <p class="text-base sm:text-lg text-muted-foreground max-w-xl mx-auto mb-10 leading-relaxed">
      Descubre las compañías más relevantes del ecosistema de negocios. Un producto editorial de
      <a class="text-accent hover:underline font-medium">whitepaper.mx</a>
    </p>
    <div class="relative max-w-xl mx-auto">
      <!-- lucide Search: absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground -->
      <input placeholder="Buscar empresa, categoría o ubicación..."
             class="w-full h-16 pl-14 pr-4 rounded-2xl bg-black/[0.03] border text-base placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 transition-all">
    </div>
  </div>
</section>
```
Nota: el markup original también trae `border-black/8`, `focus:ring-accent/20` y `focus:border-accent/30`, pero esas clases **no existen en el CSS compilado**, así que no tienen efecto (el borde visible es el `#E8E8E8` global).

### Card de empresa (grid)
```html
<a class="block group" href="/empresa/{id}">
  <div class="relative glass-dark rounded-2xl p-6 h-full transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/10">
    <div class="flex items-start gap-4 mb-4">
      <img class="w-12 h-12 rounded-xl object-cover bg-white border border-black/5">
      <div class="flex-1 min-w-0">
        <h3 class="font-heading text-3xl leading-tight group-hover:text-accent transition-colors truncate">Alsea</h3>
        <span class="inline-block mt-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground bg-black/5 px-2 py-0.5 rounded-full">Restaurantes</span>
      </div>
    </div>
    <p class="text-sm text-muted-foreground leading-relaxed line-clamp-2 mb-5">Resumen…</p>
    <div class="flex items-center justify-between pt-4 border-t border-black/5">
      <div class="flex items-center gap-4 text-xs text-muted-foreground">
        <span class="flex items-center gap-1"><!-- Users w-3 h-3 -->+75,300</span>
        <span class="flex items-center gap-1"><!-- DollarSign w-3 h-3 -->2025: $84,000 mdp</span>
      </div>
      <!-- ArrowUpRight w-4 h-4 text-muted-foreground group-hover:text-accent transition-colors -->
    </div>
  </div>
</a>
```
- Si no hay logo, se muestra la inicial (ej. "M" para Más Vuelos).
- El campo de ventas sólo aparece si existe; "(est.)" no se muestra en la card.

### Ficha de empresa (`/empresa/:id`, título de pestaña "Company Detail | Directorio de empresas")
```html
<div class="max-w-3xl mx-auto px-4 sm:px-6 pt-28 pb-12">
  <a class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"><!-- ArrowLeft w-4 h-4 -->Directorio</a>
  <div class="flex items-start gap-5 mb-8">
    <img class="w-20 h-20 rounded-2xl object-cover bg-white border border-black/5">
    <div>
      <div class="flex items-center gap-3 mb-1">
        <h1 class="font-heading text-5xl tracking-tight leading-tight">Bitso</h1>
      </div>
      <span class="inline-block text-xs font-medium uppercase tracking-wider text-muted-foreground bg-black/5 px-2.5 py-1 rounded-full">Fintech</span>
    </div>
  </div>
  <p class="text-lg text-muted-foreground leading-relaxed mb-10">Resumen…</p>

  <div class="mb-10">
    <h2 class="font-body font-bold text-lg mb-3">Acerca de</h2>
    <p class="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">…</p>
  </div>

  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
    <div class="glass-dark rounded-xl p-4">
      <!-- ícono w-4 h-4 text-muted-foreground mb-2 -->
      <p class="text-xs text-muted-foreground mb-0.5">Headquarters</p>
      <p class="font-medium text-sm">CDMX</p>
    </div>
    <!-- …Equipo (Users), Fundada (Calendar), Propiedad (Building2), Serie (TrendingUp),
         Última ronda (Coins), Ventas (DollarSign) + <span class="text-muted-foreground font-normal text-[10px] ml-1">(est.)</span> -->
  </div>

  <div>
    <h2 class="font-body font-bold text-lg mb-4">Artículos Whitepaper</h2>
    <div class="space-y-3">
      <a class="flex items-center gap-3 group" target="_blank">
        <img class="w-5 h-5 rounded flex-shrink-0">  <!-- ícono Whitepaper genérico -->
        <span class="text-sm text-muted-foreground">René Lankenau</span>
        <span class="text-sm text-foreground group-hover:text-accent underline transition-colors">Título del artículo</span>
      </a>
    </div>
  </div>
</div>
```

| Campo | Ícono lucide |
|---|---|
| Headquarters | `MapPin` |
| Equipo | `Users` |
| Fundada | `Calendar` |
| Propiedad | `Building2` |
| Serie | `TrendingUp` |
| Última ronda | `Coins` |
| Ventas | `DollarSign` |

### Caja CTA + metodología
```html
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
  <div class="rounded-3xl bg-black/[0.03] border border-black/5 px-6 py-10 sm:px-10 sm:py-12 text-center">
    <div class="flex items-center justify-center mb-3">
      <div class="w-10 h-10 rounded-full bg-foreground/5 flex items-center justify-center"><!-- Mail w-5 h-5 --></div>
    </div>
    <p class="font-heading text-2xl sm:text-3xl tracking-tight mb-2">¿Quieres proponer una empresa para nuestro directorio?</p>
    <p class="text-sm text-muted-foreground">Escríbenos a
      <a class="text-foreground font-medium underline underline-offset-4 hover:text-accent transition-colors">luis@whitepaper.mx</a></p>
  </div>
  <div class="mt-10 max-w-3xl mx-auto">
    <h3 class="font-heading text-xl sm:text-2xl tracking-tight mb-3 text-center">Sobre nuestra investigación</h3>
    <p class="text-sm text-muted-foreground leading-relaxed text-center">Para elaborar las fichas…</p>
  </div>
</div>
```

### Footer
```html
<footer class="mt-24">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <div class="flex flex-col sm:flex-row items-center justify-between gap-6">
      <div class="flex items-center h-6 overflow-hidden shrink-0"><img class="h-14 max-w-none mix-blend-multiply"></div>
      <p class="text-xs text-muted-foreground text-center">© 2026 Whitepaper.mx · Directorio de empresas · Todos los derechos reservados</p>
      <div class="flex items-center gap-4">
        <a class="text-xs text-muted-foreground hover:text-foreground transition-colors">Sitio principal</a>
        <a class="text-xs text-muted-foreground hover:text-foreground transition-colors">LinkedIn</a>
      </div>
    </div>
  </div>
</footer>
```

---

## 8. Config Tailwind sugerida para replicarlo

```js
// tailwind.config.js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["var(--font-heading)"],
        body: ["var(--font-body)"],
        display: ["var(--font-display)"],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        border: "hsl(var(--border))",
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "#FF3838", foreground: "#FFFFFF" }, // así está compilado en el sitio
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

---

## 9. Datos / API (referencia)

- Listado: `POST /api/apps/{appId}/functions/getDirectoryCompanies`
- Ficha: `POST /api/apps/{appId}/functions/getCompanyById`
- Acceso: `functions/verifyEmailAccess` (gate por email; token en `localStorage.wp_directory_token`)
- Tracking: `functions/trackEvent` y `analytics/track/batch`
- Logos e imágenes: `https://media.base44.com/images/public/{appId}/…` (Alsea usa una miniatura de Google Drive).
