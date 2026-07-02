# Reporte de Pruebas — 2026-07-02

## Contexto
Commit probado en esta sesión: **Prompt I — Fixes flujo del viaje** ("feat: guardar fechas conjunto, validacion fecha descarga, boton viaje finalizado"), pendiente de push al cierre de este reporte.

Sesiones anteriores del mismo día (ya en `main`):
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"
3. `039a6b8` — "docs: test_report actualizado post fix migracion viaje_tramos"

## Páginas probadas
- `/login` (admin)
- `/admin/viaje/<id>` (viaje #1, con cobro ya registrado) — botón único "Guardar fechas", validación `min=` de fecha de descarga, botón "Viaje finalizado"
- `/admin/viaje/<id>` (viaje #2, sin cobro) — flujo normal no afectado: paso de fechas editable, sin botón de finalizar
- Accordion "Pago al transportista" dentro de la vista de gestión

## Errores encontrados
- **Ninguno de los cambios de esta sesión.** Sin errores de consola (0 errors) ni HTTP en las páginas probadas.
- **Hallazgo preexistente (no introducido en esta sesión):** dos warnings de consola en `/admin/viaje/2` — `The specified value "2026-06-26 13:16:35" does not conform to the required format, "yyyy-MM-dd"`. Ocurre porque algunas fechas de viajes antiguos se guardaron con timestamp completo (vía `cambiar_estado`) en vez de `YYYY-MM-DD` (vía `guardar_fechas`), y el input `type="date"` no puede prellenar ese valor. Ya existía antes de este prompt (mismo patrón `value="{{ viaje.fecha_recogida or '' }}"` en el código original); no se corrigió por estar fuera de alcance — no rompe el guardado, solo el campo se ve vacío al editar.

## Correcciones aplicadas (Prompt I)

1. **Guardar todo en un solo botón:** `templates/admin/gestionar_viaje.html` — los pasos 3 ("Fecha de extracción") y 4 ("Fecha de descarga") se fusionaron en un único paso "Fechas de recogida y descarga" con un solo formulario y botón **"Guardar fechas"**, que envía `fecha_recogida` y `fecha_entrega` en un solo POST a `/admin/viaje/<id>/guardar-fechas` (el endpoint ya soportaba ambos campos). Los pasos siguientes se renumeraron (4→Documentación, 5→Confirmar entrega, 6→Pago transportista).
2. **Validación de fecha de descarga:** JS agregado al final de la plantilla fija `min` en el input de fecha de descarga = valor actual de fecha de extracción (en vivo, se actualiza si el usuario cambia la extracción antes de guardar) o la fecha de hoy si aún no hay extracción. Verificado con `checkValidity()`: el navegador rechaza fechas de descarga anteriores con el mensaje nativo "El valor debe ser igual o posterior a...".
3. **Botón "Viaje finalizado":** nuevo endpoint `POST /admin/viaje/<id>/finalizar` (`routes/admin.py`) que exige `fecha_cobro` ya registrado y cambia `estado` a `'Cerrado'`. En la plantilla, tras el bloque "Cobrado" aparece un botón verde grande "✓ Viaje finalizado" con `confirm()` con el texto exacto pedido. Al confirmarse:
   - El viaje pasa a estado **Cerrado** (badge del header, historial y auditoría registrados).
   - **Ningún campo queda editable**: se añadieron guardas de "viaje cerrado" tanto en la UI (todas las tarjetas de pasos muestran un estado gris "· Viaje cerrado" sin formularios ni botones de acción) como en el **backend** (nuevo helper `_viaje_cerrado()` bloquea con redirect+error los endpoints `asignar-todo`, `asignar`, `asignar-vehiculo`, `estado`, `confirmar-precio`, `guardar-combustible`, `guardar-fechas`, `pago-camionero`, `marcar-cobrado`, `prioridad` y `completar_tramo` si el viaje ya está cerrado).
   - El accordion "Cambiar estado" desaparece (se agregó `"cerrado": []` a `_transiciones`).
   - El accordion "Pago al transportista" muestra "Viaje cerrado — no admite cambios" en vez del formulario.
   - El bloque final se actualizó para reflejar el cierre real ("Viaje finalizado y cerrado" con ícono de candado) en vez del indicador heurístico anterior basado en checklist.

## Validaciones funcionales verificadas

| # | Verificación | Estado |
|---|---|---|
| 1 | Un solo clic en "Guardar fechas" persiste `fecha_recogida` y `fecha_entrega` en un solo POST | ✅ |
| 2 | `min` de fecha de descarga = fecha de extracción (en vivo) o fecha de hoy si no hay extracción | ✅ |
| 3 | Navegador bloquea (`checkValidity()=false`) una fecha de descarga anterior a la de extracción | ✅ |
| 4 | Botón "Viaje finalizado" solo aparece cuando el cobro ya está registrado y el viaje no está cerrado | ✅ |
| 5 | Confirm dialog con el texto exacto solicitado | ✅ |
| 6 | Tras confirmar: estado pasa a "Cerrado", badge de header actualizado, historial registrado | ✅ |
| 7 | Ningún paso (transportista, combustible, fechas, documentación, entrega, pago) muestra formulario editable tras el cierre | ✅ |
| 8 | Accordion "Cambiar estado" no aparece en viaje cerrado | ✅ |
| 9 | Backend rechaza (redirect + mensaje de error) intentos directos de POST a `guardar-combustible` y `estado` sobre un viaje cerrado, sin modificar datos (verificado con `test_client`, sin pasar por la UI) | ✅ |
| 10 | Doble clic en "Viaje finalizado" no rompe nada (segunda llamada es no-op) | ✅ |
| 11 | Flujo normal de un viaje NO cerrado (viaje #2) no se vio afectado: fechas editables, "Cambiar estado" visible | ✅ |
| — | Sin errores de consola nuevos | ✅ |

## Recomendaciones
- El warning preexistente de formato de fecha (ver "Errores encontrados") podría limpiarse a futuro normalizando `fecha_recogida`/`fecha_entrega` a `YYYY-MM-DD` en todos los puntos donde se escriben (hoy `cambiar_estado` usa timestamp completo). Fuera de alcance de este prompt.
- Los datos de prueba de esta sesión (estado y fechas temporales del viaje #1, registros de historial/auditoría del "finalizar" de prueba) fueron revertidos en `mercatoria.db`; no quedan residuos.
- Dado que "Cerrado" es un estado terminal nuevo, revisar si algún reporte/dashboard filtra viajes por lista fija de estados y debería incluir "Cerrado" explícitamente (no se tocó nada fuera de `gestionar_viaje.html` y `routes/admin.py` en este prompt).
