# Reporte de Pruebas — 2026-07-02

## Contexto
Commit probado: `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente" (push a `main` en `frankoaldos11-dotcom/Mercatoria-Trucks`).

## Páginas probadas
- `/login` (admin)
- `/admin/viajes` (listado + modal "Nuevo viaje" con selector dinámico de tramos)
- `/admin/viajes/nuevo` (POST — creación de viaje multi-tramo)
- `/admin/viajes/<id>/gestionar` (línea de progreso de tramos, botón "Marcar completado", gate de "Confirmar entrega")
- `/admin/viaje/<id>/tramo/<tramo_id>/completar` (POST — completar tramo en orden, x2)
- `/cliente/registro` y `/cliente/login` (cuenta de prueba para QA del portal cliente)
- `/cliente/solicitar` (formulario cliente con selector dinámico de tramos)
- `/cliente/viaje/<id>` (timeline visual "Recorrido de la carga")

## Errores encontrados
- **Ninguno.** Sin errores de consola (0 errors, 0 warnings en todas las páginas revisadas), sin errores HTTP (4xx/5xx) en las requests dinámicas ni estáticas, y sin excepciones/tracebacks en el log del servidor Flask durante toda la sesión de pruebas.

## Screenshots tomados
- `01_admin_viajes.png` — Listado de viajes (admin)
- `02_admin_modal_tramos.png` — Modal "Nuevo viaje" con 2 tramos añadidos (La Habana → Santiago → Holguin)
- `03_admin_gestionar_tramos_pendientes.png` — Vista de gestión del viaje con línea de progreso de tramos (tramo 1 en curso, tramo 2 pendiente)
- `04_admin_gestionar_tramos_completados.png` — Línea de progreso con ambos tramos completados y "Confirmar entrega" habilitado
- `05_cliente_solicitar.png` — Formulario de nueva solicitud (portal cliente) con selector de tramos
- `06_cliente_solicitar_tramos.png` — Formulario con 2 tramos añadidos en orden
- `07_cliente_viaje_detalle_timeline.png` — Timeline "Recorrido de la carga" en detalle de viaje (portal cliente): tramo 1 naranja (en curso), tramo 2 gris (pendiente)

(Los screenshots quedaron en la raíz del proyecto, ignorados por git vía `*.png` en `.gitignore`.)

## Correcciones aplicadas
- **Bug detectado y corregido durante esta sesión de QA** (antes del commit): en `/admin/viajes/<id>/gestionar`, el panel resumen mostraba "KM a recorrer" y "Ruta" usando solo la primera ruta del viaje, ignorando el resto de los tramos. Se corrigió en `routes/admin.py` (`gestionar_viaje`) para que, cuando el viaje tiene tramos, `km_ruta` sea la suma de `km_oficiales` de todos los tramos y `ruta_display` muestre la cadena completa (`Origen → Parada 1 → ... → Destino final`). Verificado: pasó de mostrar "1020 km" / "La Habana → Santiago" a "1220 km" / "La Habana → Santiago → Holguin" para un viaje de 2 tramos.

## Validaciones funcionales verificadas

| # | Verificación | Estado |
|---|---|---|
| 1 | Creación de viaje con 2 tramos encadenados (admin y cliente): origen/destino del viaje se derivan del primer y último tramo | ✅ |
| 2 | Validación de continuidad server-side (rutas no encadenables rechazadas con mensaje, sin error 500) | ✅ |
| 3 | Cálculo automático: KM total = suma de tramos (1220 km), litros = KM total ÷ divisor (610.0 L), pago transportista = KM total × tarifa global ($2745.00) | ✅ |
| 4 | No se puede completar el tramo 2 antes que el tramo 1 (bloqueado a nivel de servicio) | ✅ |
| 5 | Al completar un tramo, el siguiente pasa automáticamente a "en curso" | ✅ |
| 6 | "Confirmar entrega" permanece deshabilitado hasta completar todos los tramos | ✅ |
| 7 | Portal cliente: timeline visual refleja el estado real de cada tramo (verde/naranja/gris) | ✅ |
| 8 | Compatibilidad: viajes existentes sin tramos (#1–#4) no se vieron afectados | ✅ |
| — | Sin errores de consola en ninguna página | ✅ |

## Recomendaciones
- Los datos de prueba (viajes temporales, ruta "TEST Santiago-Holguin" y el usuario cliente `test.tramos.qa@example.com`) fueron eliminados de `mercatoria.db` al finalizar esta sesión; no quedan residuos.
- Pendiente para una futura iteración (fuera del alcance de este prompt): permitir editar/agregar tramos a un viaje ya creado, y reflejar el nombre completo de la ruta multi-tramo en reportes/PDFs que hoy solo usan `viaje.ruta_id` (ej. orden de carga).
