# Reporte de Pruebas — 2026-07-02

## Contexto
Commit probado en esta sesión: **validación de cobertura de rutas al asignar transportista** ("Validación: transportista debe cubrir todas las rutas del viaje al asignar"), pendiente de push al cierre de este reporte.

Sesiones anteriores del mismo día (ya en `main`):
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"
3. `039a6b8` — "docs: test_report actualizado post fix migracion viaje_tramos"
4. `6755022` — "feat: guardar fechas conjunto, validacion fecha descarga, boton viaje finalizado"

## Páginas probadas
- `/login` (admin)
- `/admin/viaje/<id>` — viaje multi-tramo de prueba (#9, La Habana→Holguín→Matanzas), paso "Asignar transportista y vehículo" y "Cambiar transportista"
- `/admin/viaje/<id>` — viaje single-ruta existente (#2, La Habana→Santiago)
- Endpoints probados directamente (sin UI, vía `test_client`): `POST /admin/viaje/<id>/asignar` (el endpoint sin formulario en la plantilla)

## Errores encontrados
- **Ninguno.** Sin errores de consola (0 errors, 0 warnings), sin errores HTTP inesperados, sin excepciones de servidor.

## Screenshots tomados
- `viaje9_inicial.png` — Viaje multi-tramo de prueba antes de asignar transportista
- `viaje9_rechazo.png` — Rechazo de asignación (transportista "testo", no cubre ninguna de las 2 rutas) con banner de error listando ambas rutas
- `viaje9_asignado_dalia.png` — Asignación exitosa de "dalia" (cubre ambas rutas del viaje)

(Los screenshots quedaron en la raíz del proyecto, ignorados por git vía `*.png` en `.gitignore`.)

## Correcciones aplicadas

**Nuevo helper `_rutas_no_cubiertas(cursor, camionero_id, viaje_id, ruta_id_directo)`** en `routes/admin.py`: reutiliza `obtener_tramos_viaje()` para viajes multi-tramo (valida cada tramo en orden) o el `ruta_id` directo para viajes de una sola ruta, y consulta `camionero_ruta` por cada una (mismo patrón que ya existía en la línea ~504 del archivo). Devuelve la lista de rutas no cubiertas.

**`asignar_camionero` (`POST /viaje/<id>/asignar`):** antes de ejecutar el `UPDATE`, valida cobertura. Si falta alguna ruta: no asigna, registra el intento fallido en Historial de Cambios (`_registrar_historial`) y redirige a `/admin/viaje/<id>?error=...` (mismo estilo que el guard `_viaje_cerrado()`) con un mensaje que nombra las rutas no cubiertas.

**`asignar_camionero_vehiculo` (`POST /viaje/<id>/asignar-todo`):** misma validación, ejecutada justo después de resolver el camionero y **antes** de buscar vehículo o tocar cualquier `UPDATE` — si el transportista no cubre todas las rutas, no se asigna ni camionero ni vehículo, y la reasignación (formulario "Cambiar transportista") tampoco puede saltarse la comprobación.

## Validaciones funcionales verificadas

| # | Escenario | Endpoint | Resultado esperado | Estado |
|---|---|---|---|---|
| 1 | Viaje multi-tramo (2 tramos), transportista que cubre ambas rutas | `/asignar-todo` (UI) | Asigna correctamente | ✅ |
| 2 | Viaje multi-tramo, transportista que no cubre ninguna ruta | `/asignar-todo` (UI) | Rechaza, mensaje lista ambas rutas: "El transportista no está habilitado para las rutas: La Habana–Holguin, Holguin–Matanzas" | ✅ |
| 3 | Reasignación (botón "Cambiar") sobre el mismo viaje multi-tramo, transportista sin cobertura | `/asignar-todo` (UI) | Rechaza — el transportista asignado (dalia) no cambia | ✅ |
| 4 | Intento fallido queda registrado en "Historial del viaje" | — | Entrada "Asignación de transportista rechazada" con el nombre del transportista y las rutas | ✅ |
| 5 | Viaje single-ruta, transportista que no cubre la ruta | `/asignar` (test_client) | Rechaza, `camionero_id` no cambia en BD | ✅ |
| 6 | Viaje single-ruta, transportista que sí cubre la ruta | `/asignar` (test_client) | Asigna correctamente, `camionero_id` actualizado | ✅ |
| 7 | Viaje multi-tramo vía el segundo endpoint (`/asignar`), transportista sin cobertura | `/asignar` (test_client) | Rechaza, asignación previa (dalia) se mantiene | ✅ |
| 8 | Viaje multi-tramo vía `/asignar`, transportista con cobertura completa | `/asignar` (test_client) | Asigna correctamente | ✅ |
| — | Sin errores de consola en ninguna prueba | — | — | ✅ |

## Recomendaciones
- Los datos de prueba (viaje #9, ruta temporal "TEST Holguin-Matanzas" y las filas de `camionero_ruta` creadas para la prueba) fueron eliminados de `mercatoria.db`. El viaje #2 fue devuelto a su transportista original ("testo") tras la prueba de regresión.
- Nota: en la BD actual, varios viajes ya asignados (p. ej. viaje #2 con "testo") tienen un transportista sin ninguna fila en `camionero_ruta` para su ruta — esto es preexistente (asignaciones hechas antes de esta validación) y no se corrige retroactivamente; la validación solo aplica hacia adelante, en el momento de asignar/reasignar.
- Si se desea, a futuro se podría extender la misma validación al selector de camioneros que se muestra en el dropdown de "Asignar transportista" (hoy solo filtra por tener vehículo activo, no por cobertura de ruta), para no ofrecer en la lista transportistas que de todos modos serán rechazados.
