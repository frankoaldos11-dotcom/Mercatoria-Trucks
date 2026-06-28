# 98 — Decision Log

> Registro de decisiones técnicas y de arquitectura tomadas durante el desarrollo.
> Formato: fecha — decisión — alternativas consideradas — razón.

---

## 2026-Q2 — v1.1

### No usar ORM (SQLAlchemy / Django ORM)
**Decisión**: SQL directo con `psycopg2` y `sqlite3`.
**Alternativas**: SQLAlchemy Core, SQLAlchemy ORM, Django ORM.
**Razón**: Control total sobre queries, migraciones simples sin estado de ORM, sin magia implícita que complique el debug, suficiente para la escala actual. El coste de aprender SQLAlchemy no se justifica en este momento.

---

### Migraciones en scripts Python versionados (no Alembic / Flask-Migrate)
**Decisión**: `migraciones.py`, `migraciones_pg.py`, `migrations_v11.py` — scripts idempotentes ejecutados al arrancar.
**Alternativas**: Alembic, Flask-Migrate.
**Razón**: Sin dependencias extra, fácil de auditar en git, idempotentes por diseño (no hay "estado de migración" que perder). Alembic añade complejidad operacional innecesaria para un equipo pequeño.

---

### SQLite en local / PostgreSQL en producción
**Decisión**: Detectar automáticamente con `DATABASE_URL` en `db_config.py`.
**Alternativas**: PostgreSQL local para desarrollo, Docker Compose.
**Razón**: Desarrollo sin dependencias externas (sin Docker, sin PostgreSQL local). El coste: algunas diferencias SQLite/PostgreSQL requieren atención (tipos de datos, funciones de fecha). Documentadas en `migraciones.py`.

---

### Sin frontend framework (Vanilla JS + Jinja2)
**Decisión**: HTML/CSS/JS puro renderizado en servidor con Jinja2.
**Alternativas**: React, Vue, HTMX.
**Razón**: Sin build step, sin complejidad de SPA, carga directa, suficiente para la escala y velocidad de desarrollo actual. Si la complejidad del UI crece significativamente, reconsiderar HTMX como siguiente paso.

---

### CSRF activado globalmente con flask-wtf
**Decisión**: `WTF_CSRF_ENABLED = True` en toda la app.
**Alternativas**: CSRF selectivo por ruta, SameSite cookies.
**Razón**: Seguridad por defecto. Un formulario sin CSRF es un bug de seguridad. El coste (añadir `{{ form.hidden_tag() }}` o el token en JS) es menor al riesgo.

---

### Rate limiting en memoria (no Redis)
**Decisión**: `storage_uri="memory://"` en flask-limiter.
**Alternativas**: Redis (más preciso, persiste entre reinicios).
**Razón**: Render Free no incluye Redis. La limitación (se resetea al reiniciar el servidor) es aceptable para el volumen actual. Migrar a Redis cuando haya plan de pago.

---

### Migraciones v1.1 se ejecutan siempre al arrancar (ignorando SKIP_MIGRATIONS)
**Decisión**: `migrations_v11.py` no respeta `SKIP_MIGRATIONS`.
**Alternativas**: Respetar la variable, requerir ejecución manual.
**Razón**: Las migraciones son idempotentes — re-ejecutar no daña nada. Garantiza que producción esté siempre al día sin pasos manuales. Si hay un caso donde no se quieren ejecutar, se comenta la importación en `app.py`.

---

### Checklist de viaje generado automáticamente al crear el viaje
**Decisión**: Al insertar un viaje, se insertan automáticamente los ítems del checklist estándar en `viaje_checklist`.
**Alternativas**: Checklist manual por el operador, checklist configurable.
**Razón**: Consistencia operativa. Todos los viajes tienen los mismos controles. El catálogo de ítems puede evolucionar en futuras versiones.

---

### Permisos por rol implementados en las rutas (decoradores / checks manuales)
**Decisión**: Verificar `session["rol"]` al inicio de cada función de ruta.
**Alternativas**: Decorador personalizado `@requiere_rol("admin")`, Flask-Login + roles.
**Razón**: Explícito y trazable. Un decorador oculta la lógica. En el nivel actual de complejidad, la verificación directa es más legible. Candidato a refactorizar en v1.2.

---

## 2025-Q4 — v1.0

### Render como hosting (plan Free)
**Decisión**: Render Free Tier.
**Alternativas**: Railway, Fly.io, Heroku (de pago), VPS propio.
**Razón**: Despliegue desde GitHub sin configuración de servidor, SSL gratuito, suficiente para la fase de validación. Limitación: el servidor "duerme" tras 15 min de inactividad (primer request lento). Aceptable para fase de desarrollo.

### Neon como PostgreSQL
**Decisión**: Neon Free Tier.
**Alternativas**: Supabase, Railway PostgreSQL, ElephantSQL, Render PostgreSQL (de pago).
**Razón**: Plan gratuito generoso, branching de BD (útil para dev), buena compatibilidad con psycopg2. Limitación: **instancias free expiran** — atención al vencimiento.
