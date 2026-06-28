# 03 — Despliegue (Deploy)

> Versión MDS: 1.0 | Proyecto: Mercatoria Truck | Actualizado: 2026-06-28

---

## Infraestructura actual

| Componente | Proveedor | Plan | Notas |
|---|---|---|---|
| Hosting app | Render | Free | `web: gunicorn app:app` |
| Base de datos | Neon (PostgreSQL 16) | Free | Expira **2026-07-26** |
| Repositorio | GitHub | Free | Rama `main` = producción |
| Dominio | Render subdomain | — | `*.onrender.com` |

> **ALERTA**: La instancia de PostgreSQL en Neon expira el **2026-07-26**. Renovar o migrar antes de esa fecha.

---

## Variables de entorno en Render

Configurar en: Render Dashboard → Mercatoria Truck → Environment

| Variable | Descripción | Obligatoria |
|---|---|---|
| `SECRET_KEY` | Clave Flask (mín. 32 chars hex) | Sí — la app no arranca sin ella |
| `DATABASE_URL` | PostgreSQL connection string de Neon | Sí |
| `SKIP_MIGRATIONS` | `true` para saltar migraciones al arrancar | No (default: false) |
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
2. Configurar todas las variables de entorno obligatorias.
3. Hacer deploy manual (o push a `main`).
4. Verificar logs de Render: sin errores en migraciones.
5. Acceder a `/login` → HTTP 200.
6. Crear usuario admin desde Render Shell si la BD está vacía:
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

---

## Migraciones

### Comportamiento automático
- `USE_POSTGRES=True` (cuando `DATABASE_URL` está definida):
  1. `migraciones_pg.py` → schema base
  2. `migrations_v11.py` → columnas y tablas del sprint v1.1

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
