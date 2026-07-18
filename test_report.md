# Reporte de Pruebas — 2026-07-18 (Orden de carga sin transportista + eliminación de viajes con aprobación)

## Contexto
Dos ajustes de producción: la orden de carga se emite antes de asignar transportista/vehículo (la aceptación es lo que asigna), y el PM necesita poder solicitar la eliminación de un viaje sin poder borrarlo él mismo — requiere confirmación del Admin.

## Páginas probadas (local, `127.0.0.1:5001` — el 5000 sigue ocupado por el proceso ajeno que Aldo diagnostica aparte)
- `/admin/viaje/<id>`, `/admin/viajes`, `/admin/` (dashboard), `/admin/papelera`

## Investigación previa a la implementación
- **CAMBIO 1**: confirmado leyendo `generar_pdf_orden_carga` completa que la sección "VEHÍCULO Y CONDUCTOR" es la única parte del PDF que depende de transportista/vehículo, y que ningún campo posterior depende de sus variables. Confirmado que `pago_camionero`/`litros_combustible`/`fecha_creacion` ya tenían fallback limpio (nunca "None"). Confirmado que `calcular_liquidacion()` no depende de `camionero_id`.
- **CAMBIO 2**: confirmado que `solicitudes_eliminacion` ya existe y ya tiene un flujo completo funcionando para transportistas (`eliminar_camionero`), y que `aprobar_eliminacion`/`rechazar_eliminacion` **ya soportan `entidad="viaje"`** sin cambios — solo faltaba el lado de creación de la solicitud. Confirmado que `viajes` ya usa borrado lógico (`deleted_at`/`deleted_by`), igual que clientes/transportistas — sin necesidad de decidir nada nuevo ahí.

## Pruebas realizadas
1. **CAMBIO 1**: viaje de prueba sin transportista/vehículo → paso 2 muestra "Ver Orden de Carga" habilitado (antes aparecía deshabilitado). PDF descargado y verificado con `pypdf`: no aparece la sección "VEHÍCULO Y CONDUCTOR", no aparece ningún "None" en el texto extraído, "PAGO AL TRANSPORTISTA" muestra el estimado calculado igual, "COMBUSTIBLE CONFIRMADO" muestra "Pendiente de confirmar" limpiamente.
2. **CAMBIO 2**: como operador de prueba — solicitud de eliminación desde el listado (`/admin/viajes`, sin motivo) y desde el detalle (`/admin/viaje/<id>`, con motivo) — en ambos casos el viaje permaneció vivo y apareció en `solicitudes_eliminacion` con `estado='Pendiente'`. Como admin — ambas solicitudes visibles en el dashboard con su motivo (columna nueva), aprobada una (viaje pasó a `deleted_at` no nulo) y rechazada la otra (`estado='Rechazada'`, viaje sin cambios).
3. **Hallazgo adicional durante la verificación, confirmado y corregido con Aldo**: el listado de viajes (`_contexto_lista_viajes`) nunca filtraba `deleted_at IS NULL` — un hueco preexistente (el botón de eliminar directo del admin ya soft-eliminaba desde antes de esta tarea, pero el viaje nunca desaparecía del listado). Se agregó el mismo filtro que ya usan clientes/transportistas. Reverificado: el viaje aprobado ahora sí desaparece del listado (5 viajes en vez de 6), el rechazado sigue apareciendo.
4. `python -m py_compile` sobre todos los `.py` tocados — sin errores. Templates parseados vía `app.jinja_env.get_template()` — sin errores.

## Errores encontrados
Ninguno funcional en el código nuevo, salvo el hallazgo de la nota 3 arriba (preexistente, no introducido por esta tarea, corregido con confirmación explícita).

## Correcciones aplicadas
`services/pdf_service.py` (quita sección "VEHÍCULO Y CONDUCTOR" de `generar_pdf_orden_carga`), `routes/admin.py` (quita checks de transportista/vehículo en `descargar_pdf_orden_carga` y `gestionar_viaje`; `eliminar_viaje_admin` reescrito con rama admin/operador reutilizando `solicitudes_eliminacion`; `motivo` agregado a la consulta de `dashboard()`; filtro `deleted_at IS NULL` agregado a `_contexto_lista_viajes`), `migraciones.py` + `migrations_v16.py` (nuevo) + `app.py` (columna `motivo` en `solicitudes_eliminacion`), `templates/admin/gestionar_viaje.html` (bloque "Eliminar viaje" con rama admin/operador + textarea de motivo, colores migrados a `var(--error-real)`), `templates/admin/viajes.html` (botón-ícono de eliminar/solicitar por fila), `templates/admin/dashboard.html` y `templates/admin/papelera.html` (columna "Motivo").

## Datos de prueba y limpieza
- Cuenta `_test_operador_elim` (rol operador): creada y eliminada.
- Viajes de prueba #39 (Cienfuegos→Trinidad) y #40 (Bayamo→Manzanillo), sus solicitudes de eliminación, y sus filas de historial/auditoría: creados durante la verificación y eliminados por completo al finalizar.
- Servidor Flask (puerto 5001) detenido tras confirmación explícita. `Get-Process python` solo muestra el proceso ajeno del puerto 5000, sin tocar.

## Recomendaciones
Ninguna pendiente de esta tanda.
