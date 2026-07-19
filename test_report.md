# Reporte de Pruebas — 2026-07-19 (Consolidar guards solo-admin + borrar código muerto)

## Contexto
La misma condición "¿es admin?" estaba implementada por quintuplicado: `solo_admin()` en `finanzas.py`, `_solo_admin()` en `comercial.py`, 30 chequeos en línea en `admin.py`, 3 en `comercial.py`, y 2 con redacción distinta en Reportes. Se consolidó todo en una sola `solo_admin()` en `routes/admin.py` (junto a `requiere_personal()`), importada desde `finanzas.py` y `comercial.py`. Se borró además `_requiere_admin_o_operador()` (código muerto sin callers). Cero cambios de comportamiento: cada condición reemplazada es la misma expresión booleana, solo centralizada. Los chequeos a nivel de template (`{% if session.get('rol') == 'admin' %}` en `gestionar_viaje.html` y `dashboard.html`) y 8 sitios de lógica de negocio en `admin.py` (branches admin/operador en `dashboard`, `eliminar_viaje_admin`, `eliminar_camionero`, `pago_camionero`, dato `es_admin` en `transportista_economico`) quedaron fuera de alcance a propósito — no son guards de rechazo.

## Páginas probadas (local, `127.0.0.1:5001` — el 5000 sigue ocupado por el proceso ajeno que Aldo diagnostica aparte)
- GET: `/admin/`, `/admin/viajes`, `/admin/transportistas`, `/admin/comercial/rutas`, `/admin/clientes`, `/admin/incidencias`, `/admin/vehiculos`, `/admin/pagos-pendientes`, `/admin/viajes-sin-cobrar`, `/admin/configuracion`, `/admin/usuarios`, `/admin/reportes`, `/admin/auditoria`, `/admin/papelera`, `/admin/comercial/vehiculos`, `/admin/comercial/tarifas`.
- POST: `/admin/solicitudes-eliminacion/<id>/aprobar`, `/admin/solicitudes-eliminacion/<id>/rechazar`, `/admin/usuarios/crear`.

## Pruebas realizadas
1. `python -m py_compile` sobre `routes/admin.py`, `routes/comercial.py`, `routes/finanzas.py` — sin errores.
2. `grep -rn "_solo_admin\|_requiere_admin_o_operador" routes/` — cero resultados (código muerto y duplicados eliminados por completo).
3. Conteo de sitios reemplazados verificado contra el plan: `admin.py` 33 (`1 def + 32 not solo_admin()`), `comercial.py` 7, `finanzas.py` 8 — coincide exactamente con el inventario del plan.
4. **Como operador** (cuenta de prueba `_test_operador_consolidar`): las 7 pantallas `requiere_personal()` devolvieron `200` (igual que antes); las 9 pantallas `solo_admin()` devolvieron redirección (bloqueo) — incluyendo los 3 endpoints POST (`aprobar`, `rechazar`, `crear_usuario`) probados con token CSRF válido para aislar específicamente el guard de rol.
5. **Como admin**: las 16 pantallas devolvieron `200` — acceso total, sin cambios.

## Errores encontrados
Ninguno.

## Correcciones aplicadas
`routes/admin.py` (agregada `solo_admin()`, 32 chequeos en línea reemplazados), `routes/comercial.py` (borrada `_solo_admin()`, import actualizado, 7 call sites reemplazados), `routes/finanzas.py` (borradas `solo_admin()` local y `_requiere_admin_o_operador()`, import actualizado), `docs/01_CLAUDE_RULES.md` (dos menciones desactualizadas a `requiere_admin()` corregidas a `requiere_personal()`/`solo_admin()`).

## Datos de prueba y limpieza
- Cuenta `_test_operador_consolidar` (id 43, rol operador): creada y eliminada.
- Servidor Flask (puerto 5001) detenido (PIDs 23480 y 200756). `Get-Process python` solo muestra el proceso ajeno del puerto 5000 (PID 190952), sin tocar.

## Recomendaciones
- Unificar también los 3 chequeos de template (`gestionar_viaje.html`, `dashboard.html`) vía un booleano `es_admin` en el `context_processor` global existente — evaluado en el plan, descartado por bajo beneficio real (son expresiones de una línea, no funciones duplicadas). Queda como propuesta para una tarea aparte si se decide perseguir.
