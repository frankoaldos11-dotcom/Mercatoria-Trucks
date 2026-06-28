# 07 — Comandos de referencia rápida

> Proyecto: Mercatoria Truck | Actualizado: 2026-06-28

---

## Desarrollo local

```bash
# Activar entorno virtual (Windows)
venv\Scripts\activate

# Activar entorno virtual (Mac/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Arrancar app (SQLite local, sin DATABASE_URL)
python app.py
# → http://127.0.0.1:5000

# Arrancar con PostgreSQL local
set DATABASE_URL=postgresql://user:pass@localhost/mercatoria   # Windows CMD
$env:DATABASE_URL="postgresql://user:pass@localhost/mercatoria" # PowerShell
python app.py
```

---

## Git

```bash
# Estado y diff
git status
git diff

# Commit semántico
git add <archivos específicos>
git commit -m "feat: descripción de la feature"
git commit -m "fix: descripción del bug corregido"
git commit -m "perf: optimización realizada"
git commit -m "security: cambio de seguridad"
git commit -m "docs: actualización de documentación"
git commit -m "refactor: refactorización sin cambio funcional"

# Push (confirmar antes de ejecutar)
git push origin main

# Ver historial
git log --oneline -20

# Ver diferencias entre commits
git diff HEAD~1 HEAD
```

---

## Migraciones

```bash
# Ejecutar migraciones v1.1 manualmente (Render Shell o local con DATABASE_URL)
python migrations_v11.py

# Ver qué migraciones SQLite existen
python -c "from migraciones import ejecutar_migraciones; ejecutar_migraciones()"
```

---

## Base de datos local (SQLite)

```bash
# Abrir SQLite interactivo
sqlite3 mercatoria.db

# Listar tablas
.tables

# Ver schema de una tabla
.schema viajes

# Query rápida
SELECT id, estado, cliente_id FROM viajes LIMIT 10;

# Salir
.quit
```

---

## Generar SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Render (producción)

```bash
# Ver logs en tiempo real (desde Render Dashboard o CLI)
# Render Dashboard → Mercatoria Truck → Logs

# Render Shell — ejecutar migración manual
python migrations_v11.py

# Render Shell — crear usuario admin
python -c "
from app import app
from database_pg import conectar_pg
from extensions import bcrypt
conn = conectar_pg()
cur = conn.cursor()
h = bcrypt.generate_password_hash('TU_PASSWORD').decode()
cur.execute(\"INSERT INTO usuarios (usuario, password, rol) VALUES ('admin', %s, 'admin')\", (h,))
conn.commit()
conn.close()
print('OK')
"
```

---

## Testing con Playwright MCP

Desde Claude Code, invocar el skill `/verify` para arrancar la app y probar con Playwright.

Comandos MCP disponibles (a través de Claude Code):
- `mcp__playwright__browser_navigate` — navegar a URL
- `mcp__playwright__browser_take_screenshot` — capturar pantalla
- `mcp__playwright__browser_snapshot` — accesibilidad snapshot
- `mcp__playwright__browser_fill_form` — rellenar formulario
- `mcp__playwright__browser_click` — hacer clic
- `mcp__playwright__browser_console_messages` — leer consola del browser

---

## Dependencias

```bash
# Ver dependencias instaladas
pip list

# Actualizar requirements.txt
pip freeze > requirements.txt  # (solo si hay nuevas deps reales)

# Instalar dependencia nueva
pip install nueva-libreria
pip freeze | grep nueva-libreria >> requirements.txt
```

Dependencias actuales (`requirements.txt`):
```
flask
gunicorn
flask-bcrypt
reportlab
openpyxl
flask-mail
flask-limiter
flask-wtf
psycopg2-binary
```

---

## Verificar estado de producción

```bash
# Comprobar que la app responde
curl https://<tu-app>.onrender.com/login

# Verificar headers de seguridad
curl -I https://<tu-app>.onrender.com/login
```
