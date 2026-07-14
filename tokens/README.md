# Design tokens — Mercatoria Truck

Fuente de verdad de los design tokens del sitio. Esta carpeta es autocontenida:
un diseñador puede editar solo los `.json` de acá y regenerar el CSS sin tocar
lógica de la app ni templates.

## Qué hay en cada archivo

| Archivo | Contiene | Convención de nombres |
|---|---|---|
| `color.json` | 14 colores (fondo, panel, texto, semánticos peligro/exito/aviso/info, barra lateral) | **Español, plano** (`fondo`, `panel`, `texto`, `atenuado`, `peligro`...) — es la definición canónica. Ver "Renombrado a español" abajo. |
| `color-legacy.json` | Los 12 nombres viejos en inglés (`bg`, `text`, `muted`, `danger`...) que siguen en uso en `admin.css` y templates | Inglés, plano — cada clave es una **referencia** (`{fondo}`, `{texto}`...) al token español correspondiente en `color.json`, no un valor duplicado a mano. Ver por qué existe este archivo abajo. |
| `effects.json` | `shadow` y `radius` originales (intactos, en uso real vía `var(--shadow)`/`var(--radius)`) + escalas nuevas `radio-*` (4 pasos) y `sombra-*` (3 pasos) | Español + talla (`radio-sm/md/lg/pill`, `sombra-sm/md/lg`) |
| `typography.json` | Font-family por superficie, escala de tamaños, escala de pesos | Español + talla (`fuente-*`, `texto-*`, `peso-*`) |
| `spacing.json` | Escala de espaciado (padding/margin/gap) | Español + talla (`espacio-*`) |

Todos los valores son los que la app usa **hoy**, verificados con grep sobre
`templates/` y `static/css/admin.css` — no son valores de diseño nuevos ni
aspiracionales. El detalle completo del inventario (qué valor, cuántas veces
se usa, dónde) está en `plan_tokens.md` (raíz del repo, no comiteado — vive
localmente hasta que se apruebe borrarlo).

## Renombrado a español (color.json) — por qué existe `color-legacy.json`

`color.json` empezó en inglés porque se tomó tal cual del `:root` que ya
vivía en `admin.css`. Se renombró a español para que todo el vocabulario de
`tokens/` sea consistente en un solo idioma. Mapeo completo:

| Nombre viejo (inglés) | Nombre nuevo (español) | Valor |
|---|---|---|
| `bg` | `fondo` | `#f4f6fb` |
| `panel` | `panel` (sin cambio — ya es una palabra válida en español) | `#ffffff` |
| `panel-soft` | `panel-suave` | `#f8fafc` |
| `text` | `texto` | `#172033` |
| `muted` | `atenuado` | `#64748b` |
| `primary` | `principal` | `#155eef` |
| `primary-dark` | `principal-oscuro` | `#0f3ea8` |
| `border` | `borde` | `#e5e7eb` |
| `danger` | `peligro` | `#dc2626` |
| `success` | `exito` | `#16a34a` |
| `warning` | `aviso` | `#f59e0b` |
| `info` | `info` (sin cambio — funciona igual en ambos idiomas) | `#0891b2` |
| `sidebar` | `barra-lateral` | `#0f172a` |
| `sidebar-soft` | `barra-lateral-suave` | `#102a56` |

Es un renombrado puro — **ningún valor cambió**.

`admin.css` y 29 templates tienen **202 referencias `var(--nombre-viejo)`**
repartidas en 30 archivos (`admin.css` solo concentra 50; `gestionar_viaje.html`
otras 38). Reescribir esos 202 sitios para que digan `var(--peligro)` en vez
de `var(--danger)` fue evaluado y descartado por volumen/riesgo frente al
beneficio (cosmético, cero cambio visual) — en cambio, `color-legacy.json`
genera los 12 nombres viejos como **alias que resuelven al mismo valor** que
su equivalente español. `static/css/tokens.css` termina con ambos juegos de
variables (español, canónico + inglés, alias de compatibilidad), así que
ninguno de los 202 `var()` existentes se rompe.

**Consecuencia práctica:** un diseñador que solo edita `.json` ya trabaja
100% en español (ese era el objetivo). El código fuente de `admin.css` y los
templates sigue diciendo `var(--danger)` literalmente — migrar esos 202
sitios a los nombres nuevos es una tanda aparte, opcional, no parte de este
renombrado.

## Cómo regenerar `static/css/tokens.css`

```bash
npm install        # solo la primera vez, o si cambió package.json
npx style-dictionary build --config sd.config.json
# o, equivalente:
npm run tokens:build
```

Esto corre **en local**. Render no ejecuta Node — sigue sirviendo
`static/css/tokens.css` como archivo estático generado y comiteado. Después
de regenerar, revisar el diff (`git diff static/css/tokens.css`) antes de
commitear, para confirmar que solo cambió lo que se esperaba tocar.

**No editar `static/css/tokens.css` a mano.** Es el output del build — cualquier
edición manual se pierde en el próximo `style-dictionary build`.

**No tocar `admin.css` ni ningún template desde esta carpeta.** `tokens/`
solo define el catálogo de variables disponibles; que un archivo empiece a
usar `var(--espacio-md)` en vez de `12px` hardcodeado (o `var(--peligro)` en
vez de `var(--danger)`) es una tanda de aplicación aparte, con su propio plan
y verificación visual — no algo que se haga al mismo tiempo que se amplía o
renombra el catálogo.

## Vocabulario de nombres (compartido con Mercatoria Fuel)

Este vocabulario lo define Truck y lo hereda Fuel. La idea es que ambas apps
usen los mismos **nombres de escalón** aunque sus valores concretos no
coincidan exactamente — por eso ningún nombre lleva el valor literal
incrustado (nunca `--espacio-8`, siempre `--espacio-sm`). Así cada app puede
tener su propio número bajo el mismo nombre. Todo el vocabulario es español
desde esta tanda.

| Categoría | Prefijo | Escalones | Ejemplo |
|---|---|---|---|
| Color de fondo/panel/texto/borde | `fondo`, `panel`, `texto`, `atenuado`, `borde` | — (plano, sin escalón todavía) | `--fondo`, `--texto` |
| Color semántico | `peligro` / `exito` / `aviso` / `info` | — | `--peligro` |
| Familia tipográfica | `fuente-*` | `staff` / `cliente` / `landing` / `base` (superficie, no talla) | `--fuente-staff` |
| Tamaño de texto | `texto-*` | `xs` `sm` `md` `lg` `xl` `2xl` | `--texto-md` |
| Peso de fuente | `peso-*` | `regular` `semibold` `bold` `extrabold` | `--peso-bold` |
| Espaciado | `espacio-*` | `xs` `sm` `md` `lg` `xl` `2xl` | `--espacio-md` |
| Radio de borde | `radio-*` | `sm` `md` `lg` `pill` | `--radio-md` |
| Sombra | `sombra-*` | `sm` `md` `lg` | `--sombra-md` |

### Pendiente de diseño (documentado, no implementado): neutros por superficie

Truck hoy tiene un solo set de neutros (`--fondo`, `--texto`, `--atenuado`,
`--borde`) porque solo existía la superficie staff/admin cuando se creó
`color.json`. Fuel sí necesita valores de neutro **distintos** entre su
superficie de staff y su superficie de cliente. El patrón de nombres
acordado para cuando se haga esa tanda (en Truck o directamente en Fuel) es:

```
--{rol}-staff   /   --{rol}-cliente
```

sobre los nombres de rol que ya existen en `color.json` (ya en español) — por
ejemplo `--fondo-staff` / `--fondo-cliente`, `--texto-staff` /
`--texto-cliente`, `--atenuado-staff` / `--atenuado-cliente`, `--borde-staff`
/ `--borde-cliente`. No se implementa ahora: los 14 tokens de color de
`color.json` siguen planos y sin sufijo de superficie hasta que se apruebe
esa tanda explícitamente (implica fusionar/revisar valores casi-duplicados,
no es "cero cambio visual" garantizado como sí lo es este renombrado).

## Paleta de Adrián (Figma, DTCG) aplicada — `mercatoria-design-tokens.json`

Adrián (diseño) entregó `tokens/mercatoria-design-tokens.json` (formato DTCG,
namespace `mercatoria.*`) con la propuesta de rediseño real de color, radios
y sombra. A diferencia de las tandas anteriores, acá **el cambio visual es
intencional**: se tradujeron sus valores al vocabulario en español ya
existente (sin adoptar su estructura de nombres), actualizando `color.json` y
`effects.json` — ver el archivo original comiteado como referencia de origen.

Regla aplicada: todo token del proyecto que Adrián no cubre **conserva su
valor actual** (no se inventó ni aproximó nada).

### Cambios de color aplicados

`fondo`, `texto`, `principal`, `borde`, `peligro`, `exito`, `aviso`,
`barra-lateral` — actualizados a los valores de Adrián. Tokens nuevos creados
por tener uso real confirmado con grep: `fondo-naranja-suave` (`#fff3e8`,
ya usado como `#fff3ec` en 8 templates), `texto-sobre-aviso` (`#7a5800`, ya
literal en `dashboard.html`/`gestionar_viaje.html`), `texto-sobre-oscuro`
(`#ffffff`, el texto real del sidebar en `admin.css`).

Un cuarto token, `activo` (`#f16a30`, desde `color.state.active`), se sumó
en una tanda de limpieza posterior tras confirmar con grep que el concepto
"ítem/paso actualmente activo o seleccionado" tiene uso real y repetido:
`.nav-item-active` en `static/css/admin.css` (17 links del sidebar en
`base_admin.html`), `.pagination .page-item.active` en
`templates/admin/viajes.html`, y `.tl-step.active` en
`templates/cliente/viaje_detalle.html` — los tres hardcodeados hoy a
`#E86A2C` (el naranja de marca anterior a la paleta de Adrián, sin ninguna
relación con el catálogo de tokens). El valor de Adrián para este rol
coincide con `principal`/`peligro` (`#f16a30`) — se creó igual como token
propio porque nombra un **rol** distinto ("esto es el color de lo
activo/seleccionado"), no solo repite un valor; una futura tanda de
aplicación es la que reemplazaría esos hardcodeos por `var(--activo)`.
`templates/base_cliente.html` usa el mismo concepto pero con su propia
variable local `--mt-orange` (fuera del catálogo de `tokens/`, no se tocó).

Un quinto token, `error-real` (`#dc2626`), se agregó durante la migración
completa de colores hardcodeados a tokens (ver commit correspondiente).
Los banners de error de `login.html` y `base_cliente.html` (`.mt-alert-error`)
usaban el rojo real `#DC2626` — distinto de `peligro`, que hoy vale
`#f16a30` (el mismo naranja que `principal`, porque la paleta de Adrián no
define ningún rojo propio). Migrar esos 2 banners a `var(--peligro)`
habría cambiado el color visible (rojo → naranja), violando la regla de
"sin cambio visual" de esa migración. Se creó `error-real` como token
separado, fijado en el rojo que ya tenían esos banners, para lograr las
dos cosas a la vez: cero hex hardcodeado y cero cambio de color. Si algún
día `peligro` recupera un rojo propio (distinto de `principal`), vale la
pena revisar si `error-real` sigue siendo necesario o puede fusionarse.

**Huecos que quedaron sin cambio a propósito** (Adrián no los cubre):
`panel-suave`, `atenuado`, `principal-oscuro`, `info`, `barra-lateral-suave`.
Dos consecuencias visuales directas de estos huecos, ya conocidas y
aceptadas al aprobar el plan:
- `peligro` quedó idéntico a `principal` (`#f16a30`) — Adrián no define
  ningún rojo en su sistema.
- `principal-oscuro` (hover) sigue azul mientras `principal` es naranja.
- El degradé del sidebar (`--sidebar` → `--sidebar-soft`) pasa de
  navy→navy-oscuro a gris→navy, un salto de tono en vez de un degradé suave.

### Radios y sombra

`radio-lg` pasó de 10px a 12px; se agregaron `radio-xl` (16px) y `radio-2xl`
(20px) por tener uso real confirmado (16px y 20px ya aparecían hardcodeados
en templates). `shadow`/`sombra-lg` (el único par con efecto visual real hoy,
vía `.panel` en `admin.css`) se actualizó a la sombra sutil de Adrián
(`0px 4px 12px rgba(0,0,0,.03)`). Huecos sin cambio: `radius` (18px),
`radio-sm`, `radio-md`, `radio-pill`, `sombra-sm`, `sombra-md`.

### Tokens de Adrián evaluados y no aplicados

Estos valores de su JSON no tienen ningún uso real hoy en el código (cero
apariciones vía grep) — documentados acá en vez de crearse como tokens
nuevos sin consumidor:

| Token de Adrián | Valor | Por qué no se aplicó |
|---|---|---|
| `color.background.icon-circle` | `#f7fafc` | Los círculos de íconos KPI (`admin.css:172-189`) usan un fondo tenue *distinto por categoría* (`.kpi-icon.primary/success/warning/info/neutral`), no un fondo único compartido — aplicarlo implicaría rediseñar esos 5 selectores, más que traducir un valor. |
| `color.text.body` | `#000000` | No existe hoy un rol "texto de cuerpo" distinto de `texto` (headings) que reemplazar. |
| `color.text.on-neutral` | `#e8e8e3` | El texto secundario del sidebar hoy es `rgba(255,255,255,.82)` (translúcido), no un gris sólido — no hay match real. |
| `color.text.muted` | `#1a202c` | Cero apariciones en el código. **Ojo:** el nombre es un falso amigo — no corresponde a nuestro `atenuado` (texto secundario general, `#64748b`); el de Adrián es un casi-negro específico de un botón puntual. No auto-mapear por el nombre. |

### Tipografía — referencia para una tanda futura, no aplicada

`typography.fontFamily.primary = "Inter"` ya coincide con `fuente-staff`
(`Inter, "Segoe UI", Arial, sans-serif`) — sin cambio. El resto de su catálogo
de tipografía son combos compuestos (familia+peso+tamaño) sin equivalente 1:1
en la escala plana `texto-*`/`peso-*` actual, y algunos valores no existen
todavía en la escala (28px, peso 500 "medium"). Referencia para cuando se
haga esa tanda:

| Token de Adrián | Familia | Peso | Tamaño |
|---|---|---|---|
| `heading.h1` | Inter | 700 (bold) | 28px |
| `heading.h2` | Inter | 700 (bold) | 22px |
| `heading.h3` | Inter | 600 (semibold) | 18px |
| `body.base` | Inter | 400 (regular) | 14px |
| `body.medium` | Inter | 500 (medium — no existe en `peso-*` hoy) | 14px |
| `body.small` | Inter | 400 (regular) | 12px |
| `label.badge` | Inter | 600 (semibold) | 11px |
| `label.kpi` | Inter | 700 (bold) | 24px |
| `label.eyebrow` | Inter | 600 (semibold) | 11px |

## Circuito automático desde `mercatoria-design`

Desde `.github/workflows/sync-design-tokens.yml` existe una GitHub Action
que automatiza la traducción que antes se hacía a mano (commit `11b96aa`).

**Qué la dispara:**
- Manualmente, desde la pestaña **Actions** → "Sync design tokens" →
  **Run workflow** (`workflow_dispatch`).
- Automáticamente vía `repository_dispatch` de tipo `tokens-actualizados`,
  que en el futuro va a enviar el repo `mercatoria-design` cuando Adrián
  empuje un JSON nuevo (esa mitad — la que dispara desde el otro repo — se
  monta en otra tanda aparte; esta Action ya está lista para recibirla).

**Qué hace, paso a paso:**
1. Trae `mercatoria-design-tokens.json` desde la raíz del repo privado
   `github.com/frankoaldos11-dotcom/mercatoria-design` (branch `main`),
   usando el secreto `DESIGN_SYNC_TOKEN` para el checkout cruzado.
2. Corre `tokens/scripts/sync-adrian-tokens.mjs`, que aplica la **misma
   tabla de mapeo** usada a mano la primera vez (Adrián → vocabulario
   español), preservando huecos con su valor actual — nunca inventa
   nombres nuevos.
3. Regenera `static/css/tokens.css` con Style Dictionary.
4. Si algo cambió, comitea y pushea a `main` con el `GITHUB_TOKEN` del
   propio workflow (no necesita el PAT para esto). Render redespliega solo
   al ver el push nuevo, igual que con cualquier commit manual.

**Qué pasa con tokens nuevos que Adrián agregue:** el script solo
re-aplica valores a tokens que ya tienen un mapeo conocido (la tabla vive
en `tokens/scripts/sync-adrian-tokens.mjs`, no acá, para no mantener dos
copias que se desincronicen). Si Adrián agrega una clave que el script no
reconoce, **no crea un token solo** — la deja fuera, la anota en
`tokens/adrian-sync-report.md` (se comitea junto con los tokens si hubo
cambios) y la marca como `::warning::` en el log del run. Decidir si esa
clave nueva merece un token español pasa por el mismo proceso manual de
siempre: grep contra el código para confirmar uso real (ver la sección de
arriba, "Tokens de Adrián evaluados y no aplicados") y, recién ahí, agregar
una fila nueva a la tabla de mapeo del script.

**Secreto necesario:** `DESIGN_SYNC_TOKEN`, un fine-grained PAT con acceso
de solo lectura (`Contents: Read-only`) únicamente al repo
`mercatoria-design`, configurado en
`Mercatoria-Trucks → Settings → Secrets and variables → Actions`. No le da
ningún permiso sobre `Mercatoria-Trucks` — el commit de vuelta usa el
`GITHUB_TOKEN` automático del workflow.

## Qué NO cubre esta ampliación

- No se migraron los 202 `var(--nombre-viejo)` existentes en `admin.css` y
  templates a los nombres nuevos en español — quedan resueltos vía
  `color-legacy.json` (ver arriba). Migrarlos es una tanda aparte, opcional.
- No se tokenizó la totalidad de los valores en uso (hay ~26 espaciados y
  ~40 tamaños de fuente distintos en el sitio hoy; solo se nombraron los
  dominantes de cada escala). Los valores fuera de la escala siguen
  hardcodeados hasta que se decida si entran o no en una escala futura.
- No se tokenizaron los anillos de foco de marca (`rgba(232,106,44,*)`) ni
  los overlays neutros menos frecuentes — son candidatos a su propio
  `sombra-focus` o mixin, pendiente de una pasada aparte.
- Ningún template ni `admin.css` consume todavía los tokens de tipografía,
  espaciado, radios o sombras agregados en la tanda anterior. Esa
  sustitución es la siguiente tanda posible, no parte de esta.
