# Reporte de Pruebas — 2026-07-02

## Contexto
Commit probado en esta sesión: **fix vehículo colgado al reasignar + reabrir viaje cerrado (solo admin) + corregir cobro** ("Fix vehículo colgado al reasignar + reabrir viaje cerrado (solo admin)"), pendiente de push al cierre de este reporte.

Sesiones anteriores del mismo día (ya en `main`):
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"
3. `039a6b8` — "docs: test_report actualizado post fix migracion viaje_tramos"
4. `6755022` — "feat: guardar fechas conjunto, validacion fecha descarga, boton viaje finalizado"
5. `b93c241` — "Validación: transportista debe cubrir todas las rutas del viaje al asignar"
6. `8e3b144` — "Habilitar transportista en rutas desde asignación + precarga monto de cobro"

## Investigación previa (antes de implementar)
Por pedido explícito, antes de tocar código se investigó dónde leen el monto cobrado los reportes financieros (`/admin/reportes` y su CSV). Hallazgo reportado al usuario: `_calcular_financieros_periodo()` (`routes/admin.py`) calcula "Importe bruto/Neto" vía `calcular_liquidacion()`, que deriva el precio de `viaje.precio_final` (o `viaje_tramos`) — **no** de `viajes.monto_cobrado`. El usuario decidió, con esta información: (a) la corrección de cobro solo toca `monto_cobrado`/`forma_cobro`/`codigo_transaccion`, sin tocar `precio_final` (acciones separadas), y (b) corregir el cobro debe resetear `verificado_financiero` a pendiente si ya estaba verificado.

## Páginas probadas
- `/admin/viaje/11` (viaje de prueba cerrado con cobro y verificación financiera ya registrados): reabrir, editar pago transportista tras reabrir, corregir cobro
- `/admin/reportes`: verificar qué campos del viaje corregido se reflejan y cuáles no
- `/admin/viaje/12` (viaje de prueba asignado): reasignar transportista sin vehículo activo y con vehículo activo
- Operador (`session` simulada vía `test_client`): confirmar que no ve los botones nuevos ni puede invocar los endpoints directamente

## Errores encontrados
- **Bug propio detectado y corregido durante la sesión de QA (antes del commit):** en `asignar_camionero_vehiculo`, el nuevo registro `_registrar_historial(id, "Vehículo desasignado", ...)` se llamaba **antes** del `commit()`/`close()` de la conexión principal. Como `_registrar_historial()` abre su propia conexión SQLite y el proyecto usa `sqlite3` con locking a nivel de archivo, esa segunda conexión chocaba con la transacción de escritura aún abierta en la conexión principal (`UPDATE viajes...`, `UPDATE vehiculos...` sin commitear) — el error quedaba silenciado por el `try/except: pass` interno de `_registrar_historial()`, así que el registro nunca se guardaba, sin ningún error visible. Se corrigió moviendo el registro a después del `commit()`/`close()`, junto al resto de los registros de historial de ese endpoint (mismo patrón ya usado en el resto del archivo). Verificado con una segunda prueba: el evento "Vehículo desasignado" ahora sí aparece en el Historial de Cambios.
- Sin más errores de consola (0 errors) en ninguna prueba.

## Screenshots tomados
- Capturas de pantalla completa del viaje #11 antes y después de reabrir, confirmando el bloqueo/desbloqueo de cada paso, el botón "Reabrir viaje", el bloque "Corregir cobro (viaje reabierto)" y el reporte financiero — eliminadas al finalizar la sesión (gitignored, `*.png`).

## Correcciones aplicadas

**1. Bug — vehículo colgado al reasignar** (`routes/admin.py`, `asignar_camionero_vehiculo`): cuando el nuevo transportista no tiene vehículo activo, el viaje ya no conserva el `vehiculo_id`/`vehiculo_placa` anterior — se limpian a `NULL`. Si el vehículo anterior estaba `'En viaje'`, se libera a `'Disponible'`. Se registra "Vehículo desasignado" en el Historial (después del commit, corrigiendo el bug propio descrito arriba). El caso de reasignación con vehículo activo sigue igual.

**2. Feature — reabrir viaje cerrado** (`routes/admin.py`, `templates/admin/gestionar_viaje.html`):
- Nueva columna `viajes.reabierto_en` (TIMESTAMP, nullable) — migración en `database.py` (`agregar_columna`) y en `migrations_v12.py` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, el archivo que ya confirmamos que corre siempre en producción sin depender de `SKIP_MIGRATIONS`).
- Nuevo endpoint `POST /viaje/<id>/reabrir`: chequeo estricto `session.get("rol") != "admin"` (no `requiere_admin()`, que también deja pasar al operador). Solo actúa si el viaje está cerrado; pasa `estado` a `'Entregado'` y setea `reabierto_en`. Registra en Historial y Auditoría.
- Al reabrir, todo lo que bloqueaba `_viaje_cerrado()` vuelve a estar disponible: combustible, fechas, documentación, entrega, pago al transportista (incluido su botón "revertir"), cambiar estado, prioridad, asignación de transportista.
- UI: botón "Reabrir viaje" junto al bloque "Viaje finalizado y cerrado", visible solo para `rol == 'admin'`, con `confirm()` de advertencia.

**3. Feature — corregir cobro en viaje reabierto** (`routes/admin.py`, `templates/admin/gestionar_viaje.html`):
- Nuevo endpoint `POST /viaje/<id>/corregir-cobro`: solo admin, solo si `viaje.reabierto_en` está seteado y el viaje no está cerrado. Actualiza `forma_cobro`/`monto_cobrado`/`codigo_transaccion`.
- Si el viaje ya estaba `verificado_financiero=1`, la corrección lo resetea a `0` (limpia `verificado_por`/`fecha_verificacion`), forzando nueva verificación.
- Cada corrección registra en Historial de Cambios el valor anterior → nuevo de cada campo modificado, más el aviso de reversión de verificación si aplica.
- UI: bloque colapsable "Corregir cobro (viaje reabierto)" dentro de "Registro de cobro al cliente", con los 3 campos precargados, visible solo si `viaje.reabierto_en` y no cerrado (implícitamente solo admin, todo el panel de cobro ya es admin-only).

## Validaciones funcionales verificadas

| # | Escenario | Resultado esperado | Estado |
|---|---|---|---|
| 1 | Reabrir un viaje cerrado como admin | Estado pasa a "Entregado", header ya no dice "CERRADO", historial registra "Viaje reabierto · Estado cambiado de Cerrado a Entregado · admin · fecha" | ✅ |
| 2 | Tras reabrir: editar "Pago al transportista" | Accordion muestra botones "Marcar como pagado"/"Pendiente de pago" habilitados de nuevo | ✅ |
| 3 | Tras reabrir: pasos de fechas/documentación/cambiar estado | Todos vuelven a mostrar formularios editables | ✅ |
| 4 | Corregir cobro (monto $500→$650, código OLD123→NEW456) | Historial registra "monto: $500.00 → $650.00; código transacción: 'OLD123' → 'NEW456'; verificación financiera revertida a pendiente" | ✅ |
| 5 | `verificado_financiero` tras corregir (viaje previamente verificado) | Vuelve a `0`, `verificado_por`/`fecha_verificacion` a `NULL` | ✅ |
| 6 | Reporte financiero (`/admin/reportes`) tras la corrección | La fila del viaje muestra el `codigo_transaccion` corregido ("NEW456") y reaparece el botón "Confirmar cobrado y verificado" (por el reset de verificación). El "Importe Bruto" **no cambia** ($1000.00, derivado de `precio_final`) — comportamiento esperado y decidido explícitamente por el usuario, no un bug | ✅ |
| 7 | Botón "Reabrir viaje" y bloque "Corregir cobro" para rol operador | No aparecen en el HTML renderizado | ✅ |
| 8 | POST directo a `/reabrir` como operador (bypass de UI) | Redirige a `/login`, sin cambios en BD | ✅ |
| 9 | Reasignar transportista **sin** vehículo activo | `vehiculo_id`/`vehiculo_placa` del viaje quedan `NULL`; el vehículo anterior (`'En viaje'`) se libera a `'Disponible'`; Historial registra "Vehículo desasignado" | ✅ |
| 10 | Reasignar transportista **con** vehículo activo (regresión) | Vehículo se asigna y marca `'En viaje'` exactamente igual que antes del fix | ✅ |
| — | Sin errores de consola en ninguna prueba | — | ✅ |

## Recomendaciones
- Los datos de prueba (viajes #11 y #12, la fila temporal de `camionero_ruta` para la prueba de regresión, y los estados de vehículo/camionero modificados) fueron eliminados/revertidos de `mercatoria.db`; no quedan residuos.
- Si en el futuro se necesita que el reporte financiero refleje el monto realmente cobrado (no solo `precio_final`), habrá que decidir explícitamente cómo reconciliar ambos valores — quedó fuera de alcance de este prompt por decisión del usuario.
- Se detectó (no se tocó, fuera de alcance) que las columnas `verificado_financiero`/`verificado_por`/`fecha_verificacion` no están presentes en ninguna migración de PostgreSQL (`migrations_v11.py`, `migrations_v12.py`, `migraciones_pg.py`) — mismo patrón de bug que motivó el fix de migración de `viaje_tramos` hace unas sesiones. Recomiendo revisarlo pronto si el proyecto corre en Postgres en producción.
