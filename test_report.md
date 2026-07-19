# Reporte de Pruebas — 2026-07-19 (Rename requiere_admin → requiere_personal)

## Contexto
`requiere_admin()` no restringía a admin — dejaba pasar admin y operador. El nombre mentía sobre el comportamiento. Se investigó el mapa completo de guards del sistema y se confirmó que no había ningún hueco de permisos escondido: cada pantalla que usa `requiere_admin()` está legítimamente destinada a admin y operador, y las pantallas realmente admin-only (Pagos Pendientes, Configuración, Usuarios, Auditoría, Papelera) ya usan mecanismos separados (`solo_admin()`, `_solo_admin()`, chequeos en línea) no tocados por este cambio. Rename mecánico puro: `requiere_admin()` → `requiere_personal()`, mismo comportamiento.

## Páginas probadas (local, `127.0.0.1:5001` — el 5000 sigue ocupado por el proceso ajeno que Aldo diagnostica aparte)
- `/admin/`, `/admin/viajes`, `/admin/transportistas`, `/admin/comercial/rutas`, `/admin/clientes`, `/admin/incidencias`, `/admin/vehiculos`, `/admin/pagos-pendientes`, `/admin/configuracion`

## Investigación previa a la implementación
- Mapeados los 6 mecanismos de guard existentes en el código (ninguno es decorador; no hay Flask-Login). Confirmados 35 call sites de `requiere_admin()` en `routes/admin.py` + 19 en `routes/comercial.py` (importada), todos legítimamente admin+operador.
- Confirmado que `_requiere_admin_o_operador()` (`routes/finanzas.py:15`) es código muerto, nunca llamado — no se toca, solo se señala como hallazgo aparte por el nombre confundible.

## Pruebas realizadas
1. `python -m py_compile routes/admin.py routes/comercial.py` — sin errores.
2. `grep -rn "requiere_admin\b" routes/` tras el rename — cero coincidencias (rename completo, sin sitios olvidados).
3. **Como operador** (cuenta de prueba `_test_operador_rename`): las 9 rutas devolvieron el mismo patrón de antes del rename — `200` en Dashboard, Viajes, Transportistas, Rutas, Clientes, Incidencias, Vehículos; redirección (bloqueo) en Pagos Pendientes y Configuración.
4. **Como admin**: las 9 rutas devolvieron `200` — acceso total, sin cambios.

## Errores encontrados
Ninguno.

## Correcciones aplicadas
`routes/admin.py` (definición renombrada línea 142 + 35 call sites), `routes/comercial.py` (import actualizado línea 6 + 19 call sites). Ningún otro archivo referenciaba `requiere_admin`.

## Datos de prueba y limpieza
- Cuenta `_test_operador_rename` (id 42, rol operador): creada y eliminada.
- Servidor Flask (puerto 5001) detenido (PIDs 204320 y 197208). `Get-Process python` solo muestra el proceso ajeno del puerto 5000 (PID 190952), sin tocar.

## Recomendaciones
- `_requiere_admin_o_operador()` en `routes/finanzas.py` sigue siendo código muerto con un nombre confundible con `requiere_personal()`/`requiere_admin()`. Considerar eliminarlo en una tarea aparte.
