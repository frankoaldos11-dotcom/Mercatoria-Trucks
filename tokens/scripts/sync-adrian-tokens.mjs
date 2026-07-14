#!/usr/bin/env node
// Traduce tokens/mercatoria-design-tokens.json (formato plano value/type de Adrian)
// al vocabulario espanol de tokens/color.json y tokens/effects.json.
// Misma logica aplicada a mano en el commit 11b96aa: solo re-aplica valores
// a tokens ya mapeados; nunca inventa nombres para claves nuevas.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TOKENS_DIR = join(__dirname, "..");

const ADRIAN_JSON_PATH = join(TOKENS_DIR, "mercatoria-design-tokens.json");
const COLOR_JSON_PATH = join(TOKENS_DIR, "color.json");
const EFFECTS_JSON_PATH = join(TOKENS_DIR, "effects.json");
const REPORT_PATH = join(TOKENS_DIR, "adrian-sync-report.md");

// Tabla de mapeo — misma traduccion aplicada a mano en el commit 11b96aa.
// origen: ruta punteada dentro de "mercatoria.*" en el JSON de Adrian.
// destino(s): clave(s) correspondiente(s) en color.json / effects.json.
const MAPEO_COLOR = [
  { origen: "color.background.page", destino: ["fondo"] },
  { origen: "color.background.card", destino: ["panel"] },
  { origen: "color.text.primary", destino: ["texto"] },
  { origen: "color.brand.primary", destino: ["principal"] },
  { origen: "color.brand.neutral", destino: ["borde"] },
  { origen: "color.state.danger", destino: ["peligro"] },
  { origen: "color.state.success", destino: ["exito"] },
  { origen: "color.state.warning", destino: ["aviso"] },
  { origen: "color.brand.dark", destino: ["barra-lateral"] },
  { origen: "color.background.primary-light", destino: ["fondo-naranja-suave"] },
  { origen: "color.text.warning", destino: ["texto-sobre-aviso"] },
  { origen: "color.text.on-dark", destino: ["texto-sobre-oscuro"] },
  { origen: "color.state.active", destino: ["activo"] },
];

const MAPEO_EFFECTS = [
  { origen: "borderRadius.sm", destino: ["radio-sm"] },
  { origen: "borderRadius.md", destino: ["radio-md"] },
  { origen: "borderRadius.lg", destino: ["radio-lg"] },
  { origen: "borderRadius.xl", destino: ["radio-xl"] },
  { origen: "borderRadius.2xl", destino: ["radio-2xl"] },
  { origen: "shadow.card", destino: ["shadow", "sombra-lg"] },
];

// Claves de Adrian ya evaluadas a mano (commit 11b96aa / tokens/README.md)
// que deliberadamente NO tienen un token espanol propio, para no repetir el
// warning de "revisar con grep" en cada corrida sobre algo ya resuelto.
const EXCLUSIONES_CONOCIDAS = {
  "color.brand.secondary": "mismo valor que color.state.warning, ya cubierto via `aviso`",
  "color.brand.success": "mismo valor que color.state.success, ya cubierto via `exito`",
  "color.background.icon-circle": "sin uso real en el codigo (ver tokens/README.md)",
  "color.text.body": "sin uso real en el codigo (ver tokens/README.md)",
  "color.text.on-neutral": "sin uso real en el codigo (ver tokens/README.md)",
  "color.text.muted": "sin uso real en el codigo — falso amigo de `atenuado` (ver tokens/README.md)",
};

// Raices del JSON de Adrian que se inspeccionan para detectar claves nuevas
// sin mapear (todo lo que cuelgue de estas ramas debe estar en alguna fila
// de MAPEO_COLOR/MAPEO_EFFECTS o en EXCLUSIONES_CONOCIDAS, o se reporta como
// pendiente de revision).
const RAICES_INSPECCIONADAS = ["color", "borderRadius", "shadow"];

function normalizarValor(valor) {
  return typeof valor === "string" && valor.startsWith("#") ? valor.toLowerCase() : valor;
}

function leer(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function resolverRuta(obj, rutaPunteada) {
  const partes = rutaPunteada.split(".");
  let actual = obj;
  for (const parte of partes) {
    if (actual == null || typeof actual !== "object" || !(parte in actual)) {
      return undefined;
    }
    actual = actual[parte];
  }
  return actual;
}

function recolectarHojas(obj, prefijo, acumulador) {
  if (obj == null || typeof obj !== "object") return;
  if ("value" in obj && "type" in obj) {
    acumulador.push(prefijo);
    return;
  }
  for (const [clave, valor] of Object.entries(obj)) {
    recolectarHojas(valor, prefijo ? `${prefijo}.${clave}` : clave, acumulador);
  }
}

function main() {
  const adrian = leer(ADRIAN_JSON_PATH).mercatoria;
  const colorTokens = leer(COLOR_JSON_PATH);
  const effectsTokens = leer(EFFECTS_JSON_PATH);

  const cambios = [];
  const sinCambio = [];

  for (const [tokens, mapeo] of [
    [colorTokens, MAPEO_COLOR],
    [effectsTokens, MAPEO_EFFECTS],
  ]) {
    for (const { origen, destino } of mapeo) {
      const nodo = resolverRuta(adrian, origen);
      if (!nodo || nodo.value === undefined) {
        sinCambio.push({ origen, destino, motivo: "no vino en esta entrega (hueco)" });
        continue;
      }
      const valorNuevo = normalizarValor(nodo.value);
      for (const clave of destino) {
        const valorViejo = normalizarValor(tokens[clave]?.$value);
        if (valorViejo === valorNuevo) {
          sinCambio.push({ origen, destino: clave, motivo: "sin cambio de valor" });
          continue;
        }
        if (!tokens[clave]) {
          // Fila mapeada pero token destino todavia no existe en el catalogo:
          // no se crea solo — requiere alta manual (mismo criterio que tokens nuevos).
          sinCambio.push({ origen, destino: clave, motivo: "token destino no existe todavia — alta manual requerida" });
          continue;
        }
        tokens[clave].$value = valorNuevo;
        cambios.push({ origen, destino: clave, de: valorViejo, a: valorNuevo });
      }
    }
  }

  // Deteccion de claves nuevas de Adrian sin mapeo conocido (excluyendo lo
  // ya evaluado a mano y documentado en EXCLUSIONES_CONOCIDAS).
  const origenesMapeados = new Set([...MAPEO_COLOR, ...MAPEO_EFFECTS].map((m) => m.origen));
  const hojas = [];
  for (const raiz of RAICES_INSPECCIONADAS) {
    recolectarHojas(adrian[raiz], raiz, hojas);
  }
  const noMapeadas = hojas.filter(
    (ruta) => !origenesMapeados.has(ruta) && !(ruta in EXCLUSIONES_CONOCIDAS)
  );

  if (cambios.length > 0) {
    writeFileSync(COLOR_JSON_PATH, JSON.stringify(colorTokens, null, 2) + "\n");
    writeFileSync(EFFECTS_JSON_PATH, JSON.stringify(effectsTokens, null, 2) + "\n");
  }

  const reporte = generarReporte(cambios, sinCambio, noMapeadas);
  writeFileSync(REPORT_PATH, reporte);

  console.log(reporte);
  if (process.env.GITHUB_STEP_SUMMARY) {
    writeFileSync(process.env.GITHUB_STEP_SUMMARY, reporte, { flag: "a" });
  }
  for (const ruta of noMapeadas) {
    console.log(`::warning::Token nuevo de Adrian sin mapear: ${ruta} — revisar a mano con grep antes de crear un token espanol.`);
  }
}

function generarReporte(cambios, sinCambio, noMapeadas) {
  const lineas = [`# Reporte de sync de tokens de diseno — ${new Date().toISOString().slice(0, 10)}`, ""];

  lineas.push("## Tokens actualizados");
  if (cambios.length === 0) {
    lineas.push("Ninguno — el JSON de Adrian no trajo valores distintos a los ya aplicados.");
  } else {
    for (const c of cambios) {
      lineas.push(`- \`${c.destino}\` (${c.origen}): \`${c.de}\` -> \`${c.a}\``);
    }
  }

  lineas.push("", "## Tokens mapeados sin cambio");
  if (sinCambio.length === 0) {
    lineas.push("Ninguno.");
  } else {
    for (const s of sinCambio) {
      lineas.push(`- \`${s.destino}\` (${s.origen}): ${s.motivo}`);
    }
  }

  lineas.push("", "## Claves nuevas de Adrian sin aplicar (requieren revision manual)");
  if (noMapeadas.length === 0) {
    lineas.push("Ninguna — todas las claves de color/radio/sombra de Adrian ya tienen mapeo conocido.");
  } else {
    for (const ruta of noMapeadas) {
      lineas.push(`- \`${ruta}\` — no tiene token espanol asociado todavia. No se crea automaticamente: hay que confirmar con grep si tiene uso real en el codigo antes de nombrarlo (ver tokens/README.md, seccion "Tokens de Adrian evaluados y no aplicados").`);
    }
  }

  lineas.push("");
  return lineas.join("\n");
}

main();
