# Reporte de Pruebas — 2026-07-03

## Contexto
Commit de esta sesión: **vincular usuario cliente a su ficha de cliente desde el admin, y crear cliente desde la pantalla de "Nuevo usuario"** ("Vincular usuario cliente a su ficha desde admin + crear cliente desde pantalla de usuario"), pendiente de push al cierre de este reporte.

**⚠️ La verificación con Playwright de este commit NO se completó** — se documenta al final por qué, y queda pendiente de verificación manual en producción por Aldo.

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

## Problema que resuelve este commit
Investigación previa (misma sesión) encontró que la única forma de vincular un usuario con rol "cliente" a su ficha de `clientes` (columna `clientes.usuario_id`) era el autoregistro del propio cliente en `/cliente/registro`. El admin no tenía ninguna vía para producir ese vínculo — ni desde "Nuevo usuario" (el select ni existía), ni desde "Clientes" (`admin_clientes()` no escribe `usuario_id`). Consecuencia real: un admin que crea manualmente un usuario rol cliente para un cliente institucional (PMA, WFP, Cáritas, etc.) le deja el portal completamente vacío, porque todas las consultas de `routes/cliente.py` filtran por `clientes.usuario_id`.

## Cambios implementados

**`database.py`** — se agregó la propiedad `rowcount` a `CursorWrapper` (pass-through a `self._cursor.rowcount`). No existía; es necesaria para el UPDATE condicional atómico que se describe abajo.

**`routes/admin.py`**:
- Se extrajo `_validar_y_crear_cliente(cursor, form)`, con la misma validación de email/documento duplicado e INSERT que ya tenía `admin_clientes()` — ahora ambos flujos (el formulario normal de "Clientes" y el nuevo endpoint rápido) reutilizan la misma función, sin duplicar la validación.
- Nuevo endpoint `POST /admin/clientes/crear-rapido`: crea un cliente vía AJAX (JSON), protegido con `requiere_admin()` (mismo nivel de permiso que `admin_clientes`), con `registrar_auditoria()` propio.
- `lista_usuarios()` (GET `/admin/usuarios`) ahora también consulta `clientes_sin_usuario` (`WHERE usuario_id IS NULL AND deleted_at IS NULL`) y se la pasa al template.
- `crear_usuario()`: si `rol == "cliente"`, exige `cliente_id`; valida que el cliente exista; crea el usuario; **vincula con `UPDATE clientes SET usuario_id = ? WHERE id = ? AND usuario_id IS NULL`** y verifica `cursor.rowcount`. Si el rowcount es 0 (otro admin vinculó ese cliente en el intervalo), no se comitea nada — ni el usuario ni el update quedan persistidos, evitando el usuario huérfano. Todo en una sola transacción/conexión. Auditoría con el detalle del vínculo.

**`templates/admin/usuarios.html`**:
- Campo "Cliente vinculado *" (select, oculto salvo rol=cliente, con `required` alternado por JS) que lista solo clientes sin usuario asociado.
- Botón "+ Nuevo cliente" que abre un modal Bootstrap (mismo patrón ya usado en `clientes.html` para importar Excel) con campos mínimos (nombre*, empresa, teléfono, email, documento).
- El modal guarda vía `fetch()` + `FormData` (mismo patrón AJAX ya usado en `gestionar_viaje.html`) contra el nuevo endpoint, inyecta la opción nueva en el select ya seleccionada, y se cierra sin recargar la página — así no se pierde lo ya escrito en email/contraseña/rol del formulario principal.

## Verificación realizada
- `py_compile` de `routes/admin.py` y `database.py`: OK.
- Verificación de sintaxis Jinja de `templates/admin/usuarios.html` (parseo con `jinja2.Environment`): OK.
- Arranque de la app local (`python app.py`): sin tracebacks en el log (`Debugger PIN` normal, ninguna excepción).
- Fixture de prueba creado y luego eliminado (cliente "Test PMA Cuba" sin `usuario_id`, id temporal, ya borrado de `mercatoria.db`).

## ⚠️ Verificación con Playwright — NO completada
Al intentar navegar a `/login` para iniciar la verificación end-to-end, la llamada de Playwright quedó sin responder y Aldo interrumpió la sesión manualmente. El log de Flask (`/tmp/flask_cliente_vinculado.log`) no muestra ningún traceback ni error — el servidor arrancó limpio y quedó escuchando en el puerto 5000 (`Debugger PIN: 768-020-502`), así que el problema fue específicamente en la herramienta de automación del navegador, no en el servidor ni en el código.

**Queda pendiente que Aldo verifique manualmente en producción:**
1. Crear un usuario rol "cliente" vinculándolo a un cliente existente sin usuario → confirmar que `clientes.usuario_id` queda escrito y que ese cliente ve sus datos al loguearse en el portal.
2. Intentar crear un usuario rol "cliente" sin seleccionar cliente → debe bloquearlo con mensaje claro, sin crear el usuario.
3. Usar "+ Nuevo cliente" desde la pantalla de "Nuevo usuario" → el cliente se crea, queda seleccionado automáticamente, y los datos ya escritos de email/contraseña/rol no se pierden.
4. Crear un usuario rol admin u operador → debe seguir funcionando igual, sin pedir cliente vinculado.
5. (Condición de carrera, más difícil de probar manualmente pero documentada): si dos intentos de vinculación al mismo cliente casi simultáneos ocurrieran, el segundo debe fallar con "Ese cliente ya fue vinculado por otro usuario, intenta de nuevo" y no dejar un usuario huérfano — esto está cubierto por el `UPDATE ... WHERE usuario_id IS NULL` + chequeo de `rowcount` dentro de la misma transacción, pero no se ejecutó una prueba de concurrencia real.

## Páginas y funcionalidad NO probadas en esta sesión
- La pantalla `/admin/usuarios` con el nuevo campo y modal no se abrió ni una vez en el navegador.
- El portal cliente (`/cliente/...`) no se verificó tras un vínculo nuevo.

## Recomendaciones
- Antes de dar por cerrado este commit, correr la lista de verificación de arriba en producción (o repetirla localmente con Playwright cuando la herramienta de automación responda con normalidad).
- Si el problema de Playwright se repite, revisar si es un problema puntual de la extensión/tab del navegador (reiniciar la sesión de Chrome) antes de asumir que es un problema del código — el arranque del servidor fue limpio.
