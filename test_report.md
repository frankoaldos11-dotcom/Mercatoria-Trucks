# Reporte de Pruebas — 2026-06-28

## Tipo de sesión
Corrección de 4 issues detectados en auditoría anterior + verificación Playwright.

---

## Cambios aplicados

### 1. Favicon (nuevo)
- Creado `static/favicon.ico` a partir de `static/icons/icon-192.png` (32×32, 48×48, 64×64 px) usando Pillow
- Añadido `<link rel="icon" href="/static/favicon.ico" type="image/x-icon">` en:
  - `templates/admin/base_admin.html`
  - `templates/base_cliente.html`

### 2. Meta PWA — `mobile-web-app-capable` añadida
- Añadida `<meta name="mobile-web-app-capable" content="yes">` en ambos templates base
- Se conserva `apple-mobile-web-app-capable` para compatibilidad con iOS Safari
- Eliminado el warning de consola de Chrome: *"apple-mobile-web-app-capable is deprecated"*

### 3. Helper `sql_mes_actual()` en `database.py`
- Nueva función que devuelve el fragmento SQL correcto según el motor:
  - PostgreSQL: `TO_CHAR(col, 'YYYY-MM') = TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM')`
  - SQLite: `strftime('%Y-%m', col) = strftime('%Y-%m', 'now')`
- Acepta el nombre de columna como parámetro (default: `fecha_creacion`)
- Exportada e importada en `routes/admin.py` — reemplaza el bloque `if USE_POSTGRES` manual

### 4. Sidebar links (ya estaban correctos)
- Los links en `base_admin.html` ya apuntaban a `/admin/comercial/cotizaciones` y `/admin/comercial/rutas`
- Las 404 detectadas en la auditoría anterior eran por navegación manual a URLs incorrectas, no por el sidebar

---

## Páginas probadas

| Ruta | Rol | Estado HTTP | Errores | Warnings |
|------|-----|-------------|---------|----------|
| `/` | — | 200 | 0 | 0 |
| `/login` | — | 200 | 0 | 0 |
| `/admin/` | admin | 200 | 0 | 0 |
| `/admin/reportes` | admin | 200 | 0 | 0 |
| `/admin/comercial/cotizaciones` | admin | 200 | 0 | 0 |
| `/admin/comercial/rutas` | admin | 200 | 0 | 0 |
| `/cliente/` | cliente | 200 | 0 | 0 |

---

## Errores y warnings en esta sesión
**Ninguno.** Todas las páginas cargaron con 0 errores y 0 warnings de consola.

---

## Screenshots tomados
- `fix_admin_dashboard.png` — Dashboard admin con `sql_mes_actual()` funcionando ($2350.00)
- `fix_cliente_home.png` — Portal cliente sin warning de meta deprecada

---

## Estado del proyecto tras esta sesión

| Issue | Estado |
|-------|--------|
| Favicon 404 | ✅ Resuelto |
| `apple-mobile-web-app-capable` deprecado | ✅ Resuelto (añadida versión estándar) |
| Helper SQL cross-DB | ✅ Implementado (`sql_mes_actual()` en `database.py`) |
| Links sidebar rotos | ✅ Confirmado que ya estaban correctos |
| Funciones PG sin guard | ✅ Sin ocurrencias nuevas |
| Errores HTTP 500 | ✅ Ninguno |

---

## Recomendaciones pendientes
- Extender `sql_mes_actual()` con variantes para filtros semanales/anuales si surgen nuevas queries
- Agregar test de smoke en CI que cargue `/admin/` y `/cliente/` y verifique status 200
