# 06 — Changelog

> Formato: [Tipo] Descripción — (commit hash)

---

## Sesión de estabilización PostgreSQL — 2026-07 (post v1.1, en producción)

### Fixes
- `fix` refactor `_registrar_historial`: recibe el cursor de la transacción activa, elimina el `try/except: pass` que silenciaba errores — `590c14a`
- `fix` elimina `conectar()` local en `migraciones.py`, usa la conexión centralizada — `65772e0`
- `fix` orden de `SKIP_MIGRATIONS`: el chequeo del flag va después de verificar si el schema existe, para que una base vacía siempre se cree — `75cf3b0`
- `fix` vincula usuario cliente a su ficha de cliente desde el admin (antes solo el autoregistro producía el vínculo) + crear cliente desde la pantalla de "Nuevo usuario" — `799a221`
- `fix` seis correcciones de flujo de viaje: UX de tramos, causa raíz de factura no descargable, transportista como requisito temprano para entrega/pago, formularios que conservan datos tras error de validación, aviso y marca retroactiva en Historial para entregas fuera de fecha, conteo correcto de "Viajes en curso" en dashboard — `b79ef18`

### Incidente de infraestructura
- Truck y Fuel compartían una sola base PostgreSQL gratuita de Render, causando un 500 "column does not exist" en el login de Truck (esquema de Fuel pisando el de Truck). Resuelto separando Truck a su propia base (`mercatoria-truck-db`, plan Basic). Detalle en `98_DECISION_LOG.md`.

---

## v1.1 — 2026-Q2 (en producción)

### Fixes
- `fix` links del sidebar corregidos, favicon añadido, meta PWA correctos, helper `sql_mes_actual` — `6c19ffa`
- `fix` auditoría: compatibilidad SQLite/PostgreSQL en queries con fechas — `d808d20`
- `fix` checklist automático al crear viaje, layout móvil del sidebar — `553d971`
- `fix` permisos del rol operario en viaje, métricas del cliente, scroll móvil — `6eda156`
- `fix` migración v1.1 arranca correctamente con gunicorn en Render — `16d08bb`
- `fix` migraciones v1.1 columnas nuevas en PostgreSQL — `324d459`
- `fix` ocultar "cotizar" del sidebar y conectar catálogo tipo transporte — `3a8a673`

### Features
- `feat` PWA Android: manifest.json, service worker e iconos — `d9a1ff8`
- `feat` camioneros sin vehículo obligatorio, catálogo tipo transporte, filtros y paginación — `b6684a0`
- `feat` estado económico del camionero con pendientes por cobrar — `583824e`
- `feat` sistema de incidencias por viaje con modal y estados — `8d95dce`
- `feat` checklist operativo persistente por viaje — `69a5d59`
- `feat` viaje admin en pestañas con bloque de alertas operativas — `71732ca`
- `feat` categoría de cliente con badge visual y filtro en admin — `53f642b`
- `feat` solicitud ampliada: tipo carga, transporte, peso toneladas y campos operativos — `3917736`
- `feat` permisos por rol en clientes, tarifas y configuración — `ca7b94a`

### Performance
- `perf` índices en BD, paginación de clientes, optimización dashboard, logging de tiempos — `3a8a673`

### Seguridad
- `security` CSRF activado, SECRET_KEY obligatoria, prints eliminados, ruta legacy removida, .env.example — `63758c6`

---

## v1.0 — 2025-Q4

- Base del sistema: autenticación, roles (admin/operador/cliente)
- Módulos: dashboard, viajes, camioneros, clientes, vehículos
- Despliegue inicial en Render con PostgreSQL Neon
- Schema base de BD con migraciones idempotentes

---

## Próximo: v1.2 (planificado)

- Reset de contraseña por email
- Notificaciones en cambios de estado de viaje
- API REST básica
- Tests automatizados (pytest)
- Dashboard con histórico >30 días
