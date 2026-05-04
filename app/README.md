# Templates de Producción — CellTrack v2.0

## ¿Qué es esta carpeta?

Templates Jinja2 listos para reemplazar los originales de `app/templates/` en tu VM de producción.
Son un **drop-in replacement**: mismas variables de contexto, mismos `url_for()`, mismas macros y bloques — solo el HTML/CSS cambió.

## Archivos incluidos

```
templates_prod/
├── base.html                  → app/templates/base.html
├── auth/
│   └── login.html             → app/templates/auth/login.html
├── dashboard/
│   └── index.html             → app/templates/dashboard/index.html
├── celulares/
│   ├── lista.html             → app/templates/celulares/lista.html
│   └── ver.html               → app/templates/celulares/ver.html
├── chips/
│   └── lista.html             → app/templates/chips/lista.html
└── responsables/
    └── ver.html               → app/templates/responsables/ver.html
```

> **Nota:** Los templates NO incluidos (forms, auditoria, reportes, catalogos, etc.) son compatibles con el nuevo `base.html` sin cambios — heredan automáticamente el nuevo diseño.

---

## Cómo aplicar los cambios en tu VM

### Opción A — Copiar manualmente

```bash
# Desde la raíz de tu repo en la VM:
cp templates_prod/base.html                app/templates/base.html
cp templates_prod/auth/login.html          app/templates/auth/login.html
cp templates_prod/dashboard/index.html     app/templates/dashboard/index.html
cp templates_prod/celulares/lista.html     app/templates/celulares/lista.html
cp templates_prod/celulares/ver.html       app/templates/celulares/ver.html
cp templates_prod/chips/lista.html         app/templates/chips/lista.html
cp templates_prod/responsables/ver.html    app/templates/responsables/ver.html
```

### Opción B — Via git

1. Descargá esta carpeta `templates_prod/` (botón Download en el Design System)
2. Copiá los archivos a `app/templates/` en tu repo local
3. Hacé commit y push:

```bash
git add app/templates/
git commit -m "feat: rediseño UI v2.0 - nuevo sistema de diseño"
git push origin main
```

4. En tu VM: `git pull origin main`
5. Reiniciá el container: `docker-compose restart app`

---

## Cambios en `base.html`

El nuevo `base.html` reemplaza el layout Bootstrap `container-fluid > .row` por un layout CSS `display:flex` que no requiere Bootstrap para la estructura del shell.

**Lo que cambió:**
- Navbar: de `<nav class="navbar navbar-dark">` a `<header class="ct-navbar">`
- Sidebar: de `<div class="col-md-2 sidebar">` a `<aside class="ct-sidebar">`
- Main: de `<div class="col-md-10 main-content">` a `<main class="ct-main">`
- Se agrega Google Fonts (Outfit) via CDN — requiere conexión a internet en el browser

**Lo que NO cambió:**
- Todos los `url_for()` son idénticos al original
- `{% block content %}`, `{% block extra_css %}`, `{% block extra_js %}` funcionan igual
- Bootstrap 5.3.0, jQuery 3.7.0, Select2 — mismas versiones y CDN
- Font Awesome 6.4.0 — misma versión

---

## Sin conexión a internet (red interna)

Si la VM no tiene acceso a Google Fonts, el sistema usa el font stack nativo (`-apple-system, BlinkMacSystemFont, sans-serif`) como fallback — se ve bien igualmente.

Para servir la fuente localmente, descargá Outfit desde:
https://fonts.google.com/specimen/Outfit

Y reemplazá en `base.html`:
```html
<!-- Reemplazar esto: -->
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">

<!-- Por esto: -->
<style>
@font-face {
    font-family: 'Outfit';
    src: url('/static/fonts/Outfit.woff2') format('woff2');
    font-weight: 100 900;
}
</style>
```

---

## Compatibilidad

| Template | Variables de contexto | Compatible con rutas existentes |
|---|---|---|
| `base.html` | `current_user`, `request` | ✅ Sin cambios |
| `auth/login.html` | flash messages | ✅ Sin cambios |
| `dashboard/index.html` | `cel_activos`, `chip_activos`, `cel_baja`, `resp_total`, `cel_libres`, `chip_libres`, `cel_asignados`, `chip_asignados`, `resp_sin_chip`, `top_sectores`, `ultimas` | ✅ Sin cambios |
| `celulares/lista.html` | `celulares`, `marcas`, `q`, `filtro`, `marca_f` | ✅ Sin cambios |
| `celulares/ver.html` | `cel`, `marca`, `modelo`, `historial`, `responsables_libres`, `motivos`, `asign_actual` | ✅ Sin cambios |
| `chips/lista.html` | `chips`, `prestadoras`, `tab`, `q`, `filtro`, `prestadora_f`, `total_telefonia`, `total_datos` | ✅ Sin cambios |
| `responsables/ver.html` | `resp`, `loc`, `sec`, `cel_activos`, `chip_activos`, `hist_cel`, `hist_chip` | ✅ Sin cambios |
