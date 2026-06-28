# 02 — QA Master (Especificación de Calidad)

> Versión MDS: 1.0 | Proyecto: Mercatoria Truck | Actualizado: 2026-06-28

---

## Herramienta principal

**Playwright MCP** (`mcp__playwright__*`) — automatización de browser integrada con Claude Code.

Al terminar cualquier sesión de pruebas con Playwright, generar automáticamente `test_report.md` en la raíz del proyecto con la estructura definida en las reglas globales de Claude (`~/.claude/CLAUDE.md`).

---

## Roles y acceso a probar

| Rol | Usuario de prueba | Acceso esperado |
|---|---|---|
| admin | admin | Todo el sistema |
| operador | operador | Viajes, camioneros, clientes — sin finanzas ni configuración |
| cliente | cliente@test.com | Portal cliente propio (`/cliente/*`) |

---

## Flujos críticos — smoke test obligatorio antes de cada despliegue

### AUTH
- [ ] Login con credenciales correctas → redirige según rol
- [ ] Login con credenciales incorrectas → mensaje de error, no expone info
- [ ] Logout → limpia sesión, redirige a `/login`
- [ ] Rate limit login: más de 10 intentos/min → bloqueo temporal

### DASHBOARD (admin/operador)
- [ ] Métricas del mes cargadas sin error (viajes, ingresos, clientes)
- [ ] Gráficos visibles
- [ ] Badges del sidebar reflejan viajes urgentes/solicitados en tiempo real

### VIAJES
- [ ] Crear viaje desde solicitud de cliente
- [ ] Asignar camionero y vehículo
- [ ] Cambiar estado: Solicitado → Pendiente → En tránsito → Entregado → Liquidado
- [ ] Checklist operativo: marcar ítems, persiste al recargar
- [ ] Registrar incidencia y cambiar su estado
- [ ] Notas de viaje: agregar y visualizar
- [ ] Generar PDF de viaje
- [ ] Operador no puede ver sección de finanzas/pagos

### CAMIONEROS
- [ ] Crear camionero (sin vehículo obligatorio)
- [ ] Ver estado económico: pendientes por cobrar
- [ ] Asignar rutas al camionero

### CLIENTES
- [ ] Portal cliente: ver mis viajes, estado actualizado
- [ ] Registro de nuevo cliente
- [ ] Filtro por categoría (Normal, Premium, VIP)
- [ ] Paginación funciona

### COMERCIAL / COTIZACIONES
- [ ] Crear cotización desde ruta + tipo vehículo
- [ ] Precio calculado automáticamente
- [ ] Convertir cotización a viaje

### FINANZAS (solo admin)
- [ ] Ver ingresos del mes
- [ ] Registrar pago a camionero
- [ ] Exportar reporte Excel

### ADMIN PANEL
- [ ] Gestión de usuarios: crear, editar rol, desactivar
- [ ] Configuración: editar tarifas/km, márgenes
- [ ] Auditoría: ver log de acciones con filtros

### PWA
- [ ] `manifest.json` accesible en `/static/manifest.json`
- [ ] `sw.js` accesible en `/sw.js` con header `Service-Worker-Allowed: /`
- [ ] Icono visible en pestaña del navegador (favicon)

---

## Casos de borde a cubrir

- Viaje sin camionero asignado: no rompe la vista
- Cliente sin viajes: portal muestra estado vacío limpio
- Campos numéricos con valor 0: se muestran como `0`, no como `—`
- Fechas nulas: filtro `fmt_fecha` devuelve `—` sin excepción
- Sesión expirada (>8h): redirige a login sin error 500

---

## Errores que NO deben aparecer en consola

- `500 Internal Server Error` en rutas de uso normal
- `OperationalError` de PostgreSQL (conexión caída)
- `KeyError` en acceso a columnas de BD
- Warnings de CSRF (token faltante o inválido en formularios)
- `NullPointerException` en JavaScript (consola del browser)

---

## Checklist de regresión post-despliegue

Ejecutar después de cada `git push` a producción:

1. `curl https://<app>.onrender.com/login` → HTTP 200
2. Login admin → dashboard carga con métricas
3. Crear un viaje de prueba → asignar camionero → cambiar estado
4. Login cliente → portal carga viajes correctamente
5. Revisar logs de Render: sin errores 500 ni excepciones Python

---

## Reporte estándar de pruebas

Archivo: `test_report.md` en la raíz del proyecto.

Estructura mínima:
```markdown
# Reporte de Pruebas — YYYY-MM-DD
## Páginas probadas
## Errores encontrados
## Screenshots tomados
## Correcciones aplicadas
## Recomendaciones
```
