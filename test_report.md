# Reporte de Pruebas — 2026-07-02

## Contexto
Commit probado en esta sesión: **4 columnas en uso faltantes en migración Postgres** ("Fix: 4 columnas en uso faltantes en migración Postgres (verificación financiera + documento_identidad)"), pendiente de push al cierre de este reporte.

Sesiones anteriores del mismo día (ya en `main`):
1. `2f53dee` — "feat: viajes multi-tramo con validacion continuidad y timeline cliente"
2. `6aa7115` — "fix: migracion viaje_tramos produccion, boton refrescar navbar"
3. `039a6b8` — "docs: test_report actualizado post fix migracion viaje_tramos"
4. `6755022` — "feat: guardar fechas conjunto, validacion fecha descarga, boton viaje finalizado"
5. `b93c241` — "Validación: transportista debe cubrir todas las rutas del viaje al asignar"
6. `8e3b144` — "Habilitar transportista en rutas desde asignación + precarga monto de cobro"
7. `b33a385` — "Fix vehículo colgado al reasignar + reabrir viaje cerrado (solo admin)"

## Auditoría previa (antes de implementar, por pedido explícito)
Se comparó, columna por columna, cada `agregar_columna(...)` de `database.py` (SQLite) contra el conjunto combinado de `CREATE TABLE`/`ALTER TABLE ADD COLUMN IF NOT EXISTS` de los tres archivos de migración de Postgres (`migraciones_pg.py`, `migrations_v11.py`, `migrations_v12.py`), para las 20 tablas del esquema.

**Resultado:** además de las 3 columnas de verificación financiera ya conocidas (`verificado_financiero`, `verificado_por`, `fecha_verificacion` en `viajes`), se encontró una cuarta: **`clientes.documento_identidad`** — en uso activo (creación/edición de clientes, validación de duplicados) en `routes/admin.py` y en los templates `clientes.html`/`editar_cliente.html`. Se reportó al usuario antes de tocar código; confirmó incluirla en el mismo fix. No se encontraron más columnas faltantes en el resto de las tablas auditadas (camioneros, rutas, usuarios, vehiculos, tarifas, cotizaciones, tipos_vehiculo, catalogo_tipo_transporte, camionero_ruta, configuracion, configuracion_texto, reset_tokens, auditoria, notas_viaje, viaje_checklist, incidencias, historial_viaje, viaje_tramos, movimientos_viaje).

**Decisión de tipos** (para que el código funcione igual en ambos motores):
- `verificado_financiero`: **INTEGER DEFAULT 0** (no BOOLEAN) — el código ya escribe literales SQL crudos `verificado_financiero=1`/`=0` sin cast; Postgres no acepta asignar un entero literal a una columna BOOLEAN sin cast explícito, así que INTEGER es el único tipo que mantiene ese código funcionando sin cambios, además de ser consistente con columnas hermanas del mismo estilo (`activo INTEGER DEFAULT 1`, `precio_editado INTEGER DEFAULT 0`).
- `verificado_por`: TEXT (username).
- `fecha_verificacion`: **TEXT** (no TIMESTAMP) — igual que su equivalente en SQLite y que columnas hermanas (`fecha_asignacion`, `fecha_recogida`, `fecha_entrega`, todas TEXT en ambos motores). El template `reportes.html` lee este campo con un slice crudo de string (`f.fecha_verificacion[:10]`); si el tipo fuera TIMESTAMP nativo, psycopg2 devolvería un objeto `datetime` (no *sliceable*) y esa línea rompería. Se ajustó además `verificar_viaje()` en `routes/admin.py` para dejar de escribir el valor con el literal SQL `CURRENT_TIMESTAMP` (que en Postgres no tiene cast implícito hacia TEXT) y en su lugar pasar un string ya formateado (`datetime.now().strftime(...)`) como parámetro — mismo patrón que ya usa `cambiar_estado()` para columnas de fecha equivalentes.
- `documento_identidad`: TEXT.

## Bug adicional encontrado y corregido durante la verificación
Al tocar `verificar_viaje()` se detectó que `_registrar_historial()` para "Verificado financiero"/"Verificación revertida" se llamaba **antes** del `commit()`/`close()` de la conexión principal — el mismo patrón de bug ya corregido una vez en esta sesión (`asignar_camionero_vehiculo`, prompt anterior). Como `_registrar_historial()` abre su propia conexión SQLite, chocaba con la transacción de escritura aún abierta y el error quedaba silenciado por el `try/except: pass` interno; el evento nunca se guardaba en el Historial de Cambios. Se corrigió moviendo el registro a después del commit/close. Verificado: el evento "Verificado financiero" ahora sí aparece en el Historial.

## Páginas probadas
- App completa: arranque sin errores de migración (`crear_base_datos` vía SQLite local)
- `/admin/reportes`: verificar financieramente un viaje "Entregado" y cobrado
- `/admin/viaje/<id>`: cerrar → reabrir → corregir cobro (dispara el reset de verificación)
- `/admin/clientes`: crear cliente con documento de identidad
- `/admin/clientes/<id>/editar`: editar el documento de identidad de un cliente existente

## Errores encontrados
- Ninguno nuevo tras la corrección del bug de orden de historial descrito arriba. 0 errores de consola en todas las páginas probadas. Sin tracebacks en el log del servidor Flask.
- **Limitación de esta verificación, informada explícitamente:** este entorno no tiene Postgres ni `psql`/`docker` disponibles, así que no fue posible levantar una instancia real de Postgres y ejecutar `ejecutar_migraciones_pg()`/`aplicar_migraciones_v12()` contra ella de punta a punta. La verificación de la migración de Postgres se hizo por: (a) el script de auditoría columna-por-columna confirmando que las 4 columnas ya no faltan en ningún archivo de migración (`MISSING=[]`), (b) revisión manual de la sintaxis SQL añadida (comas, paréntesis, tipos) comparada exactamente con el patrón ya usado en las líneas vecinas, y (c) `py_compile` sobre los tres archivos. La app **sí** se probó de punta a punta contra SQLite local, que ejerce la misma lógica de aplicación (rutas, plantillas, tipos de columna) que Postgres usaría.

## Screenshots tomados
- Capturas del formulario "Nuevo cliente" con el campo "Documento identidad" y de "Editar Cliente" con el valor precargado — eliminadas al finalizar la sesión (gitignored, `*.png`).

## Correcciones aplicadas

**Migración Postgres — 4 columnas añadidas** (`migrations_v12.py`, `migraciones_pg.py`):
- `migrations_v12.py` (el archivo que corre siempre al arrancar, sin depender de `SKIP_MIGRATIONS` — la lección de la sesión de `viaje_tramos`): nuevas secciones `ALTER TABLE viajes ADD COLUMN IF NOT EXISTS verificado_financiero/verificado_por/fecha_verificacion` y `ALTER TABLE clientes ADD COLUMN IF NOT EXISTS documento_identidad`.
- `migraciones_pg.py`: añadidas también aquí por consistencia con el patrón "doble seguro" ya usado para `viaje_tramos` — en la rama de "schema existente" (`nuevas_columnas_viajes` + un bloque `try/except` para `documento_identidad`) y en la rama de "schema nuevo" (directamente en los `CREATE TABLE clientes`/`CREATE TABLE viajes`). El orden de creación no se alteró: estas son todas sentencias `ADD COLUMN` sobre tablas que ya se crean antes en el mismo flujo, o columnas añadidas al literal `CREATE TABLE` original.
- `routes/admin.py` (`verificar_viaje`): se reemplazó el literal SQL `CURRENT_TIMESTAMP` por un valor Python parametrizado, para evitar depender de un cast implícito timestamp→text que Postgres no garantiza.

## Validaciones funcionales verificadas

| # | Escenario | Resultado esperado | Estado |
|---|---|---|---|
| 1 | Arranque de la app (SQLite local, migración vía `crear_base_datos`) | Sin errores de migración ni columna inexistente | ✅ |
| 2 | Auditoría columna-por-columna tras el fix | 0 columnas faltantes en `viajes` y `clientes` (antes: 4) | ✅ |
| 3 | Verificar financieramente un viaje "Entregado" y cobrado | `verificado_financiero=1`, `verificado_por`, `fecha_verificacion` se guardan; Historial registra "Verificado financiero" | ✅ |
| 4 | Cerrar → reabrir el mismo viaje → corregir su cobro | `verificado_financiero` vuelve a `0`, `verificado_por`/`fecha_verificacion` a `NULL`; Historial registra el reset | ✅ |
| 5 | Crear cliente con documento de identidad | Se guarda correctamente (`CI-12345678`), sin error de columna inexistente | ✅ |
| 6 | Editar el documento de identidad de un cliente existente | Formulario precarga el valor actual; el cambio se persiste (`CI-99999999`) | ✅ |
| — | Sin errores de consola ni tracebacks de servidor en ninguna prueba | — | ✅ |

## Recomendaciones
- **Importante:** confirmar en el próximo deploy de Render (Postgres real) que los logs de arranque muestran las líneas `[ verificacion financiera ]` y `[ documento de identidad en clientes ]` de `migrations_v12.py` sin errores, dado que esta sesión no pudo probar contra un Postgres real por falta de herramientas en el entorno (sin `docker`/`psql`).
- Los datos de prueba (viaje #13, cliente "Cliente Test Doc") fueron eliminados de `mercatoria.db`; no quedan residuos.
- Dado que ya van dos rondas de auditoría de este tipo (`viaje_tramos` y ahora estas 4 columnas), podría valer la pena automatizar el script de comparación columna-por-columna usado en esta sesión como un chequeo de CI o un comando de mantenimiento, para detectar este tipo de bug antes de que llegue a producción.
