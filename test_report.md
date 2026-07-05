# Reporte de Pruebas — 2026-07-05

## Contexto
Commit de esta sesión: **seis correcciones en el flujo de viajes** ("Fixes flujo viaje: tramo UX, factura PDF, validacion transportista temprana, conservar datos, entrega fuera de fecha, conteo en curso"), pendiente de push al cierre de este reporte.

Sesiones anteriores (ya en `main`):
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"
3. `039a6b8` — "docs: test_report actualizado post fix migracion viaje_tramos"
4. `6755022` — "feat: guardar fechas conjunto, validacion fecha descarga, boton viaje finalizado"
5. `b93c241` — "Validación: transportista debe cubrir todas las rutas del viaje al asignar"
6. `8e3b144` — "Habilitar transportista en rutas desde asignación + precarga monto de cobro"
7. `b33a385` — "Fix vehículo colgado al reasignar + reabrir viaje cerrado (solo admin)"
8. `f2d5a7c` — "Fix: 4 columnas en uso faltantes en migración Postgres (verificación financiera + documento_identidad)"
9. `590c14a` — "Refactor _registrar_historial: usa cursor de la transacción activa, sin tragar errores"
10. `65772e0` — "Elimina conectar() local de migraciones.py, usa conexión centralizada"
11. `75cf3b0` — "Fix: SKIP_MIGRATIONS ya no puede dejar una Postgres vacia sin schema"
12. `799a221` — "Vincular usuario cliente a su ficha desde admin + crear cliente desde pantalla de usuario"

## Correcciones aplicadas (una por punto del prompt)

**1. UX de tramos.** `templates/cliente/solicitar.html` y `templates/admin/viajes.html`: texto de ayuda explícito ("selecciona la ruta y pulsa 'Añadir tramo' para confirmarla") + el botón "Añadir tramo" se resalta visualmente (box-shadow pulsante) en cuanto se elige una ruta en el desplegable sin haberla añadido, con un aviso textual debajo. El resaltado se apaga al añadir el tramo. No se tocó el flujo multi-tramo existente.

**2. Factura no descarga — causa raíz encontrada y corregida.** El fallback de auto-creación de `clientes` en `routes/cliente.py` (`solicitar()`) usaba `session.get("nombre", "")`, pero el login real (`app.py` `/login`) nunca setea `session["nombre"]` (solo lo hace una ruta de login duplicada e inalcanzable en `cliente.py`). Cualquier cliente cuya ficha se creara por esa vía quedaba con `nombre=""` para siempre, y `generar_factura_cliente()` rechaza clientes sin nombre real — pero `descargar_factura()` tragaba la excepción en silencio y solo redirigía, así que el cliente no veía nada. Fix: (a) nombre de respaldo razonable (parte local del email) en vez de cadena vacía; (b) `descargar_factura()` ya no traga el error — lo pasa a la página vía query param y se muestra en un banner visible. **Bug propio detectado y corregido durante la verificación:** mi primera implementación combinaba `quote_plus()` con `url_for()`, que ya codifica sus parámetros — esto producía doble codificación y el mensaje se mostraba con `+` y `%2C` literales en vez de espacios y comas. Corregido pasando el string plano a `url_for()`.

**3. Transportista temprano.** `cambiar_estado()` (transición a "Entregado") y `marcar_cobrado()` ahora exigen `camionero_id` asignado, con mensaje claro, tanto en backend (verificado con POST directo vía `fetch()`, bypaseando el UI) como en el template (botones deshabilitados con el mismo patrón visual que el bloqueo de tramos incompletos).

**4. Conservar datos tras error de validación.** `admin_camioneros()` ya re-renderizaba pero no rellenaba los campos — se agregó `form_data`. `admin_clientes()` y `nuevo_viaje_admin()` **redirigían** en el error (perdían el POST completo) — se cambiaron a re-renderizar directamente, reutilizando el listado (`_contexto_lista_viajes()` extraído como helper compartido para `viajes()` y `nuevo_viaje_admin()`). El modal de "Nuevo viaje" se auto-abre si hay error, incluidos los tramos ya seleccionados (reconstruidos en JS desde `form_data`).

**5. Entrega fuera de fecha.** `cambiar_estado()`: si el viaje ya tenía `fecha_entrega` guardada (vía "Guardar fechas") y no coincide con la fecha real del sistema, la confirmación de entrega dispara un `confirm()` de advertencia distinto al normal; si el admin continúa, se conserva la fecha ya registrada (no se sobreescribe con hoy) y el Historial queda marcado como "Entrega confirmada con fecha retroactiva" con el detalle de ambas fechas. **Si no hay fecha previa registrada, no hay aviso ni marca — se usa hoy con normalidad**, tal como se acordó explícitamente.

**6. Dashboard "Viajes en curso".** El `CASE` pasó de `LOWER(estado) IN ('en ruta','en_ruta')` a `LOWER(estado) NOT IN ('entregado','cerrado','cancelado')`.

## Verificación con Playwright (todos los puntos)

| # | Verificación | Resultado |
|---|---|---|
| 1 | Elegir ruta sin añadir → botón se resalta + aviso visible; añadir tramo → resaltado se apaga | ✅ Verificado en `/admin/viajes` (JS `boxShadow`/`display` inspeccionados directamente) |
| 2 | Cliente con nombre válido → factura se descarga (`factura-0017.pdf` descargado con éxito) | ✅ |
| 2 | Cliente con `nombre=''` (el caso raíz) → error visible en banner rojo, con el motivo exacto, ya no silencioso | ✅ (y se corrigió el bug de doble-encoding encontrado en el camino) |
| 3 | POST directo a `/estado` (Entregado) sin transportista → bloqueado, estado permanece "Pendiente" | ✅ |
| 3 | POST directo a `/marcar-cobrado` sin transportista → bloqueado, redirige con error | ✅ |
| 3 | UI: botones "Confirmar entrega" y "Marcar cobrado" deshabilitados con mensaje cuando no hay transportista | ✅ |
| 4 | Camionero — matrícula duplicada (ejemplo literal del prompt): error mostrado, **todos** los campos conservados (nombre, teléfono, empresa, matrícula, marca) | ✅ |
| 4 | Ciclo completo: corregir matrícula → reenviar → `?ok=1`, sin error 400 de CSRF | ✅ |
| 4 | Cliente — email duplicado: error mostrado, nombre/empresa/email conservados; corregir → reenviar → `?ok=1` sin error CSRF | ✅ |
| 5 | Fecha de descarga guardada distinta a hoy + confirmar entrega → diálogo de advertencia con ambas fechas | ✅ |
| 5 | Continuar tras advertencia → Historial: "Entrega confirmada con fecha retroactiva", fecha original conservada (no sobreescrita) | ✅ |
| 5 | Sin fecha previa registrada + confirmar entrega → diálogo normal, sin marca retroactiva, fecha_entrega = hoy | ✅ |
| 6 | Dashboard con 4 viajes en estado "Asignado" → "Viajes en curso" muestra 4 (antes mostraba 0) | ✅ |

## Errores encontrados durante la sesión (y su resolución)
- **Bug propio de doble-codificación de URL** en el fix del punto 2 (`quote_plus()` + `url_for()`) — detectado durante la propia verificación de Playwright, corregido antes de cerrar el punto.
- Advertencia de consola preexistente y ya documentada en reportes anteriores (formato de fecha del `<input type="date">` vs. el string con hora completa que devuelve `cambiar_estado()`) — no es una regresión de esta sesión.
- Nota operativa: durante la prueba del punto 2 se restableció temporalmente la contraseña del usuario de prueba `ana2@test.com` (dato de desarrollo local, no de producción) para poder iniciar sesión como ese cliente.

## Páginas probadas
- `/admin/viajes` (modal Nuevo viaje, tramos, ciclo de error/corrección)
- `/admin/camioneros` (ciclo de error/corrección)
- `/admin/clientes` (ciclo de error/corrección)
- `/admin/viajes/<id>/gestionar` (bloqueo de entrega/cobro, fecha retroactiva, historial)
- `/admin` (dashboard, conteo de viajes en curso)
- `/cliente/viaje/<id>` y `/cliente/viaje/<id>/factura` (descarga exitosa y caso de error visible)

## Limpieza posterior
Todos los viajes, clientes y usuarios de prueba creados durante esta verificación (ids 15–18, cliente "Cliente Test Conservar", camionero "Test Conservar Datos" y su vehículo, usuario `clientevacio@test.com`) fueron eliminados de `mercatoria.db` al finalizar. Los 4 viajes y camioneros/clientes preexistentes de sesiones anteriores no se tocaron.

## Recomendaciones
- Ninguna corrección quedó pendiente de los 6 puntos pedidos.
- Vale la pena, en un futuro prompt aparte, revisar si conviene eliminar la ruta de login duplicada e inalcanzable en `routes/cliente.py` (`cliente.login()` POST), ya que fue la pista que confirmó por qué `session["nombre"]` nunca se seteaba en el flujo real.
