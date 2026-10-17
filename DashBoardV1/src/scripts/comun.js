// Utilidades compartidas: datos cargados, formato, colores, selección y el modelo final.
import * as d3 from "d3";

export const QUIETO = matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Datos verificados (ver datos.js). Se asigna una vez con fijarDatos. */
export let D = null;
export function fijarDatos(d) { D = d; }

/* ── Colores ──────────────────────────────────────────────────────────── */
export const RAMPA = ["#CBA03A", "#B08528", "#946A1C", "#775114", "#5A3A0D", "#3F280A"];
export const CORTES = [3, 3.5, 4, 4.5, 5];
export const clase = (v) => d3.bisectRight(CORTES, v);
export const colorV = (v) => RAMPA[clase(v)];
export const COLORES = { MUN: "#9AA1A8", MIX: "#5B636B", J: "#2F6FD6", K: "#3A9E6E", E_JK: "#C27A12" };
export const NOMBRES = { MUN: "Media municipal", MIX: "MIX (referencia)", J: "J, lluvia y región", K: "K, verdor relativo", E_JK: "E_JK, entrega" };
export const TINTA = "#1C2733", GRIS = "#5A6570", LINEA = "#E3E7E0", MARINO = "#022448", PAJA = "#E3C772", VERDE = "#95BD59";

/* ── Formato (es-MX) ──────────────────────────────────────────────────── */
export const f = (v, d = 2) =>
  v == null || !isFinite(v) ? "—" : v.toLocaleString("es-MX", { minimumFractionDigits: d, maximumFractionDigits: d });
export const fs = (v, d = 2) => {
  const t = f(Math.abs(v), d);
  return (Number(t.replace(/,/g, "")) === 0 ? "" : v > 0 ? "+" : "−") + t;
};
export const pct = (v, d = 0) => `${f(v * 100, d)} %`;
export const corto = (m) => m.replace(" de Mariano Arista", "").replace(" de Hinojosa", "");
export const r4 = (v) => Math.round(v * 1e4) / 1e4;
export const grupoTxt = (g) => g.replace("_", " ");

/* ── Selección compartida entre mapa, tabla, ficha, ejecución y boleta ─── */
export const estado = { seleccion: null };
const oyentes = [];
export function alSeleccionar(fn) { oyentes.push(fn); }
export function seleccionar(id, origen) {
  estado.seleccion = id;
  oyentes.forEach((fn) => fn(id, origen));
}

/* ── Tooltip único ────────────────────────────────────────────────────── */
let tip = null;
export function mostrarTip(html, ev) {
  tip ??= document.getElementById("tip");
  tip.innerHTML = html;
  tip.style.opacity = 1;
  const r = tip.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
  tip.style.left = `${Math.max(8, x)}px`;
  tip.style.top = `${Math.max(8, y)}px`;
}
export function ocultarTip() { if (tip) tip.style.opacity = 0; }
export function htmlParcela(p) {
  return p.oculta
    ? `<b>${p.id}</b> <span class="s">${p.mun}</span><br>Estimado <b class="num">${f(p.pred)}</b> t/ha<br><span class="s">80 %: ${f(p.lo80)} a ${f(p.hi80)}. ${f(p.ha)} ha</span>`
    : `<b>${p.id}</b> <span class="s">${p.mun}</span><br>Conocido <b class="num">${f(p.obs)}</b> t/ha<br><span class="s">${f(p.ha)} ha</span>`;
}
/** Tooltip con ratón; en pantallas táctiles el toque selecciona. */
export function conTip(sel, html) {
  sel.on("pointerenter pointermove", (ev, d) => { if (ev.pointerType !== "touch") mostrarTip(html(d), ev); })
    .on("pointerleave", ocultarTip);
}

/* ── Geometría ────────────────────────────────────────────────────────── */
/** Polígonos en UTM 14N (metros) como GeoJSON plano. */
export const featureDe = (p) => ({ type: "Feature", properties: { id: p.id }, geometry: { type: "MultiPolygon", coordinates: p.poly.map((r) => [r]) } });
export const cajaUTM = (x0, y0, x1, y1) => ({ type: "Feature", geometry: { type: "Polygon", coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });

/** Surcos (rayado a 45°) por clase de rendimiento. Devuelve una función para seguir el zoom. */
export function surcos(defs, pref, tam = 6, fondo = "#fff") {
  RAMPA.forEach((c, i) => {
    const pt = defs.append("pattern").attr("id", `${pref}-s${i}`).attr("patternUnits", "userSpaceOnUse")
      .attr("width", tam).attr("height", tam).attr("patternTransform", "rotate(45)");
    pt.append("rect").attr("width", tam).attr("height", tam).attr("fill", fondo);
    pt.append("rect").attr("width", tam * 0.56).attr("height", tam).attr("fill", c);
  });
  return (k = 1) => defs.selectAll("pattern").filter(function () { return this.id.startsWith(pref + "-s"); })
    .attr("patternTransform", `rotate(45) scale(${1 / k})`);
}
export const rellenoDe = (p, pref) => (p.oculta ? `url(#${pref}-s${clase(p.pred)})` : colorV(p.obs));

/* ── Huellas ──────────────────────────────────────────────────────────── */
export async function sha256hex(datos) {
  if (!(window.crypto && crypto.subtle)) return null;
  const b = typeof datos === "string" ? new TextEncoder().encode(datos) : datos;
  const h = await crypto.subtle.digest("SHA-256", b);
  return [...new Uint8Array(h)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/* ── Estado de la API en AWS ──────────────────────────────────────────── */
export const NUBE = (async () => {
  if (!/^https?:$/.test(location.protocol)) return null;
  try {
    const r = await fetch("/api/salud", { cache: "no-store" });
    if (!r.ok) return null;
    const s = await r.json();
    return s && s.estado === "ok" ? s : null;
  } catch {
    return null;
  }
})();

/* ── El modelo final, como en el cuaderno 04 ──────────────────────────── */
/** Para una parcela conocida se excluye su propio rendimiento (como si estuviera oculta). */
export function modeloFinal(p) {
  const M = D.M;
  const ent = p.oculta ? D.REP : D.REP.filter((q) => q.id !== p.id);
  const delMun = ent.filter((q) => q.mun === p.mun);
  const MUN = delMun.length ? d3.mean(delMun, (q) => q.obs) : d3.mean(ent, (q) => q.obs);
  const dist = ent.map((q) => ({ q, d: Math.hypot(q.x - p.x, q.y - p.y) })).sort((a, b) => a.d - b.d).slice(0, M.idw.k);
  const w = dist.map((o) => 1 / Math.max(o.d, M.idw.piso_m) ** M.idw.potencia);
  const sw = d3.sum(w);
  const vecinas = dist.map((o, i) => ({ id: o.q.id, d: o.d, w: w[i] / sw, obs: o.q.obs, q: o.q }));
  const IDW = d3.sum(vecinas, (v) => v.w * v.obs);
  const MIX = 0.5 * MUN + 0.5 * IDW;
  const z = p.k1 == null ? 0 : (p.k1 - M.K.mediana) / M.K.escala;
  const K = MIX + M.K.beta * z;
  const J = M.J[p.grupo] + M.J.pendiente * p.anom;
  return { MUN, nMun: delMun.length, IDW, vecinas, MIX, z, K, J, E: 0.5 * J + 0.5 * K };
}

/** Rinde una función de dibujo al tamaño real del contenedor y la repite al cambiar de ancho. */
export function alAncho(el, dibujar) {
  let ancho = 0;
  const ro = new ResizeObserver(() => {
    const w = Math.round(el.clientWidth);
    if (w && Math.abs(w - ancho) > 2) { ancho = w; dibujar(w); }
  });
  ro.observe(el);
}
