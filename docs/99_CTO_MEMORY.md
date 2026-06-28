# 99 — CTO Memory

> Memoria técnica del CTO (ChatGPT) para Mercatoria Truck.
> Contexto y decisiones de arquitectura que Claude Code debe conocer al inicio de cada sesión.
> Actualizado: 2026-06-28

---

## Contexto del proyecto

**Mercatoria Truck** es una plataforma de gestión logística de transporte de carga para la empresa Mercatoria. Gestiona el ciclo completo: solicitud → cotización → asignación → operación → liquidación.

Usuarios reales: operadores internos de Mercatoria y clientes externos que contratan transporte.

---

## Estado técnico actual

- **Versión**: v1.1 en producción (Render + Neon PostgreSQL)
- **Alerta activa**: PostgreSQL Neon expira **2026-07-26** — prioritario
- **Deuda técnica menor**: reset de contraseña incompleto (tabla existe, flujo no)
- **Sin tests automatizados**: solo QA manual con Playwright MCP

---

## Principios de diseño que NO deben romperse

1. **Migraciones siempre idempotentes.** Nunca una migración que falle si se ejecuta dos veces.
2. **Sin ORM.** SQL directo. Si se necesita ORM, es decisión del CTO, no del engineer.
3. **Seguridad por defecto.** CSRF, bcrypt, SECRET_KEY obligatoria. No negociable.
4. **Separación SQLite/PostgreSQL transparente.** `db_config.py::USE_POSTGRES` es el único switch.
5. **Blueprints por módulo.** No mezclar lógica de módulos diferentes en el mismo archivo.
6. **Services para lógica compleja.** Las rutas solo orquestan; la lógica va en `services/`.

---

## Restricciones de negocio conocidas

- El rol `operador` no puede ver ingresos ni pagos a camioneros (solo `admin`).
- El rol `cliente` solo ve sus propios viajes en `/cliente/*` — sin acceso a datos de otros clientes.
- Los camioneros pueden no tener vehículo asignado (vehículo propio no obligatorio).
- El precio al cliente y el pago al camionero son independientes (margen configurable en tabla `configuracion`).

---

## Configuración de márgenes (tabla `configuracion`)

| Clave | Valor default | Descripción |
|---|---|---|
| `tarifa_km` | 1.5 | USD/km cobrado al camionero |
| `margen_combustible_divisor` | 2.0 | pago_camionero / divisor = combustible estimado |
| `multiplicador_pago_camionero` | 2.5 | precio_cliente = pago_camionero × multiplicador |
| `minimo_km_garantizado` | 120.0 | Km mínimo para liquidación |
| `minimo_pago_usd` | 150.0 | Pago mínimo garantizado al camionero (USD) |
| `comision_mercatoria_porcentaje` | 20.0 | % de comisión de Mercatoria sobre precio cliente |

---

## Decisiones pendientes del CTO

- **v1.2**: ¿API REST o seguir con server-side rendering? (impacta integración con Fuel)
- **Hosting**: ¿cuándo pasar de Render Free a plan de pago? (elimina el "sleep" del servidor)
- **BD**: ¿Neon Pro o migrar a Supabase/Railway? Decidir antes de 2026-07-26
- **Auth**: ¿Implementar OAuth/SSO para clientes empresariales en v1.3?
- **Multi-IA**: roadmap v2.0 — ¿qué agentes se integran? ¿para qué casos de uso?

---

## Roadmap aprobado (MDS v1.0)

| Versión | Contenido |
|---|---|
| v1.1 | Mejoras demostradas durante Truck/Fuel — **COMPLETADO** |
| v1.2 | BD/API — migraciones avanzadas, API REST básica |
| v1.3 | Observabilidad — logging estructurado, métricas, alertas |
| v2.0 | Multi-IA — integración de agentes de IA en el flujo operativo |

---

## Proyectos hermanos

- **Mercatoria Fuel**: proyecto paralelo, mismo stack (Flask + PostgreSQL), mismos estándares MDS.
- En v1.2 se planifica integración entre Truck y Fuel vía API REST.

---

## Contexto de equipo

| Rol | Responsable | Herramienta |
|---|---|---|
| CEO | Aldo | Visión, prioridades, decisión de negocio |
| CTO | ChatGPT | Arquitectura, metodología, estándares (este archivo) |
| Senior Software Engineer | Claude Code | Implementación, refactorización, despliegues |
| QA | Playwright MCP | Validación automática |

---

## Notas de sesiones anteriores

- La compatibilidad SQLite/PostgreSQL en queries de auditoría fue un bug recurrente. La solución: helper `sql_mes_actual()` que devuelve la expresión correcta según `USE_POSTGRES`.
- El sidebar en móvil tenía problema de scroll: resuelto con CSS específico para `position: sticky` en breakpoints pequeños.
- Las migraciones v1.1 fallaban en gunicorn porque el contexto de app no estaba disponible en el import. Resuelto: `with app.app_context():` en `app.py` antes de llamar `aplicar_migraciones_v11()`.
