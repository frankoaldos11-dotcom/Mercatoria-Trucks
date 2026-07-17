# Reporte de Pruebas — 2026-07-17

## Contexto
Cinco cambios de revisión en producción: elimina "camionero" de toda superficie visible (queda como "transportista"), combustible se confirma en litros (no dólares), tipo de carga editable en el detalle del viaje, reordena el flujo del viaje con un paso nuevo "En ruta", y la Orden de Carga quita datos del cliente y añade pago al transportista + litros confirmados.

## Páginas probadas (local, `127.0.0.1:5000`, con Claude in Chrome / MCP)
- `/login`, `/admin/` (dashboard)
- `/admin/transportistas` (y las 4 URLs viejas con "camionero" que deben redirigir)
- `/admin/viajes`
- `/admin/viaje/<id>` (gestionar viaje — flujo completo de pasos)
- `/admin/viaje/<id>/pdf` (Orden de Carga)

## Pruebas realizadas
1. Redirects 301: `/camioneros`→`/transportistas`, `/admin/camioneros`→`/admin/transportistas`, `/admin/camioneros/<id>/editar`→`/admin/transportistas/<id>/editar`, `/admin/camioneros/<id>/economico`→`/admin/transportistas/<id>/economico`. Confirmados con `curl -I`.
2. Flujo completo de un viaje de prueba (viaje existente #4, mutado y luego revertido): paso 4 "Confirmar combustible" acepta litros (50.0 L), calcula el costo en dólares solo con el precio de zona ($130.00), y persiste ambos valores (`litros_combustible`, `combustible`). Paso 5 "Marcar en ruta" aparece deshabilitado con aviso hasta confirmar combustible, y una vez confirmado permite la transición — confirmado que el estado del viaje pasa a "En ruta" y queda registrado en el historial.
3. Guard de backend: POST directo a `/admin/viaje/<id>/guardar-combustible` sobre un viaje sin transportista asignado (viaje de prueba creado y borrado ad-hoc) devuelve error "Asigna un transportista antes de confirmar combustible" sin persistir nada — confirma que la dependencia transportista→combustible se aplica en el servidor, no solo en la UI.
4. Dashboard: recuadro nuevo "En ruta" aparece con el conteo correcto (0 → 1 tras la transición de prueba).
5. Tipo de carga: el control de 7 opciones (Seca/Refrigerada/Congelada/Desagrupada/Frágil/Peligrosa/Otra) — el mismo control que "Nueva solicitud de viaje" — se guarda correctamente desde el detalle del viaje vía `POST /admin/viaje/<id>/guardar-tipo-carga`.
6. Orden de Carga (PDF descargado y verificado con `pypdf`): sección "DATOS DEL CLIENTE" ausente por completo; sección nueva "DATOS DE PAGO" muestra "Pago al transportista" y "Combustible confirmado" (con "Pendiente de confirmar" cuando aún no hay litros persistidos, sin inventar un dato).
7. Barrido final case-insensitive de "camionero" sobre `templates/`, `routes/`, `services/`, `static/` — 0 apariciones visibles al usuario; todo lo que queda son nombres internos (columnas de BD, variables Jinja, atributos `name=`, clases CSS, funciones JS).
8. `python -m py_compile` sobre todos los `.py` tocados — sin errores. Todas las plantillas del proyecto parseadas vía `app.jinja_env.get_template()` — sin errores.

## Errores encontrados
- Ninguno funcional en el código de la app. Durante la verificación, un `Start-Process` mío con directorio de trabajo mal resuelto lanzó por error el servidor del proyecto hermano `mercatoria-fuel` en el puerto 5000 (nunca se editó ningún archivo ahí — solo se ejecutó su servidor por accidente). Detectado, confirmado con `git status` en `mercatoria-fuel` (limpio), y corregido relanzando con `-WorkingDirectory` explícito.

## Screenshots tomados
- Login y dashboard tras iniciar sesión como admin.
- `/admin/transportistas` (listado, sin "camionero" visible).
- `/admin/viaje/4` con los 6 pasos reordenados y el paso "En ruta" nuevo.

## Correcciones aplicadas
Ver plan aprobado (`transient-shimmying-truffle.md`): `migrations_v15.py` (nuevo) + `migraciones.py` + `app.py` (columna `litros_combustible`), `routes/admin.py` (`guardar_combustible` reescrito con guard, `guardar_tipo_carga` nuevo, dashboard KPI, 4 rutas con redirect 301 + 5 rutas sin redirect renombradas, mensajes de error y auditoría "camionero"→"transportista"), `routes/camioneros.py` y `routes/comercial.py` (rutas renombradas), `routes/finanzas.py` (etiqueta de error), `services/pdf_service.py` (Orden de Carga sin cliente + sección de pago, Liquidación Transportista renombrada), `templates/admin/gestionar_viaje.html` (reorden completo de pasos + paso En ruta + tipo de carga editable), `templates/admin/dashboard.html` (KPI En ruta), 15 templates con texto "camionero"→"transportista", 3 templates renombrados (`camioneros.html`→`transportistas.html`, etc.), `static/sw.js` (URL de precache actualizada).

## Datos de prueba y limpieza
- Viaje #4 (preexistente, dev-only): se confirmó combustible (50 L), se cambió tipo de carga a "Frágil" y se marcó "En ruta" durante la verificación — revertido a su estado original (`Asignado`, `piezas de carro`, litros/combustible/fecha_recogida a NULL) al finalizar.
- Viaje de prueba #38 (creado ad-hoc para probar el guard de combustible sin transportista): eliminado junto con sus filas de `historial_viaje` y `auditoria`.
- Servidor Flask detenido correctamente tras la verificación. `Get-Process python` confirma que no queda proceso vivo.

## Recomendaciones
- Ninguna pendiente de esta tanda. Los ítems marcados en el plan como "a confirmar con Aldo" (nombres de archivo de template, alias de Excel, línea de firma "Cliente / Receptor") se resolvieron según lo propuesto por defecto sin objeción.
