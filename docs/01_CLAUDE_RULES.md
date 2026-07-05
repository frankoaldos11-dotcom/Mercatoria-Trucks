# 01 — Reglas técnicas obligatorias (Claude Code)

> Versión MDS: 1.1 | Proyecto: Mercatoria Truck | Actualizado: 2026-07-05

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
- No usar ORM. SQL directo con `psycopg2` (prod) o `sqlite3` (local).
- Usar `RealDictCursor` en PostgreSQL para acceder a columnas por nombre.
- Cerrar siempre las conexiones explícitamente (`conexion.close()`).
- Las funciones de registro (historial, auditoría) reciben el cursor de la transacción activa como parámetro — nunca abren conexión propia. Abrir una conexión nueva dentro de una transacción ya abierta choca por el lock de escritura en SQLite.
- Prohibido el patrón `try/except: pass` para silenciar errores, especialmente en auditoría/historial: una auditoría que falla en silencio es peor que no tenerla. Los fallos de registro deben ser visibles (log, excepción, lo que sea — nunca `pass`).

---

## 4. Código Python / Flask

- Python 3.x. Sin dependencias no declaradas en `requirements.txt`.
- Estructura de blueprints: cada módulo funcional es un Blueprint en `routes/`.
- Lógica de negocio compleja va en `services/`, no en las rutas.
- Filtros Jinja2 globales se registran en `app.py` (`app.jinja_env.filters`).
- Sesiones permanentes de 8 horas. `session.permanent = True` en login.
- Roles definidos en `utils/constants.py`: `admin`, `operador`, `cliente`.
- `context_processor` global para badges del sidebar (viajes urgentes / solicitados).
- Al rechazar un formulario por validación, **re-renderizar conservando los datos ya ingresados** — nunca redirigir perdiendo el POST completo. Al re-renderizar, el token CSRF debe seguir siendo válido para el segundo envío (Flask-WTF reutiliza el token de sesión; no hace falta generarlo a mano, pero sí verificar que el re-render no rompa ese flujo).

---

## 5. Estructura de archivos

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

## 6. Despliegue

- Hosting: **Render** (plan Free). Plataforma: Python/Gunicorn.
- `Procfile`: `web: gunicorn app:app`
- Las migraciones se ejecutan **automáticamente al arrancar** si `USE_POSTGRES=True`.
- Variables de entorno requeridas en Render: `SECRET_KEY`, `DATABASE_URL`, `MAIL_*`.
- No usar `--no-verify` en commits. No forzar push a `main` sin confirmación explícita.

---

## 7. Estilo de código

- Sin comentarios innecesarios. Solo comentar el *por qué* cuando no es obvio.
- Sin docstrings multi-línea en funciones triviales.
- Sin features no solicitadas. Sin refactoring preventivo en PRs de bug.
- Sin abstracciones prematuras. Tres líneas similares no justifican una función.
- Sin backwards-compatibility shims para código eliminado.
- Nombres de variables en español si forman parte de la lógica de negocio (ej. `camionero_id`, `viaje_estado`).

---

## 8. Git

- Commits semánticos: `feat:`, `fix:`, `perf:`, `security:`, `docs:`, `refactor:`.
- No commitear: `.env`, `mercatoria.db`, `__pycache__/`, `*.pyc`, screenshots PNG.
- Pedir confirmación antes de `git push` o `git push --force`.
- Rama principal: `main`.

---

## 9. Contexto del proyecto

- **Mercatoria Truck v1.1** — plataforma de gestión logística de transporte de carga.
- Roles: `admin` (gestión total), `operador` (operaciones sin finanzas), `cliente` (portal propio).
- Módulos activos: dashboard, viajes, camioneros, clientes, vehículos, comercial, finanzas, auditoría.
- PWA habilitada: `manifest.json` + `sw.js` + iconos.
- Sistema de auditoría en tabla `auditoria` (quién, qué, cuándo, categoría).
