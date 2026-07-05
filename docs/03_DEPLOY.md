# 03 — Despliegue (Deploy)

> Versión MDS: 1.1 | Proyecto: Mercatoria Truck | Actualizado: 2026-07-05

---

## Infraestructura actual

| Componente | Proveedor | Plan | Notas |
|---|---|---|---|
| Hosting app | Render | Free | `web: gunicorn app:app` |
| Base de datos | Render PostgreSQL — `mercatoria-truck-db` | Basic (de pago) | Base propia de Truck, separada de Fuel. No expira (plan de pago). |
| Repositorio | GitHub | Free | Rama `main` = producción |
| Dominio | Render subdomain | — | `*.onrender.com` |

> **Corrección de infraestructura (2026-07-05):** este MDS documentaba la base de producción como Neon PostgreSQL, expirando el 2026-07-26. Eso ya no es así — producción corre sobre PostgreSQL de Render. Truck y Fuel llegaron a compartir una sola base gratuita de Render (`mercatoria-db`), lo cual causó un incidente real (ver `98_DECISION_LOG.md`); la corrección fue separar Truck a su propia base `mercatoria-truck-db` en plan Basic de pago, dejando `mercatoria-db` para Fuel. **A confirmar**: fecha exacta del cambio de proveedor Neon → Render, y si `mercatoria-db` (Fuel) sigue en plan Free con expiración propia.

---

## Variables de entorno en Render

Configurar en: Render Dashboard → Mercatoria Truck → Environment

| Variable | Descripción | Obligatoria |
|---|---|---|
| `SECRET_KEY` | Clave Flask (mín. 32 chars hex) | Sí — la app no arranca sin ella |
| `DATABASE_URL` | PostgreSQL connection string de `mercatoria-truck-db` (Render) | Sí |
| `SKIP_MIGRATIONS` | `true` para saltar las migraciones **incrementales** al arrancar — solo tiene efecto si el schema ya existe; contra una base vacía, el schema completo se crea siempre, ignorando el flag (ver "Migraciones" más abajo) | No (default: false) |
| `MAIL_SERVER` | SMTP server (default: smtp.gmail.com) | No |
| `MAIL_PORT` | Puerto SMTP (default: 587) | No |
| `MAIL_USERNAME` | Cuenta de correo | No |
| `MAIL_PASSWORD` | App password de Gmail | No |
| `MAIL_DEFAULT_SENDER` | Remitente por defecto | No |

Generar `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Flujo de despliegue

Render despliega automáticamente al hacer push a `main`.

```
git add <archivos>
git commit -m "tipo: descripción concisa"
git push origin main
```

Render ejecuta automáticamente:
1. `pip install -r requirements.txt`
2. `gunicorn app:app` (vía Procfile)
3. Al arrancar: migraciones PostgreSQL idempotentes

---

## Primer despliegue en un entorno nuevo

1. Conectar el repositorio GitHub en Render.
2. Crear la base de datos PostgreSQL **propia de este proyecto** (nunca reutilizar la base de otro proyecto Mercatoria). Render Free solo permite **una base de datos gratis por cuenta** — si ya hay otro proyecto usando la base free, este necesita plan de pago (Basic, ~$6/mes). Al crearla, revisar el storage por defecto (Render asigna 15 GB extra) y bajarlo al mínimo si el proyecto arranca vacío.
3. Configurar todas las variables de entorno obligatorias.
4. Hacer deploy manual (o push a `main`).
5. Verificar logs de Render: sin errores en migraciones.
6. Acceder a `/login` → HTTP 200.
7. Crear usuario admin desde Render Shell si la BD está vacía:
   ```python
   python -c "
   from app import app
   from database_pg import conectar_pg
   from extensions import bcrypt
   with app.app_context():
       conn = conectar_pg()
       cur = conn.cursor()
       h = bcrypt.generate_password_hash('PASSWORD').decode()
       cur.execute(\"INSERT INTO usuarios (usuario, password, rol) VALUES ('admin', %s, 'admin')\", (h,))
       conn.commit()
       conn.close()
   print('Admin creado')
   "
   ```
8. **Cambiar de inmediato la contraseña default del admin** (`migraciones_pg.py` siembra `admin` / `1234` en el schema nuevo si no se crea uno manualmente en el paso anterior). No dejarla así en producción.

---

## Migraciones

### Comportamiento automático
- `USE_POSTGRES=True` (cuando `DATABASE_URL` está definida):
  1. `migraciones_pg.py` → verifica primero si el schema existe. Si **no** existe, lo crea completo (ignora `SKIP_MIGRATIONS` — una base vacía siempre debe arrancar con su schema). Si **sí** existe, recién ahí se respeta `SKIP_MIGRATIONS` para saltar las columnas/tablas incrementales.
  2. `migrations_v11.py`, `migrations_v12.py` → columnas y tablas de sprint, siempre corren (no respetan `SKIP_MIGRATIONS` — son idempotentes por diseño, ver `98_DECISION_LOG.md`).

- `USE_POSTGRES=False` (local con SQLite):
  1. `database.py::crear_base_datos()` → schema base
  2. `migraciones.py` → migraciones SQLite

### Ejecución manual desde Render Shell
```bash
python migrations_v11.py
```

### Añadir nueva migración de sprint
1. Crear `migrations_v12.py` con el patrón de `migrations_v11.py`.
2. Importar y llamar en `app.py` junto a las anteriores.
3. La migración debe ser idempotente.
4. Toda columna nueva que use SQLite (`database.py` / `migraciones.py`) debe reflejarse también en Postgres (`migraciones_pg.py` o el `migrations_v*.py` correspondiente) con `ADD COLUMN IF NOT EXISTS` — nunca solo en un lado.

### Auditoría periódica del esquema
No esperar a que algo revienta en producción para revisar el esquema. Cada cierto tiempo, comparar columna por columna lo que espera el código (`SELECT`/`INSERT` en `routes/`, `services/`) contra lo que realmente existe en la Postgres de producción (`information_schema.columns`). Ya pasó más de una vez que una columna existía en SQLite pero no en Postgres y solo se detectó cuando falló en vivo.

---

## Desarrollo local

```bash
# 1. Clonar
git clone https://github.com/<org>/mercatoria-truck.git
cd mercatoria-truck

# 2. Entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
copy .env.example .env
# Editar .env con SECRET_KEY (y DATABASE_URL si usas PostgreSQL local)

# 5. Arrancar
python app.py
# → http://127.0.0.1:5000
```

Sin `DATABASE_URL` → usa SQLite (`mercatoria.db`). La BD se crea sola al primer arranque.

---

## Rollback

Render mantiene historial de deploys. En caso de fallo:
1. Render Dashboard → Deploys → seleccionar deploy anterior → "Redeploy".
2. Si el fallo es de migración: conectar a Render Shell y revertir manualmente la columna/tabla problemática.

---

## Checklist post-despliegue

- [ ] Render logs sin errores 500 ni excepciones Python
- [ ] `/login` responde HTTP 200
- [ ] Login admin funciona → dashboard carga
- [ ] Login cliente funciona → portal carga
- [ ] Crear viaje de prueba → asignar camionero → cambiar estado
- [ ] PWA: favicon visible, `manifest.json` accesible
