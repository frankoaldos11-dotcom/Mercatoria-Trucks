# Reporte de Pruebas — 2026-06-28

## Tipo de auditoría
Auditoría de compatibilidad SQLite/PostgreSQL — búsqueda y corrección de funciones SQL exclusivas de PostgreSQL sin guard `if USE_POSTGRES`.

---

## Páginas probadas

### Panel Admin (usuario: `admin`)
| Ruta | Estado | Errores consola |
|------|--------|----------------|
| `/admin/` | ✅ OK | 0 |
| `/admin/viajes` | ✅ OK | 0 |
| `/admin/reportes` | ✅ OK | 0 |
| `/admin/clientes` | ✅ OK | 0 |
| `/admin/camioneros` | ✅ OK | 0 |
| `/admin/vehiculos` | ✅ OK | 0 |
| `/admin/usuarios` | ✅ OK | 0 |
| `/admin/auditoria` | ✅ OK | 0 |
| `/admin/lote` | ✅ OK | 0 |
| `/admin/comercial/rutas` | ✅ OK | 0 |
| `/admin/comercial/cotizaciones` | ✅ OK | 0 |
| `/admin/cotizaciones` | ⚠️ 404 | — (ruta no registrada; sidebar apunta a URL incorrecta) |
| `/admin/rutas` | ⚠️ 404 | — (idem) |

### Portal Cliente (usuario: `ana2@test.com`)
| Ruta | Estado | Errores consola |
|------|--------|----------------|
| `/cliente/` | ✅ OK | 0 |
| `/cliente/viajes` | ✅ OK | 0 |
| `/cliente/solicitar` | ✅ OK | 0 |
| `/cliente/perfil` | ✅ OK | 0 |

---

## Resultados de la auditoría de funciones PostgreSQL

### Archivos escaneados
- `routes/*.py` (11 archivos)
- `services/*.py` (3 archivos)
- `app.py`, `database.py`
- `templates/**/*.html`

### Ocurrencias encontradas en runtime

| Archivo | Línea | Función | Estado |
|---------|-------|---------|--------|
| `routes/admin.py` | 133 | `TO_CHAR` | ✅ Corregida (sesión anterior) — guard `if USE_POSTGRES` añadido |
| `routes/admin.py` | 1769–1772 | `TO_CHAR`, `DATE_TRUNC`, `INTERVAL` | ✅ Ya tenía `if USE_POSTGRES / else SQLite` |
| `templates/admin/viajes.html` | 129 | `.strftime()` sobre `str` | ✅ Corregida — usa filtro `fmt_fecha` |
| `templates/admin/clientes.html` | 140 | `.strftime()` sobre `str` | ✅ Corregida — usa filtro `fmt_fecha` |
| `templates/admin/camionero_economico.html` | 67 | `.strftime()` sobre `str` | ✅ Corregida — usa filtro `fmt_fecha` |
| `templates/admin/orden_carga.html` | 262 | `.strftime()` sobre `str` | ✅ Corregida — usa filtro `fmt_fecha` |
| `templates/cliente/viajes.html` | 63, 98 | `.strftime()` sobre `str` | ✅ Corregida — usa filtro `fmt_fecha` |

### Funciones PG-only en archivos de migración
`ON CONFLICT`, `DATE_TRUNC`, `INTERVAL`, `TO_CHAR` aparecen en `migraciones_pg.py` y `migrations_v11.py` — **correcto**, son archivos exclusivos de PostgreSQL que nunca se ejecutan en SQLite.

### Sin ocurrencias problemáticas en
- `routes/viajes.py`, `routes/camioneros.py`, `routes/vehiculos.py`
- `routes/finanzas.py`, `routes/comercial.py`, `routes/dashboard.py`
- `routes/cliente.py`, `routes/clientes.py`
- `services/finanzas_service.py`, `services/comercial_service.py`, `services/pdf_service.py`
- `app.py`, `database.py`
- Todos los templates (tras las correcciones)

---

## Errores encontrados en esta sesión
**Ninguno nuevo.** Todas las rutas cargaron sin errores HTTP 500 ni excepciones de consola.

### Warnings no bloqueantes (preexistentes)
- `favicon.ico` → 404 en todas las páginas (cosmético)
- `<meta name="apple-mobile-web-app-capable">` deprecado en portal cliente (PWA)

---

## Screenshots tomados
- `audit_admin_dashboard.png` — Dashboard admin post-auditoría
- `audit_admin_reportes.png` — Página de reportes (usa `DATE_TRUNC`/`strftime` según motor)
- `audit_admin_auditoria.png` — Log de auditoría del sistema

---

## Recomendaciones

1. **Links rotos en sidebar**: `/admin/cotizaciones` y `/admin/rutas` devuelven 404. Las rutas reales están en `/admin/comercial/cotizaciones` y `/admin/comercial/rutas`. Corregir los href en el template del sidebar.

2. **Favicon**: Añadir `static/favicon.ico` y enlazarlo en el `<head>` del template base para eliminar el 404 en cada carga.

3. **Meta PWA**: Reemplazar `apple-mobile-web-app-capable` por `mobile-web-app-capable` en el template del portal cliente.

4. **Helper SQL cross-DB**: Considerar un helper `fecha_mes_actual()` que devuelva el fragmento SQL correcto según `USE_POSTGRES`, para centralizar futuras queries de filtro por mes y evitar repetir el patrón `if USE_POSTGRES / else`.

5. **Test de integración mínimo**: Ejecutar un smoke test de las queries críticas contra SQLite en CI antes de desplegar a Render, para detectar incompatibilidades antes de que lleguen a producción.
