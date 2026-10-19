// Portada: relieve real de la zona como fondo y lámina de las 197 parcelas.
import * as d3 from "d3";
import { createTimeline, stagger, svg as asvg } from "animejs";
import { D, QUIETO, htmlParcela, mostrarTip, ocultarTip, seleccionar, alSeleccionar } from "./comun.js";

/** Curvas de nivel del modelo de elevación (INEGI, muestreado cada ~660 m). */
function relieve() {
  const R = D.REL;
  const v = R.valores.slice();
  // rellena los huecos del borde con el promedio de sus vecinos
  for (let pasada = 0; pasada < 30 && v.some((x) => x == null); pasada++) {
    const copia = v.slice();
    for (let i = 0; i < v.length; i++) {
      if (v[i] != null) continue;
      const fx = i % R.nx, fy = Math.floor(i / R.nx);
      const vs = [[fx - 1, fy], [fx + 1, fy], [fx, fy - 1], [fx, fy + 1]]
        .filter(([x, y]) => x >= 0 && y >= 0 && x < R.nx && y < R.ny).map(([x, y]) => copia[y * R.nx + x]).filter((x) => x != null);
      if (vs.length) v[i] = d3.mean(vs);
    }
  }
  const [lo, hi] = d3.extent(v);
  const umbrales = d3.range(Math.ceil(lo / 50) * 50, hi, 50);
  const svg = d3.select("#relieve").attr("viewBox", `0 0 ${R.nx - 1} ${R.ny - 1}`);
  const ruta = d3.geoPath(d3.geoIdentity().translate([-0.5, -0.5]));
  svg.selectAll("path").data(d3.contours().size([R.nx, R.ny]).smooth(true).thresholds(umbrales)(v)).join("path")
    .attr("d", ruta).attr("fill", "none").attr("vector-effect", "non-scaling-stroke")
    .attr("stroke", (d) => (d.value % 250 === 0 ? "rgba(149,189,89,.24)" : "rgba(196,214,236,.10)"))
    .attr("stroke-width", (d) => (d.value % 250 === 0 ? 1.1 : 0.8));
}

function trazoNormalizado(poly, tam = 100, mg = 8) {
  const pts = poly.flat();
  const [x0, x1] = d3.extent(pts, (c) => c[0]), [y0, y1] = d3.extent(pts, (c) => c[1]);
  const esc = (tam - 2 * mg) / Math.max(x1 - x0, y1 - y0);
  const ox = mg + ((tam - 2 * mg) - (x1 - x0) * esc) / 2, oy = mg + ((tam - 2 * mg) - (y1 - y0) * esc) / 2;
  return poly.map((r) => "M" + r.map(([x, y]) => `${(ox + (x - x0) * esc).toFixed(1)},${(oy + (y1 - y) * esc).toFixed(1)}`).join("L") + "Z").join("");
}

function lamina() {
  const cont = d3.select("#lamina");
  D.MUNICIPIOS.forEach(([mun, ps]) => {
    const g = cont.append("div").attr("class", "grupo");
    const n59 = ps.filter((p) => p.oculta).length;
    g.append("div").attr("class", "tit").html(`<b>${mun}</b>${ps.length} ${ps.length === 1 ? "parcela" : "parcelas"}${n59 ? `, ${n59} sin dato` : ""}`);
    const cel = g.append("div").attr("class", "celdas");
    [...ps].sort((a, b) => d3.ascending(a.id, b.id)).forEach((p) => {
      const b = cel.append("button").attr("class", "pz" + (p.oculta ? " est" : "")).attr("data-id", p.id).attr("tabindex", "-1")
        .attr("aria-label", `${p.id}, ${mun}, ${p.oculta ? "sin dato, estimada por el modelo" : "con rendimiento conocido"}`);
      b.append("svg").attr("viewBox", "0 0 100 100").attr("aria-hidden", "true").append("path").attr("d", trazoNormalizado(p.poly));
      b.on("pointerenter pointermove", (ev) => { if (ev.pointerType !== "touch") mostrarTip(htmlParcela(p), ev); })
        .on("pointerleave", ocultarTip)
        .on("click", () => {
          seleccionar(p.id, "lamina");
          document.getElementById(p.oculta ? "estimaciones" : "tablero").scrollIntoView({ behavior: QUIETO ? "auto" : "smooth" });
        });
    });
  });
  alSeleccionar((id) => d3.selectAll(".pz").classed("sel", function () { return this.dataset.id === id; }));

  // el único momento coreografiado al cargar: se trazan las 59 y el contador llega a 59
  const contador = document.getElementById("contador");
  const est = [...document.querySelectorAll(".pz.est path")];
  if (QUIETO) { contador.textContent = "59"; return; }
  est.forEach((p) => { p.style.fillOpacity = 0; });
  const cuenta = { n: 0 };
  createTimeline({ defaults: { ease: "outQuad" } })
    .add(asvg.createDrawable(est), { draw: ["0 0", "0 1"], duration: 1000, delay: stagger(14) }, 250)
    .add(est, { fillOpacity: [0, 1], duration: 600, delay: stagger(10) }, 900)
    .add(cuenta, { n: [0, 59], duration: 1500, onUpdate: () => { contador.textContent = Math.round(cuenta.n); } }, 250);
}

export function iniciarPortada() {
  relieve();
  lamina();
}
