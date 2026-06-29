# Reporte de Pruebas — 2026-06-29

## Páginas probadas
- `http://127.0.0.1:5000/login` — Login como admin y como cliente
- `http://127.0.0.1:5000/admin/` — Dashboard (ítem 1: texto, ítem 2: sidebar headers, ítem 4: grupos)
- `http://127.0.0.1:5000/admin/viajes/4/gestionar` — Flujo de viaje (ítem 5: orden de bloques)
- `http://127.0.0.1:5000/cliente/viaje/2` — Portal cliente viaje sin cliente_id (ítem 3)
- `http://127.0.0.1:5000/admin/auditoria` — Historial de Cambios (ítem 1 + 4 sidebar activo)

## Errores encontrados
- `GET /favicon.ico → 404` — Pre-existente, no relacionado con Prompt E. El favicon se sirve desde `/static/favicon.ico`.
- Sin errores de consola JavaScript en ninguna de las páginas visitadas.
- Sin errores HTTP 5xx.

## Screenshots tomados
- `pe_01_dashboard.png` — Dashboard con texto "Historial de Cambios" en cuadro azul admin y sidebar con 4 grupos colapsados
- `pe_02_sidebar_groups.png` — Sidebar expandido: ADMINISTRACIÓN (Cotizaciones, Tarifas) + CONFIGURACIÓN (6 ítems)
- `pe_03_gestionar_viaje_top.png` — Viaje #4: Steps 1-7 → Acordeón detalles → Registro de cobro al cliente (orden correcto)
- `pe_04_cliente_viaje2.png` — Cliente accede correctamente a Viaje #2 que tenía `cliente_id = NULL`
- `pe_05_historial_cambios.png` — Página "Historial de Cambios" con enlace activo en sidebar (CONFIGURACIÓN)

## Correcciones aplicadas (Prompt E — commits 1736201 y bf97e22)

| # | Ítem | Estado | Verificación |
|---|------|--------|-------------|
| 1 | `dashboard.html`: "Auditoría" → "Historial de Cambios" en texto visible | ✅ | `pe_01_dashboard.png` y `pe_05_historial_cambios.png` |
| 2 | `admin.css`: nav-group-header font-size 11px → 13px | ✅ | `getComputedStyle` devuelve `"13px"` (requirió bump a `admin.css?v=5`) |
| 3 | `routes/cliente.py`: query `detalle_viaje` acepta viajes por `cliente_id` OR email del cliente | ✅ | `pe_04_cliente_viaje2.png` — Viaje #2 (`cliente_id=NULL`) carga correctamente |
| 4 | `base_admin.html`: ADMINISTRACIÓN queda con Cotizaciones+Tarifas; nuevo grupo CONFIGURACIÓN con 6 ítems | ✅ | `pe_02_sidebar_groups.png` |
| 5 | `gestionar_viaje.html`: acordeón de detalles aparece ANTES del bloque Registro de cobro | ✅ | `pe_03_gestionar_viaje_top.png` — Steps → Acordeón → Cobro |
| 6 | `gestionar_viaje.html`: botón CERRAR pide confirm con texto específico | ✅ | Verificado en template: `onsubmit="return confirm('¿Confirmas que esta operación está completada y pagada? Esta acción no se puede deshacer.')"` |

## Recomendaciones
- El bloque CERRAR OPERACIÓN (ítem 6) solo aparece cuando `done_all=True` (7 pasos completados); no fue verificable visualmente porque todos los viajes en DB están en estado "Asignado". Se confirmó directamente en el HTML del template.
- El 404 de favicon es cosmético; puede resolverse con una ruta `@app.route('/favicon.ico')` que redirija a `/static/favicon.ico`.
- Para pruebas futuras del bloque CERRAR OPERACIÓN conviene tener al menos un viaje de demostración con los 7 pasos completados.
