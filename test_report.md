# Reporte de Pruebas — 2026-06-29

## Páginas probadas
- `http://127.0.0.1:5000/login` — Login como admin (user: admin / 1234)
- `http://127.0.0.1:5000/admin/` — Dashboard + sidebar completo expandido
- `http://127.0.0.1:5000/cliente/viaje/7` — Portal cliente viaje #7 (no existe en DB local)
- `http://127.0.0.1:5000/cliente/viaje/2` — Portal cliente viaje #2 (cliente_id = NULL, fix ítem 3)

## Errores encontrados
- `GET /favicon.ico → 404` — Pre-existente, no relacionado con cambios actuales.
- Sin errores de consola JavaScript.
- Sin errores HTTP 5xx.
- Viaje #7 no existe en DB local (solo existen viajes #1–#4); la app redirige correctamente a `/cliente/viajes`.

## Screenshots tomados
- `sidebar_completo.png` — Sidebar admin con los 4 grupos completamente expandidos
- `cliente_viaje7_redirect.png` — Redirección correcta a "Mis Viajes" al pedir viaje #7 inexistente
- `cliente_portal_viaje.png` — Portal cliente viaje #2 (cliente_id=NULL cargado por email, fix ítem 3 activo)

## Correcciones verificadas en esta sesión

| Verificación | Estado | Evidencia |
|---|---|---|
| Sidebar OPERACIONES (6 ítems) | ✅ | `sidebar_completo.png` |
| Sidebar FINANZAS (Reportes) | ✅ | `sidebar_completo.png` |
| Sidebar ADMINISTRACIÓN (Cotizaciones + Tarifas) | ✅ | `sidebar_completo.png` |
| Sidebar CONFIGURACIÓN colapsable (6 ítems) | ✅ | `sidebar_completo.png` |
| Headers sidebar en 13px | ✅ | Verificado en sesión anterior con `getComputedStyle` |
| Portal cliente redirige si viaje no existe | ✅ | `cliente_viaje7_redirect.png` |
| Portal cliente carga viaje con `cliente_id=NULL` | ✅ | `cliente_portal_viaje.png` |
| `.gitignore` excluye `.playwright-mcp/`, `*.png`, `*.log`, `test_report.md` | ✅ | `.gitignore` actualizado y commiteado |

## Recomendaciones
- Viaje #7 solo existe en producción. Para pruebas completas del portal cliente en local, crear viajes adicionales en la DB de desarrollo.
- El `.gitignore` ahora cubre todos los artefactos de Playwright: futuros commits no incluirán `.yml`, `.log`, `.png` ni `test_report.md`.
- El 404 de favicon puede resolverse con `@app.route('/favicon.ico')` → redirect a `/static/favicon.ico`.
