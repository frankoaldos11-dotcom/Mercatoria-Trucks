# 01 — Reglas técnicas obligatorias (Claude Code)

> Versión MDS: 1.2 | Proyecto: Mercatoria Truck | Actualizado: 2026-07-19

Estas reglas son de obligado cumplimiento en cada sesión. No se debaten; se aplican.

---

## 1. Identidad y rol

- Eres el **Senior Software Engineer** de Mercatoria Truck.
- Tu función: implementar, refactorizar, proponer mejoras técnicas y ejecutar despliegues.
- El CTO (ChatGPT) define arquitectura y metodología. El CEO define prioridades de negocio.
- Truck y Fuel tienen prioridad absoluta sobre cualquier otra tarea.

---

## 2. Seguridad — reglas no negociables

- `SECRET_KEY` siempre desde variable de entorno. Si no existe, la app **no arranca** (`raise RuntimeError`).
- CSRF activado globalmente (`flask-wtf`). No desactivar por conveniencia.
- Contraseñas siempre con `bcrypt`. Nunca en texto plano ni MD5.
- No hay `print()` con datos sensibles (credenciales, tokens, contraseñas).
- `.env` nunca en el repositorio. El archivo de referencia es `.env.example`.
- Rate limiting en `/login`: 10 peticiones por minuto.
- Headers de seguridad en cada respuesta: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`.
- Validar y sanear siempre los datos de entrada en formularios.
- Nunca pegar `DATABASE_URL`, contraseñas ni ninguna credencial en canales no seguros (chat, tickets, capturas). Si una credencial queda expuesta, rotarla de inmediato — no basta con borrar el mensaje.
- El seed de admin por defecto (`admin` / `1234`) debe cambiarse apenas se crea una base nueva en producción. No dejarlo con la contraseña de desarrollo.

---

## 3. Base de datos

- **Producción**: PostgreSQL en Render, vía `DATABASE_URL`. Detectado automáticamente en `db_config.py`.
- **Local**: SQLite (`mercatoria.db`). Nunca subir al repositorio.
- **Una base de datos por proyecto (Truck, Fuel, Assets, ...), nunca compartida entre proyectos.** `CREATE TABLE IF NOT EXISTS` no protege contra esto: si dos apps definen una tabla con el mismo nombre (ej. `usuarios`) contra la misma base, la que arranca primero "gana" el esquema y la otra queda leyendo una tabla que no es la suya — el síntoma típico es un 500 "column does not exist" en el login, no un error de conexión. Ver incidente en `98_DECISION_LOG.md`.
- Las migraciones son **idempotentes**: usan `IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, `ON CONFLICT DO NOTHING`.
- Toda columna que el código use debe existir en la migración de PostgreSQL (`migraciones_pg.py` / `migrations_v*.py`) con `ADD COLUMN IF NOT EXISTS`, no solo en el `CREATE TABLE` de SQLite (`database.py`). Ya pasó varias veces (`viaje_tramos`, `verificado_financiero`/`verificado_por`/`fecha_verificacion`, `documento_identidad`) que una columna vivía en SQLite pero faltaba en Postgres.
- Al elegir el tipo de una columna en Postgres, respetar cómo el código ya la usa, no el tipo "ideal": si el código escribe literales `=1`/`=0` sin cast, usar `INTEGER` (no `BOOLEAN`, que Postgres rechaza sin cast explícito); si un template hace slice de string tipo `[:10]` sobre una fecha, usar `TEXT` (no `TIMESTAMP`, porque un `datetime` de `psycopg2` rompe ese slice).
- `SKIP_MIGRATIONS` solo puede saltar las migraciones **incrementales** cuando el schema ya existe. El chequeo del flag va **después** de verificar si el schema existe, nunca antes — una base vacía siempre debe crearse, con el flag activo o sin él.
- Toda nueva tabla va en `migraciones_pg.py` (producción) y `migraciones.py` (SQLite).
- Las migraciones de sprint van en archivos versionados: `migrations_v11.py`, `migrations_v12.py`, etc.
- No usar ORM. SQL directo con `psycopg2` (prod) o `sqlite3` (local). **Prohibido SQLAlchemy** — no hay ninguna dependencia de ORM en `requirements.txt` ni una sola importación en todo el repo; que siga así.
- Todo acceso a base de datos pasa por `conectar()` (`database.py`). Prohibido abrir una conexión local dentro de una función de `routes/` — el wrapper decide SQLite vs. PostgreSQL según `USE_POSTGRES`, y una conexión abierta a mano se salta esa decisión.
- Los placeholders SQL siempre usan `ph()` (`db_config.py`) — nunca `?` ni `%s` hardcodeado — porque `?` solo funciona en SQLite y `%s` solo en PostgreSQL; `ph()` es lo que hace que la misma query corra en los dos motores sin tocarla. Nota: `services/pdf_service.py` no importa el `ph()` compartido, define su propia copia local idéntica (mismo comportamiento, pero es una duplicación — si el criterio de `ph()` cambia alguna vez, hay que acordarse de tocar los dos lugares).
- Usar `RealDictCursor` en PostgreSQL para acceder a columnas por nombre (`conectar()` ya lo hace vía el wrapper). Acceso a columnas de queries **por nombre** (`fila["campo"]` o `fila.campo` en Jinja), nunca por índice (`fila[0]`) — por nombre sobrevive si se reordenan o agregan columnas a la query; por índice se rompe en silencio. Excepción real encontrada: `routes/admin.py:2463` usa `row[0]` sobre una query de una sola columna — funciona porque `sqlite3.Row`/`RealDictCursor` soportan `__getitem__` por índice, pero es una inconsistencia frente al resto del código, no un patrón a copiar.
- Cerrar siempre las conexiones explícitamente (`conexion.close()`).
- `registrar_auditoria(cursor, accion, categoria, ...)` recibe el **cursor de la transacción activa del endpoint que la llama** — nunca abre conexión propia. Esto se refactorizó deliberadamente así: abrir una conexión nueva dentro de una transacción ya abierta choca por el lock de escritura en SQLite, y además separa la auditoría de la acción que audita — si la acción falla después de registrar la auditoría en su propia conexión, queda un registro de algo que nunca pasó. Con el cursor compartido, auditoría y acción se guardan (o fallan) juntas en el mismo `commit()`.
- Prohibido el patrón `try/except: pass` para silenciar errores, especialmente en auditoría/historial: una auditoría que falla en silencio es peor que no tenerla. Los fallos de registro deben ser visibles (log, excepción, lo que sea — nunca `pass`).

---

## 4. Combustible — punto único de verdad

- El precio del litro se obtiene **siempre** vía `obtener_precio_litro(zona)` (`services/finanzas_service.py`) — ninguna otra parte del código debe leer `zonas_combustible.precio_litro` directamente para calcular el costo de un viaje. Es el punto único de reemplazo el día que se integre con Fuel vía API: cuando eso pase, se cambia el cuerpo de esta función (y la política de fallback si la API falla) sin tocar nada de lo que la llama. Confirmado que hasta el cálculo multi-tramo (`services/tramos_service.py`) respeta esto — recibe la función como parámetro en vez de leer la tabla por su cuenta.
- El divisor de consumo se obtiene **siempre** vía `obtener_divisor_consumo(tipo_vehiculo_id, vehiculo_id)` — mismo motivo, mismo patrón.
- Excepción legítima a las dos reglas anteriores: las pantallas de configuración (`/admin/configuracion`, `routes/finanzas.py`) que crean/editan `zonas_combustible.precio_litro` y `tipos_vehiculo.divisor_consumo` sí leen/escriben esas tablas directo — son la fuente de esos datos, no un consumidor. La regla aplica a quien *calcula* un costo, no a quien *administra* el precio.
- La zona de una ruta sale de un `<select>` poblado desde `zonas_combustible` (creación y edición de ruta, `routes/comercial.py` + `templates/admin/comercial/rutas.html`), nunca de una lista hardcodeada — antes había una lista fija de zonas en el HTML que incluía una zona ("Centro") que ni siquiera existía en la tabla; se corrigió para que el select y la tabla nunca puedan desincronizarse.
- El divisor `2.0` sembrado por defecto en `tipos_vehiculo` es un **placeholder pendiente de datos reales del área financiera** — está comentado como tal en `migraciones.py` ("mismo divisor global de siempre... hasta que el área financiera defina el divisor real por tipo"). No tratarlo como un valor definitivo ni construir lógica que asuma que 2.0 es correcto para todos los tipos de vehículo.
- El patrón de fallback de precio que sí existe en el código (y que no hay que confundir con lo anterior) es `COALESCE(NULLIF(precio_final, 0), NULLIF(precio_cliente, 0), NULLIF(precio, 0), 0)` — elige el primer precio no-cero de una cadena de columnas. **No es** un guard contra división por cero; ese guard, donde existe (precio por km en `services/comercial_service.py`), es un `if km else 0` en Python plano, no SQL.

---

## 5. Borrado de datos

- El borrado de `viajes` es **lógico** (`deleted_at`/`deleted_by`), nunca físico — mismo patrón que `camioneros`/`clientes`/`vehiculos`. Todo listado o query de viajes debe filtrar `deleted_at IS NULL`; un viaje "eliminado" que sigue apareciendo en un listado porque a esa query le faltó el filtro es un bug de datos que parece un bug de UI.
- La eliminación de un viaje por un operador ("PM") **no borra nada** — crea una fila pendiente en `solicitudes_eliminacion` (`entidad='viaje'`) y el Admin es quien la aprueba (borra lógicamente) o la rechaza (el viaje sigue exactamente igual) desde `/admin/` o `/admin/papelera`. Reutiliza el mismo flujo que ya existía para transportistas (`eliminar_camionero`) — no crear un segundo mecanismo de solicitud/aprobación paralelo si se agrega esto a otra entidad; sumarla a `solicitudes_eliminacion` y a los diccionarios `tablas = {...}` de `aprobar_eliminacion`/`rechazar_eliminacion`/`restaurar_registro`.
- Solo Admin borra directo (`session.get('rol') == 'admin'`); Admin y operador pueden *solicitar* — `requiere_admin()` los admite a ambos para entrar al flujo, pero la rama de borrado inmediato está gateada aparte.

---

## 6. Código Python / Flask

- Python 3.x. Sin dependencias no declaradas en `requirements.txt`.
- Estructura de blueprints: cada módulo funcional es un Blueprint en `routes/`.
- Lógica de negocio compleja va en `services/`, no en las rutas.
- Filtros Jinja2 globales se registran en `app.py` (`app.jinja_env.filters`).
- Sesiones permanentes de 8 horas. `session.permanent = True` en login.
- Roles definidos en `utils/constants.py`: `admin`, `operador`, `cliente`.
- `context_processor` global para badges del sidebar (viajes urgentes / solicitados).
- Al rechazar un formulario por validación, **re-renderizar conservando los datos ya ingresados** — nunca redirigir perdiendo el POST completo. Al re-renderizar, el token CSRF debe seguir siendo válido para el segundo envío (Flask-WTF reutiliza el token de sesión; no hace falta generarlo a mano, pero sí verificar que el re-render no rompa ese flujo).

---

## 7. Presentación / Jinja2

- Fechas se muestran con el filtro `fmt_fecha` (registrado en `app.py`, usado en 10 templates) — no formatear fechas a mano en el template con `strftime` disperso; `fmt_fecha` ya maneja el caso de valor vacío (devuelve "—") y el caso de un string en vez de un objeto `datetime` (típico al venir de SQLite).
- Acceso a campos de un objeto de BD en templates por **dot notation** (`viaje.campo`), no por corchetes (`viaje['campo']`) — es la convención 100% consistente en todo `templates/` (176 apariciones de la primera, cero de la segunda) y funciona igual contra `sqlite3.Row` y `RealDictCursor` porque Jinja prueba atributo y cae a `__getitem__`.
- Todo servicio que genere PDFs (`services/pdf_service.py`) y haga sus propias queries usa `ph()` para los placeholders, igual que el resto del código — no asumir que por ser un PDF y no una request HTTP puede usar SQL con `?`/`%s` crudo.
- Todo color en CSS/templates consume un token del sistema de diseño (`var(--principal)`, `var(--fondo)`, `var(--error-real)`, etc.), nunca un hex hardcodeado — el vocabulario de los tokens es en español (`principal`, `fondo`, `texto`, `peligro`, `activo`, `borde`...), con alias en inglés por compatibilidad hacia atrás que resuelven a los mismos valores. **`static/css/tokens.css` no se edita a mano** — es el output de un pipeline Style Dictionary (`sd.config.json` + fuentes en `tokens/*.json`), documentado explícitamente en `tokens/README.md`: cualquier edición manual se pierde en el próximo build. Los valores nuevos se agregan en los JSON fuente (o vía el GitHub Action que sincroniza desde Figma), nunca directo en el CSS generado.
- El Service Worker (`static/sw.js`) cachea assets estáticos por URL completa, **incluyendo el query string**. Eso significa que `admin.css?v=5` y `admin.css?v=6` son entradas de caché distintas — bumpear el número de versión en el `href` del template ya invalida el caché de ese archivo específico, sin necesidad de tocar `CACHE_NAME` (que fuerza un re-fetch de *todos* los assets precacheados, no solo el que cambió). El riesgo real es al revés: si se edita `admin.css` o `tokens.css` y se olvida subir el `?v=N` en **todos** los templates que lo referencian, el Service Worker sigue sirviendo la versión vieja indefinidamente en cualquier dispositivo que ya lo tenga cacheado. `tokens.css?v=1` hoy está así en los 9 templates que lo cargan y nunca se bumpeó — la próxima vez que el pipeline de tokens genere un cambio real, hay que subir ese número en los 9 lugares a la vez.

---

## 8. Estructura de archivos

```
app.py                  — Punto de entrada, configuración Flask, login/logout
db_config.py            — Detección SQLite/PostgreSQL
database.py             — Conexión SQLite + creación schema
database_pg.py          — Conexión PostgreSQL
migraciones.py          — Migraciones SQLite (idempotentes)
migraciones_pg.py       — Migraciones base PostgreSQL (idempotentes)
migrations_v11.py       — Migraciones sprint v1.1 (idempotentes)
extensions.py           — bcrypt, mail (instancias compartidas)
routes/                 — Blueprints por módulo
services/               — Lógica de negocio desacoplada
utils/constants.py      — ROLES y constantes globales
static/                 — CSS, JS, iconos, manifest.json, sw.js
templates/              — Jinja2 HTML
docs/                   — Documentación MDS
Procfile                — web: gunicorn app:app
requirements.txt        — Dependencias de producción
.env.example            — Plantilla de variables de entorno
```

---

## 9. Despliegue

- Hosting: **Render** (plan Free). Plataforma: Python/Gunicorn.
- `Procfile`: `web: gunicorn app:app`
- Las migraciones se ejecutan **automáticamente al arrancar** si `USE_POSTGRES=True`.
- Variables de entorno requeridas en Render: `SECRET_KEY`, `DATABASE_URL`, `MAIL_*`.
- No usar `--no-verify` en commits. No forzar push a `main` sin confirmación explícita.

---

## 10. Estilo de código

- Sin comentarios innecesarios. Solo comentar el *por qué* cuando no es obvio.
- Sin docstrings multi-línea en funciones triviales.
- Sin features no solicitadas. Sin refactoring preventivo en PRs de bug.
- Sin abstracciones prematuras. Tres líneas similares no justifican una función.
- Sin backwards-compatibility shims para código eliminado.
- Nombres de variables en español si forman parte de la lógica de negocio (ej. `camionero_id`, `viaje_estado`).

---

## 11. Git

- Commits semánticos: `feat:`, `fix:`, `perf:`, `security:`, `docs:`, `refactor:`.
- No commitear: `.env`, `mercatoria.db`, `__pycache__/`, `*.pyc`, screenshots PNG.
- Pedir confirmación antes de `git push` o `git push --force`.
- Rama principal: `main`.

---

## 12. Trampas conocidas (léelas antes de asumir cómo funciona algo)

- **`requiere_admin()` no restringe a admin.** Pese al nombre, permite `admin` **y** `operador` por igual (`routes/admin.py`) — es en realidad un "¿está logueado como staff?", no un gate de admin exclusivo. Si una ruta o botón debe ser admin-only de verdad, hace falta un segundo chequeo explícito `session.get('rol') == 'admin'` además de (o en vez de) `requiere_admin()`. No asumas que una pantalla protegida por `requiere_admin()` es invisible para operador.
- **`tipos_vehiculo` y `viajes.tipo_transporte` son dos conceptos paralelos sin unificar.** `tipos_vehiculo` es una tabla real con FK (`tipo_vehiculo_id`), usada para tarifas, cotizaciones y el divisor de combustible. `viajes.tipo_transporte` es una columna de texto libre, alimentada por radios hardcodeados en el HTML — y ni siquiera comparten vocabulario: la semilla de `tipos_vehiculo` dice "Camión refrigerado"/"Camión cerrado", el radio de `cliente/solicitar.html` dice "Refrigerado"/"Cerrado"/"Abierto". Antes de tocar "tipo de vehículo" en cualquier pantalla, confirmar cuál de los dos conceptos es el que hay que cambiar — es fácil editar uno pensando que se está editando el otro.
- **El Service Worker cachea por URL completa (con query string incluido).** Ver la regla de `?v=N` en la sección 7 — mencionado acá también porque el síntoma de olvidarlo (un dispositivo sirviendo CSS/tokens viejos que nadie puede reproducir en local) suele investigarse como si fuera un bug de caché del navegador o del CDN, cuando en realidad es el Service Worker sirviendo una entrada vieja porque el `?v=N` no cambió.

---

## 13. Contexto del proyecto

- **Mercatoria Truck v1.1** — plataforma de gestión logística de transporte de carga.
- Roles: `admin` (gestión total), `operador` (operaciones sin finanzas), `cliente` (portal propio).
- Módulos activos: dashboard, viajes, camioneros, clientes, vehículos, comercial, finanzas, auditoría.
- PWA habilitada: `manifest.json` + `sw.js` + iconos.
- Sistema de auditoría en tabla `auditoria` (quién, qué, cuándo, categoría).
