# Reporte de Pruebas — 2026-07-03

## Contexto
Commit probado en esta sesión: **fix del bootstrap de `SKIP_MIGRATIONS` en `migraciones_pg.py`** ("Fix: SKIP_MIGRATIONS ya no puede dejar una Postgres vacia sin schema"), pendiente de push al cierre de este reporte.

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

## Corrección aplicada
`migraciones_pg.py` — `ejecutar_migraciones_pg()` se reordenó completamente:

1. La consulta `SELECT COUNT(*) FROM information_schema.tables WHERE table_name='usuarios'` ahora corre **primero**, sin condición alguna.
2. Si el schema **no existe** (`not schema_existe`), se ejecuta siempre la creación completa (todas las `CREATE TABLE`), sin mirar `SKIP_MIGRATIONS` — una base vacía se crea con o sin el flag. Esta rama termina con `conn.commit(); cur.close(); conn.close(); return`, igual que antes (mismo manejo de conexión, solo con un `return` explícito porque ahora ya no es el final físico del archivo).
3. Solo si el schema **ya existe** se evalúa `SKIP_MIGRATIONS`: si está en `true`, se omiten las migraciones incrementales (`conn.close(); return`); si no, corren igual que siempre (mismos `ALTER TABLE`/`CREATE TABLE IF NOT EXISTS`, mismo manejo de conexión con `conn.close()` al final, try/except por sentencia sin cambios).

Ninguna sentencia SQL cambió. Solo se movió el orden de los chequeos y a qué rama afecta el flag, tal como se acordó.

## Verificación (sin Postgres disponible en este entorno)

Dado que el entorno local no tiene Postgres, se hizo:

1. **Auditoría de código línea por línea** confirmando la nueva estructura de control (`schema_existe` se calcula antes de cualquier chequeo de flag; `SKIP_MIGRATIONS` solo se lee dentro de la rama donde el schema ya existe).
2. **Simulación funcional de los 3 escenarios** con una conexión/cursor simulados (mock de `psycopg2`) que registra cada sentencia SQL ejecutada, para probar el árbol de decisión real de Python (no solo la lectura del código):

| Escenario | `schema_existe` | `SKIP_MIGRATIONS` | Resultado esperado | Resultado obtenido |
|---|---|---|---|---|
| (1) Base vacía + flag activo | `False` | `true` | Crea el schema completo (ignora el flag) | ✅ Corrió `CREATE TABLE ... usuarios` y el resto del schema completo; no corrió ninguna migración incremental |
| (2) Schema existente + flag activo | `True` | `true` | Salta las migraciones incrementales, no recrea nada | ✅ No corrió ni el schema completo ni los incrementales — retornó de inmediato tras el mensaje de "omitiendo" |
| (3) Schema existente + flag ausente | `True` | *(no seteada)* | Corre las migraciones incrementales normalmente | ✅ Corrió `ALTER TABLE clientes ADD COLUMN IF NOT EXISTS categoria` y el resto del bloque incremental |

Los 3 escenarios se comportaron exactamente como lo especifica la mitigación acordada.

3. **Arranque local (SQLite)** sin cambios ni errores — este archivo no se toca en esa rama de `app.py`, se verificó como control de que nada se rompió colateralmente.

**⚠️ Pendiente:** esta verificación es de código y de lógica simulada, no contra una Postgres real. La verificación definitiva contra producción queda pendiente del próximo deploy en Render (confirmar en los logs de arranque que aparece el mensaje esperado según el estado real de la base al momento del deploy).

## Páginas probadas
- Arranque completo de la app (SQLite local) vía `python app.py` — sin errores, como control de no-regresión.

## Errores encontrados
Ninguno. 0 errores de consola, sin tracebacks en el log del servidor local.

## Screenshots tomados
- Ninguno nuevo — este fix no tiene superficie de UI (solo lógica de arranque de Postgres, no ejercitable desde el navegador en este entorno).

## Validaciones funcionales verificadas

| # | Verificación | Resultado esperado | Estado |
|---|---|---|---|
| 1 | Base vacía + `SKIP_MIGRATIONS=true` → crea schema completo | Sí, ignorando el flag | ✅ (simulado) |
| 2 | Schema existente + `SKIP_MIGRATIONS=true` → salta incrementales | Sí, sin recrear nada | ✅ (simulado) |
| 3 | Schema existente + `SKIP_MIGRATIONS` ausente → corre incrementales | Sí, igual que antes | ✅ (simulado) |
| 4 | Ninguna sentencia SQL cambió de contenido | Solo se reordenó el control de flujo | ✅ (diff de código) |
| 5 | Arranque local SQLite sin regresión | Sin errores | ✅ |
| — | Verificación real contra Postgres | **Pendiente del próximo deploy en Render** | ⏳ |

## Recomendaciones
- Confirmar en el próximo deploy a Render que el log de arranque muestre el mensaje correcto según el estado real de la base (`"Schema nuevo — ejecutando migraciones completas."` o `"SKIP_MIGRATIONS=true — omitiendo migraciones incrementales..."` o `"Schema existente detectado — migraciones incrementales aplicadas."`), y que no aparezca ningún traceback.
- El archivo de prueba temporal usado para simular los 3 escenarios se guardó en el scratchpad de la sesión (no en el repo), no queda residuo en el proyecto.
