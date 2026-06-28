# 04 — Arquitectura

> Versión MDS: 1.0 | Proyecto: Mercatoria Truck | Actualizado: 2026-06-28

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.x + Flask |
| Base de datos prod | PostgreSQL 16 (Neon) |
| Base de datos local | SQLite 3 |
| ORM | Ninguno — SQL directo con `psycopg2` / `sqlite3` |
| Autenticación | `flask-bcrypt` + sesiones Flask |
| CSRF | `flask-wtf` |
| Rate limiting | `flask-limiter` (memory://) |
| Correo | `flask-mail` (SMTP Gmail) |
| PDF | `reportlab` |
| Excel | `openpyxl` |
| Frontend | Jinja2 + HTML/CSS/JS (Vanilla) |
| PWA | `manifest.json` + Service Worker (`sw.js`) |
| Servidor prod | Gunicorn |
| Hosting | Render (Free) |
| CI/CD | GitHub → Render autodeploy en push a `main` |

---

## Diagrama de capas

```
┌─────────────────────────────────────────────────┐
│                  Cliente (Browser)               │
│            HTML/CSS/JS + PWA (sw.js)            │
└───────────────────────┬─────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────┐
│              Flask Application (app.py)          │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ CSRF     │  │ Rate     │  │ Security      │  │
│  │ (WTF)    │  │ Limiter  │  │ Headers       │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │              Blueprints (routes/)          │  │
│  │  home │ dashboard │ viajes │ camioneros    │  │
│  │  clientes │ cliente │ admin │ vehiculos    │  │
│  │  comercial │ finanzas                      │  │
│  └──────────────────┬─────────────────────────┘  │
│                     │                            │
│  ┌──────────────────▼─────────────────────────┐  │
│  │              Services (services/)           │  │
│  │  finanzas_service │ comercial_service       │  │
│  │  pdf_service                               │  │
│  └──────────────────┬─────────────────────────┘  │
└─────────────────────┼───────────────────────────┘
                      │ SQL
┌─────────────────────▼───────────────────────────┐
│              Base de Datos                       │
│  Prod: PostgreSQL (Neon) via DATABASE_URL        │
│  Dev:  SQLite (mercatoria.db)                    │
└─────────────────────────────────────────────────┘
```

---

## Módulos (Blueprints)

| Blueprint | Prefijo URL | Roles con acceso | Función principal |
|---|---|---|---|
| `home_bp` | `/` | Público | Redirect a login o portal |
| `dashboard_bp` | `/admin` | admin, operador | KPIs, métricas, alertas |
| `viajes_bp` | `/viajes` | admin, operador | CRUD viajes, checklist, incidencias |
| `camioneros_bp` | `/camioneros` | admin, operador | CRUD camioneros, estado económico |
| `clientes_bp` | `/clientes` | admin, operador | CRUD clientes, categorías |
| `cliente_bp` | `/cliente` | cliente | Portal propio, mis viajes |
| `admin_bp` | `/admin/...` | admin | Usuarios, configuración, auditoría |
| `vehiculos_bp` | `/vehiculos` | admin, operador | CRUD vehículos y tipos |
| `comercial_bp` | `/comercial` | admin, operador | Cotizaciones, tarifas, rutas |
| `finanzas_bp` | `/finanzas` | admin | Ingresos, pagos, reportes |

---

## Schema de base de datos (tablas principales)

```
usuarios          — id, usuario, password (bcrypt), rol, nombre, activo
clientes          — id, empresa, contacto, email, categoria, usuario_id
camioneros        — id, nombre, telefono, licencia, estado, activo
vehiculos         — id, camionero_id, tipo_vehiculo_id, placa, marca, modelo
tipos_vehiculo    — id, nombre, capacidad_ton
rutas             — id, origen, destino, zona, km_oficiales, activa
tarifas           — id, ruta_id, tipo_vehiculo_id, precio_cliente, pago_camionero
cotizaciones      — id, cliente_id, ruta_id, precio_final, estado
viajes            — id, cliente_id, camionero_id, ruta_id, estado, prioridad, ...
viaje_checklist   — id, viaje_id, item, completado, completado_por
incidencias       — id, viaje_id, categoria, descripcion, estado
notas_viaje       — id, viaje_id, usuario, texto, fecha
movimientos_viaje — id, viaje_id, tipo, monto, descripcion
configuracion     — clave (PK), valor (REAL), descripcion
configuracion_texto — clave (PK), valor (TEXT)
auditoria         — id, fecha, usuario, rol, accion, categoria, entidad, detalle
reset_tokens      — id, token, usuario, expira, usado
```

---

## Detección de entorno (SQLite vs PostgreSQL)

```python
# db_config.py
DATABASE_URL = os.environ.get("DATABASE_URL", None)
USE_POSTGRES = DATABASE_URL is not None
```

Las migraciones y la función `conectar()` usan `USE_POSTGRES` para decidir qué driver usar.

---

## Sistema de auditoría

Tabla `auditoria` — registra todas las acciones relevantes:
- `usuario`: quién hizo la acción
- `rol`: con qué rol
- `accion`: verbo (creó, editó, eliminó, cambió estado)
- `categoria`: módulo (viajes, clientes, finanzas, admin)
- `entidad` + `entidad_id`: objeto afectado
- `detalle`: descripción libre en JSON o texto

Visible en Admin Panel → Auditoría con filtros por categoría y fecha.

---

## PWA

- `static/manifest.json` — metadatos de la app (nombre, iconos, colores)
- `static/sw.js` — service worker (cache offline básico)
- Ruta especial `/sw.js` en `app.py` con header `Service-Worker-Allowed: /`
- Iconos en `static/icons/`

---

## Seguridad

- Sesiones: 8 horas, permanentes, almacenadas en cookie firmada con `SECRET_KEY`
- CSRF: token obligatorio en todos los formularios POST
- Rate limit: `/login` → 10 req/min (en memoria, se resetea al reiniciar)
- bcrypt para contraseñas (coste por defecto)
- Headers: `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`

---

## Decisiones de arquitectura clave

| Decisión | Razón |
|---|---|
| Sin ORM (SQL directo) | Control total, migraciones simples, sin magia implícita |
| SQLite en local / PostgreSQL en prod | Desarrollo sin dependencias externas, prod con BD real |
| Migraciones idempotentes en scripts versionados | Seguro de re-ejecutar, rastreable en git |
| Blueprints por módulo | Separación de responsabilidades, escalable |
| Services para lógica compleja | Rutas limpias, reutilización, testeable |
| Sin frontend framework (Vanilla JS) | Sin build step, carga directa, suficiente para la escala actual |
