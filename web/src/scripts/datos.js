// Carga los datos publicados en S3 y comprueba su huella SHA-256 contra el manifiesto.
import * as d3 from "d3";
import { sha256hex } from "./comun.js";

const ARCHIVOS = ["parcelas", "modelo", "vitrina", "evidencia", "relieve"];

export class DatosAlterados extends Error {}

async function traer(ruta) {
  const r = await fetch(`/${ruta}`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${ruta}: respuesta ${r.status}`);
  return r.arrayBuffer();
}

export async function cargarDatos() {
  const man = JSON.parse(new TextDecoder().decode(await traer("datos/manifiesto.json")));
  const verificacion = {};
  const leidos = await Promise.all(ARCHIVOS.map(async (n) => {
    const ruta = `datos/${n}.json`;
    const buf = await traer(ruta);
    const h = await sha256hex(buf);
    const esperado = man.archivos[ruta]?.sha256;
    verificacion[ruta] = h === null ? null : h === esperado;
    if (h !== null && h !== esperado) throw new DatosAlterados(`${ruta} no coincide con el manifiesto`);
    return JSON.parse(new TextDecoder().decode(buf));
  }));
  const [P, M, VIT, EV, REL] = leidos;
  const EST = P.filter((p) => p.oculta).sort((a, b) => d3.ascending(a.id, b.id));
  const REP = P.filter((p) => !p.oculta).sort((a, b) => d3.ascending(a.id, b.id));
  const MUNICIPIOS = d3.groups(P, (p) => p.mun).sort((a, b) => b[1].length - a[1].length || d3.ascending(a[0], b[0]));
  return {
    P, M, VIT, EV, REL, MAN: man, verificacion, EST, REP, MUNICIPIOS,
    porId: new Map(P.map((p) => [p.id, p])),
    COLECCION: { type: "FeatureCollection", features: P.map((p) => ({ type: "Feature", properties: { id: p.id }, geometry: { type: "MultiPolygon", coordinates: p.poly.map((r) => [r]) } })) },
  };
}

/** Comprueba un archivo de descarga contra el manifiesto (se usa en vistas previas y en el pie). */
export async function verificarArchivo(ruta, man) {
  const buf = await traer(ruta);
  const h = await sha256hex(buf);
  return { buf, h, ok: h === null ? null : h === man.archivos[ruta]?.sha256 };
}
