# Reporte de Pruebas — 2026-07-02

## Contexto
Dos commits probados en esta fecha:
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"

Ambos pusheados a `main` en `frankoaldos11-dotcom/Mercatoria-Trucks`.

## Páginas probadas
- `/login` (admin)
- `/admin/viajes` (listado + modal "Nuevo viaje" con selector dinámico de tramos + botón refrescar en sidebar)
- `/admin/viajes/nuevo` (POST — creación de viaje multi-tramo)
- `/admin/viajes/<id>/gestionar` (línea de progreso de tramos, botón "Marcar completado", gate de "Confirmar entrega")
- `/admin/viaje/<id>/tramo/<tramo_id>/completar` (POST — completar tramo en orden, x2)
- `/cliente/registro` y `/cliente/login` (cuenta de prueba para QA del portal cliente)
- `/cliente/solicitar` (formulario cliente con selector dinámico de tramos)
- `/cliente/viaje/<id>` (timeline visual "Recorrido de la carga")
- Navbar admin en escritorio (sidebar) y en móvil (topbar, viewport 390×800) — botón de refrescar

## Errores encontrados
- **Ninguno.** Sin errores de consola (0 errors, 0 warnings) en ninguna página revisada, sin errores HTTP (4xx/5xx), y sin excepciones/tracebacks en el log del servidor Flask durante toda la sesión.
- **Nota sobre el fix de migración:** no fue posible probar contra la base PostgreSQL real de producción (Render) desde este entorno local (SQLite). La verificación se limitó a: (a) confirmar que `migrations_v12.py` corre siempre al arrancar en `USE_POSTGRES=True` sin depender de `SKIP_MIGRATIONS` (ver `app.py:237-245`), y (b) validar sintácticamente el nuevo `CREATE TABLE IF NOT EXISTS viaje_tramos` con `py_compile`. Se recomienda confirmar en el próximo deploy de Render que la tabla se crea (revisar logs de arranque: línea `[ viajes multi-tramo ]` / `OK CREATE TABLE viaje_tramos`).

## Screenshots tomados
- `01_admin_viajes.png` — Listado de viajes (admin)
- `02_admin_modal_tramos.png` — Modal "Nuevo viaje" con 2 tramos añadidos (La Habana → Santiago → Holguin)
- `03_admin_gestionar_tramos_pendientes.png` — Vista de gestión del viaje con línea de progreso de tramos (tramo 1 en curso, tramo 2 pendiente)
- `04_admin_gestionar_tramos_completados.png` — Línea de progreso con ambos tramos completados y "Confirmar entrega" habilitado
- `05_cliente_solicitar.png` — Formulario de nueva solicitud (portal cliente) con selector de tramos
- `06_cliente_solicitar_tramos.png` — Formulario con 2 tramos añadidos en orden
- `07_cliente_viaje_detalle_timeline.png` — Timeline "Recorrido de la carga" en detalle de viaje (portal cliente)
- `refresh_btn_sidebar.png` — Botón de refrescar junto al logo "Mercatoria" en el sidebar de escritorio
- `refresh_btn_mobile.png` — Botón de refrescar en la topbar móvil (junto al hamburger)

(Los screenshots quedaron en la raíz del proyecto, ignorados por git vía `*.png` en `.gitignore`.)

## Correcciones aplicadas
- **Bug crítico de producción (reportado por el usuario):** `/cliente/solicitar` daba 500 en Render porque la tabla `viaje_tramos` nunca se creaba — `ejecutar_migraciones_pg()` respeta `SKIP_MIGRATIONS` (activo en producción) y por eso el `CREATE TABLE IF NOT EXISTS viaje_tramos` agregado en la sesión anterior no llegaba a ejecutarse. Se movió/agregó la creación de la tabla a `migrations_v12.py`, que corre siempre al arrancar sin importar `SKIP_MIGRATIONS` (mismo patrón ya usado ahí para `historial_viaje`). No requiere Shell manual en Render.
- **UX solicitada:** botón de refrescar discreto (ícono `bi-arrow-clockwise`, `window.location.reload()`) agregado en `templates/admin/base_admin.html`, junto al logo en el sidebar de escritorio y junto al botón hamburguesa en la topbar móvil. No navega a otra ruta, solo recarga la página actual.
- **Bug detectado y corregido en la sesión anterior:** panel resumen de `/admin/viajes/<id>/gestionar` mostraba KM/ruta de un solo tramo en vez del total (ver commit `2f53dee`).

## Validaciones funcionales verificadas

| # | Verificación | Estado |
|---|---|---|
| 1 | Creación de viaje con 2 tramos encadenados (admin y cliente): origen/destino se derivan del primer y último tramo | ✅ |
| 2 | Validación de continuidad server-side (rutas no encadenables rechazadas con mensaje, sin error 500) | ✅ |
| 3 | Cálculo automático: KM total, litros, pago transportista sobre KM total de tramos | ✅ |
| 4 | No se puede completar un tramo antes que el anterior (bloqueado a nivel de servicio) | ✅ |
| 5 | "Confirmar entrega" deshabilitado hasta completar todos los tramos | ✅ |
| 6 | Portal cliente: timeline visual refleja el estado real de cada tramo (verde/naranja/gris) | ✅ |
| 7 | Compatibilidad: viajes existentes sin tramos no se vieron afectados | ✅ |
| 8 | Botón refrescar (sidebar escritorio) recarga `/admin/viajes` sin redirigir a otra página | ✅ |
| 9 | Botón refrescar visible y clicable en topbar móvil (390×800) | ✅ |
| 10 | `migrations_v12.py` compila y el `CREATE TABLE IF NOT EXISTS viaje_tramos` sigue el patrón idempotente ya probado en producción para `historial_viaje` | ✅ (verificación estática; pendiente confirmar en logs de Render tras el próximo deploy) |
| — | Sin errores de consola en ninguna página | ✅ |

## Recomendaciones
- Confirmar en los logs de arranque de Render (tras el redeploy de `6aa7115`) que aparece la línea `OK CREATE TABLE viaje_tramos` bajo `[ viajes multi-tramo ]`, y volver a probar `/cliente/solicitar` en producción para cerrar el bug crítico.
- Los datos de prueba generados en ambas sesiones (viajes temporales, rutas de prueba y el usuario cliente `test.tramos.qa@example.com`) fueron eliminados de `mercatoria.db`; no quedan residuos.
- Pendiente para una futura iteración (fuera de alcance): permitir editar/agregar tramos a un viaje ya creado, y reflejar el nombre completo de la ruta multi-tramo en reportes/PDFs que hoy solo usan `viaje.ruta_id`.
