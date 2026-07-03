# Reporte de Pruebas — 2026-07-03

## Contexto
Commit probado en esta sesión: **refactor de `_registrar_historial()`** ("Refactor _registrar_historial: usa cursor de la transacción activa, sin tragar errores"), pendiente de push al cierre de este reporte.

Sesiones anteriores (ya en `main`):
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"
3. `039a6b8` — "docs: test_report actualizado post fix migracion viaje_tramos"
4. `6755022` — "feat: guardar fechas conjunto, validacion fecha descarga, boton viaje finalizado"
5. `b93c241` — "Validación: transportista debe cubrir todas las rutas del viaje al asignar"
6. `8e3b144` — "Habilitar transportista en rutas desde asignación + precarga monto de cobro"
7. `b33a385` — "Fix vehículo colgado al reasignar + reabrir viaje cerrado (solo admin)"
8. `f2d5a7c` — "Fix: 4 columnas en uso faltantes en migración Postgres (verificación financiera + documento_identidad)"

## Alcance real vs. lo reportado
El pedido original mencionaba 8 llamadas a `_registrar_historial()`. Al mapear el archivo se encontraron **15 call sites reales** (más que los 8 estimados, probablemente por referirse a una versión anterior del archivo, antes de que prompts recientes de esta misma sesión agregaran `finalizar_viaje`, `reabrir_viaje`, `corregir_cobro` y las ramas de habilitar-rutas). Se reportó antes de implementar y se cubrieron las 15, para no dejar ninguna con el bug original.

## Correcciones aplicadas

**`_registrar_historial()` (routes/admin.py:84):** nueva firma `_registrar_historial(cursor, viaje_id, accion, detalle="")`. Ya no abre conexión propia, no comitea, no tiene `except Exception: pass`. El `INSERT` corre sobre el cursor de la transacción del endpoint llamador; el commit lo hace el propio endpoint.

**15 call sites actualizados**, cada uno verificado individualmente para que la llamada quede **antes** del `commit()` de su transacción:
- `completar_tramo_admin`: no tenía cursor propio (la mutación vive en el servicio `completar_tramo()`); se abrió una conexión dedicada solo para este registro, comiteada por el propio endpoint.
- `nueva_incidencia`, `cambiar_estado`, `marcar_cobrado`, `finalizar_viaje`, `reabrir_viaje`, `verificar_viaje` (x2): estaban después del commit/close; se movieron antes, reutilizando el cursor ya abierto.
- `asignar_camionero` y `asignar_camionero_vehiculo` (2 y 4 llamadas respectivamente): la rama de "habilitar rutas" ya estaba antes del commit (solo se cambió a usar el cursor); la rama de rechazo cerraba la conexión **antes** de registrar el historial — se reordenó para registrar primero y cerrar después; las llamadas finales (camionero asignado / vehículo desasignado) se movieron de después del commit a antes.
- `corregir_cobro`: se mantuvo el mismo condicional (`if cambios:`) pero moviendo el registro antes del commit.

`registrar_auditoria()` no se tocó (no fue parte del pedido; ya maneja errores de forma visible con `logger.error`, no un `pass` silencioso).

## Bug detectado durante la implementación
Al reproducir el flujo de asignación en el navegador tras el redeploy de código, la sesión había expirado (token CSRF inválido → `400 Bad Request` en `/admin/viaje/<id>/asignar-todo`). No es un bug del código: fue por el tiempo real transcurrido entre la carga de la página y el envío del formulario durante la sesión de pruebas. Se resolvió recargando la página (nuevo token) y volviendo a iniciar sesión — no requirió cambios de código.

## Páginas y flujo probado
Un viaje de prueba multi-tramo (2 tramos) recorrido de punta a punta: asignar transportista (rechazado por rutas → habilitar y asignar) → completar tramo 1 → completar tramo 2 → registrar incidencia → confirmar entrega (cambio de estado) → marcar cobrado → finalizar → reabrir → corregir cobro. Los 8 tipos de acción pedidos para la verificación quedaron cubiertos.

## Errores encontrados
Ninguno atribuible al refactor. 0 errores de consola en toda la sesión; el único *warning* de consola es el de formato de fecha ya documentado en reportes anteriores (preexistente, no relacionado). Sin tracebacks en el log del servidor Flask.

## Screenshots tomados
- Captura completa del panel del viaje de prueba mostrando las 11 entradas del Historial de Cambios generadas durante la prueba, en orden cronológico inverso — eliminada al finalizar la sesión (gitignored, `*.png`).

## Validaciones funcionales verificadas

| # | Acción | Entrada esperada en Historial | Estado |
|---|---|---|---|
| 1 | Asignación rechazada por cobertura de rutas | "Asignación de transportista rechazada" | ✅ |
| 2 | Habilitar rutas y asignar | "Transportista habilitado en rutas" + "Camionero asignado: ..." | ✅ |
| 3 | Completar tramo 1 y tramo 2 | "Tramo completado" (x2, con el ID de cada tramo) | ✅ |
| 4 | Registrar incidencia | "Incidencia registrada: Retraso" | ✅ |
| 5 | Confirmar entrega (cambio de estado) | "Estado cambiado a Entregado · Estado anterior: Asignado" | ✅ |
| 6 | Marcar cobrado | "Cobro registrado · Forma: Efectivo · Monto: $600.00" | ✅ |
| 7 | Finalizar viaje | "Viaje finalizado · Estado cambiado a Cerrado" | ✅ |
| 8 | Reabrir viaje | "Viaje reabierto · Estado cambiado de Cerrado a Entregado" | ✅ |
| 9 | Corregir cobro | "Cobro corregido · monto: $600.00 → $720.00" | ✅ |
| — | Todas las entradas conservan orden cronológico correcto y no se pierde ninguna | — | ✅ |
| — | Sin errores de consola ni tracebacks de servidor | — | ✅ |

## Recomendaciones
- Los datos de prueba (viaje temporal, ruta "TEST Historial-Tramo2", incidencia y filas de `camionero_ruta` creadas durante la prueba) fueron eliminados/revertidos de `mercatoria.db`; no quedan residuos.
- Dado que este refactor eliminó el `except Exception: pass` que ocultaba fallos, cualquier error futuro en el `INSERT` de historial (por ejemplo, una migración de Postgres pendiente) ahora **sí** hará fallar visiblemente el endpoint completo, en vez de continuar en silencio sin dejar rastro. Esto es el comportamiento buscado, pero conviene tenerlo presente al hacer el próximo deploy a Postgres: si `historial_viaje` no existiera ahí (no es el caso — ya se confirmó creada por `migrations_v12.py`), estos endpoints ahora fallarían con 500 en vez de simplemente omitir el registro.
