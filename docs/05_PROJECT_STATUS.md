# 05 — Estado del Proyecto

> Proyecto: Mercatoria Truck | Actualizado: 2026-07-05

---

## Estado general

| Campo | Valor |
|---|---|
| Versión desplegada | **v1.1** |
| Entorno de producción | Render (Python/Gunicorn) |
| Base de datos | PostgreSQL — Render (`mercatoria-truck-db`, plan Basic, propia de Truck) |
| Estado | **En producción — estable** |
| Próximo hito | Ver backlog v1.2+ |

---

## Nota de infraestructura (2026-07-05)

> La alerta anterior de este archivo ("PostgreSQL en Neon expira el 2026-07-26") **ya no aplica**. Producción migró de Neon a PostgreSQL de Render. Truck tiene su propia base (`mercatoria-truck-db`, plan Basic de pago — no expira), separada de la base de Fuel (`mercatoria-db`); ambas llegaron a compartir una base gratuita de Render en algún momento, lo cual causó un incidente real (detalle en `98_DECISION_LOG.md`). **A confirmar**: fecha exacta del cambio de proveedor y si `mercatoria-db` (Fuel) sigue en plan Free con expiración propia.

---

## Funcionalidades implementadas en v1.1

### Core
- [x] Autenticación con bcrypt + CSRF + rate limiting
- [x] Roles: admin, operador, cliente
- [x] Sesiones permanentes de 8 horas
- [x] Headers de seguridad en todas las respuestas
- [x] PWA: manifest.json + service worker + iconos + favicon

### Dashboard
- [x] KPIs del mes: viajes, ingresos, clientes activos
- [x] Alertas de viajes urgentes y solicitados
- [x] Badges en sidebar actualizados por context_processor
- [x] Métricas ocultadas para rol operador (ingresos)

### Viajes
- [x] Flujo completo de estados: Solicitado → Pendiente → En tránsito → Entregado → Liquidado
- [x] Asignación de camionero y vehículo
- [x] Checklist operativo persistente por viaje (tabla `viaje_checklist`)
- [x] Sistema de incidencias con categorías y estados (tabla `incidencias`)
- [x] Notas de viaje (tabla `notas_viaje`)
- [x] Generación de PDF
- [x] Campos operativos ampliados: tipo carga, tipo transporte, peso toneladas, contenedores
- [x] Control de pago al camionero: estado, monto, fecha

### Camioneros
- [x] CRUD completo
- [x] Camionero sin vehículo obligatorio
- [x] Estado económico: pendientes por cobrar
- [x] Asignación de rutas (tabla `camionero_ruta`)
- [x] Licencia y estado de actividad

### Clientes
- [x] CRUD con categorías (Normal, Premium, VIP)
- [x] Portal cliente propio (`/cliente/*`)
- [x] Paginación en listado
- [x] Filtros por categoría
- [x] Registro self-service

### Vehículos y catálogos
- [x] CRUD vehículos vinculados a camioneros
- [x] Tipos de vehículo con capacidad (tabla `tipos_vehiculo`)
- [x] Catálogo tipo transporte: Rastra, Plancha, Furgón, Camión cerrado, etc.

### Comercial / Cotizaciones
- [x] Rutas con km oficiales y zona
- [x] Tarifas por ruta + tipo vehículo
- [x] Cotizaciones con precio calculado automáticamente
- [x] Conversión cotización → viaje
- [x] Configuración de márgenes (tabla `configuracion`)

### Finanzas (solo admin)
- [x] Ingresos del mes
- [x] Pagos a camioneros
- [x] Movimientos por viaje
- [x] Exportación Excel (openpyxl)
- [x] Generación de reportes PDF (reportlab)

### Admin Panel
- [x] Gestión de usuarios (crear, editar, desactivar)
- [x] Configuración numérica (tarifas, márgenes, mínimos)
- [x] Configuración de texto
- [x] Auditoría completa con filtros

### BD y migraciones
- [x] Migraciones base SQLite (`migraciones.py`)
- [x] Migraciones base PostgreSQL (`migraciones_pg.py`)
- [x] Migraciones v1.1 (`migrations_v11.py`) — idempotentes, se ejecutan al arrancar
- [x] Índices en viajes, clientes, camioneros, auditoría

---

## Pendientes externos (bloqueos fuera del código)

| Pendiente | Responsable | Fecha límite | Impacto |
|---|---|---|---|
| Confirmar plan/expiración de `mercatoria-db` (Fuel) tras la separación de bases | CEO/CTO | Sin fecha confirmada | Medio — evitar repetir el mismo tipo de alerta con Fuel |
| Dominio propio (no `*.onrender.com`) | CEO | Sin fecha | Imagen profesional |
| Plan de pago Render (para no dormir el servidor) | CEO | Sin fecha | UX — arranque lento tras inactividad |

---

## Pendientes técnicos (backlog v1.2+)

- [ ] Reset de contraseña por email (tabla `reset_tokens` ya existe, falta flujo completo)
- [ ] Notificaciones por correo en cambios de estado de viaje
- [ ] Tests automatizados (pytest) para rutas críticas
- [ ] Dashboard con gráficos históricos (más de 30 días)
- [ ] API REST para integración con Mercatoria Fuel
- [ ] Modo offline avanzado en PWA (sync diferido)

---

## Historial de versiones

| Versión | Fecha | Estado |
|---|---|---|
| v1.0 | 2025-Q4 | Base — auth, viajes, clientes, camioneros |
| v1.1 | 2026-Q2 | En producción — ver CHANGELOG |
| v1.2 | Planificado | BD/API, reset contraseña, notificaciones |
