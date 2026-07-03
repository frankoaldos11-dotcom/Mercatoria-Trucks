# Reporte de Pruebas — 2026-07-03

## Contexto
Commit probado en esta sesión: **elimina `conectar()` local de `migraciones.py`** ("Elimina conectar() local de migraciones.py, usa conexión centralizada"), pendiente de push al cierre de este reporte.

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

## Corrección aplicada
`migraciones.py`: se eliminó el `import sqlite3`, el `DATABASE_NAME` local y el `def conectar()` propio (que hacía `sqlite3.connect()` directo). Se reemplazó por `from database import conectar`, el conector centralizado del proyecto. Sin cambios en `tabla_existe`, `columna_existe`, `agregar_columna` ni en la lógica de `ejecutar_migraciones()` — solo cambia el origen de la conexión. Este archivo solo se invoca en la rama SQLite de `app.py` (`else:` del `if USE_POSTGRES:`), así que el `row_factory=sqlite3.Row` del conector centralizado (idéntico al que tenía el conector local) garantiza que `columna_existe()` (que accede a `col["name"]`) siga funcionando igual.

## Hallazgo reportado — deuda técnica (NO implementada en este commit, solo documentada)

**Riesgo:** `ejecutar_migraciones_pg()` (`migraciones_pg.py:12-23`) chequea `SKIP_MIGRATIONS` **antes** de verificar si el schema existe. Si se arranca contra una Postgres **vacía** (sin tabla `usuarios`) con `SKIP_MIGRATIONS=true`, la función retorna de inmediato sin crear ninguna tabla base (`usuarios`, `viajes`, `clientes`, `rutas`, etc.) — la única rama del código que crea esas tablas desde cero. `migrations_v11.py`/`migrations_v12.py` corren después igualmente (ignoran el flag), pero solo hacen `ALTER TABLE`/`CREATE TABLE IF NOT EXISTS` sobre tablas específicas; si las tablas base no existen, esos `ALTER TABLE` fallan silenciosamente (cada uno con su propio try/except que hace rollback y continúa). Resultado: **base de datos a medio crear, en silencio, sin ningún error visible en el arranque** — la app luego falla en cualquier página que toque la base ("relation does not exist").

**Mitigación propuesta (pendiente de implementar en un prompt aparte):** mover el chequeo de `SKIP_MIGRATIONS` para que ocurra **después** de la verificación de "¿existe el schema?" (la query `SELECT COUNT(*) FROM information_schema.tables WHERE table_name='usuarios'`), de modo que:
- Si el schema no existe → siempre se crea completo, sin importar el flag.
- Si el schema ya existe → el flag puede seguir usándose para saltar el chequeo incremental de columnas nuevas (comportamiento actual, ya usado como optimización de arranque).

**Prioridad:** alta — mismo tipo de bug de familia que ya causó los incidentes de `viaje_tramos` y las 4 columnas de verificación financiera, pero a nivel de bootstrap completo en vez de columnas sueltas. Bajo riesgo de ocurrencia inmediata (requiere una Postgres vacía + el flag ya activo), pero alto impacto si ocurre (app completamente no funcional).

## Páginas probadas
- Arranque completo de la app (SQLite local) vía `python app.py`
- `/login` → `/admin/` (dashboard) tras iniciar sesión

## Errores encontrados
Ninguno. 0 errores de consola, sin tracebacks en el log del servidor.

## Screenshots tomados
- Captura del Dashboard tras iniciar sesión, confirmando arranque normal de la app post-refactor — eliminada al finalizar la sesión (gitignored, `*.png`).

## Validaciones funcionales verificadas

| # | Verificación | Resultado esperado | Estado |
|---|---|---|---|
| 1 | Arranque contra la base SQLite existente (`mercatoria.db`) | Sin errores de migración | ✅ |
| 2 | Esquema resultante (23 tablas, mismas columnas) comparado antes/después del refactor | Idéntico — 0 tablas nuevas, 0 tablas perdidas, 0 diferencias de columnas | ✅ |
| 3 | Arranque desde una base SQLite completamente nueva (`crear_base_datos` + `ejecutar_migraciones()`) | Se crean las 23 tablas sin excepciones | ✅ |
| 4 | Login y carga del Dashboard tras el refactor | Funciona normalmente | ✅ |
| — | Sin errores de consola ni tracebacks de servidor | — | ✅ |

## Recomendaciones
- Retomar la mitigación de `SKIP_MIGRATIONS` documentada arriba en un prompt aparte, tal como se acordó — no se tocó el flag en este commit.
- El archivo de prueba SQLite temporal creado para la verificación de "arranque desde cero" fue eliminado; no quedan residuos en `mercatoria.db`.
