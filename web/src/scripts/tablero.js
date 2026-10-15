// Tablero: mapa con zoom, cifras del reto y rendimiento por municipio.
import * as d3 from "d3";
import {
  D, RAMPA, TINTA, GRIS, LINEA, f, pct, corto, surcos, rellenoDe, featureDe, conTip, htmlParcela,
  seleccionar, alSeleccionar, estado, alAncho,
} from "./comun.js";

function mapa() {
  const svg = d3.select("#mapa");
  const caja = svg.node().getBoundingClientRect();
  const movil = matchMedia("(max-width: 760px)").matches;
  const W = 800, H = Math.max(520, Math.round((W * caja.height) / Math.max(caja.width, 300)));
  const u = W / Math.max(300, caja.width); // unidades del lienzo por píxel de pantalla
  svg.attr("viewBox", `0 0 ${W} ${H}`).attr("preserveAspectRatio", "xMidYMid meet");
  const escPat = surcos(svg.append("defs"), "m", 6 * u);
  const proy = d3.geoIdentity().reflectY(true).fitExtent([[24 * u, 78 * u], [W - 60 * u, H - (movil ? 130 : 24) * u]], D.COLECCION);
  const ruta = d3.geoPath(proy);
  const centro = (p) => proy([p.x, p.y]);
  const g = svg.append("g");
  const polis = g.append("g").selectAll("path").data(D.P).join("path")
    .attr("d", (p) => ruta(featureDe(p))).attr("fill", (p) => rellenoDe(p, "m"))
    .attr("stroke", TINTA).attr("stroke-width", 0.6).attr("vector-effect", "non-scaling-stroke").attr("opacity", 0);
  const simbolos = g.append("g").selectAll("circle").data(D.P).join("circle")
    .attr("cx", (p) => centro(p)[0]).attr("cy", (p) => centro(p)[1]).attr("r", 4.2 * u)
    .attr("fill", (p) => rellenoDe(p, "m")).attr("stroke", TINTA).attr("stroke-width", 0.6 * u);
  const rot = g.append("g").selectAll("text").data(D.MUNICIPIOS).join("text")
    .attr("x", (d) => d3.mean(d[1], (p) => centro(p)[0])).attr("text-anchor", "middle")
    .attr("font-weight", 650).attr("fill", "#3E4A56").attr("paint-order", "stroke").attr("stroke", "#fff")
    .text((d) => corto(d[0]));
  const resaltado = g.append("g");
  const barra = svg.append("g").attr("transform", `translate(${16 * u},${H - 18 * u - (movil ? 112 * u : 0)})`);
  let k = 1, filtro = "todas";
  const visible = (d) => (filtro === "todas" || (filtro === "est") === d.oculta ? 1 : 0.12);
  const pintar = () => {
    const poligonos = k >= 7;
    simbolos.attr("r", (4.2 * u) / k).attr("stroke-width", (0.6 * u) / k).attr("opacity", (d) => (poligonos ? 0 : 1) * visible(d));
    polis.attr("opacity", (d) => (poligonos ? 1 : 0) * visible(d));
    rot.attr("font-size", (12.5 * u) / k).attr("stroke-width", (3.5 * u) / k)
      .attr("y", (d) => d3.min(d[1], (p) => centro(p)[1]) - (10 * u) / k)
      .attr("opacity", (d) => (d[1].length >= 9 || k >= 3 ? 1 : 0));
    resaltado.selectAll("circle").attr("r", (9 * u) / k).attr("stroke-width", (2.4 * u) / k);
    escPat(k);
    // escala gráfica en metros reales (UTM)
    const mpu = 1 / (proy.scale() * k);
    const L = [10000, 5000, 2000, 1000, 500, 200].find((m) => m / mpu <= 130 * u) || 200;
    barra.selectAll("*").remove();
    barra.append("rect").attr("width", L / mpu).attr("height", 4 * u).attr("fill", TINTA);
    barra.append("rect").attr("width", L / mpu / 2).attr("height", 4 * u).attr("fill", "#fff").attr("stroke", TINTA).attr("stroke-width", 0.8 * u);
    barra.append("text").attr("y", -6 * u).attr("font-size", 12 * u).attr("fill", GRIS).text(L >= 1000 ? `${L / 1000} km` : `${L} m`);
  };
  const zoom = d3.zoom().scaleExtent([1, 80]).translateExtent([[-200, -200], [W + 200, H + 200]])
    .filter((ev) => !ev.button && (ev.type !== "touchstart" || ev.touches.length > 1))
    .on("zoom", (ev) => { k = ev.transform.k; g.attr("transform", ev.transform); pintar(); });
  svg.call(zoom).on("wheel.zoom", null).on("dblclick.zoom", null);
  svg.on("wheel", (ev) => {
    if (!(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    zoom.scaleBy(svg.transition().duration(150), ev.deltaY < 0 ? 1.3 : 1 / 1.3, d3.pointer(ev));
  }, { passive: false });
  // los botones acercan sobre la parcela elegida (la del anillo azul)
  document.querySelectorAll(".mapa-zoom button").forEach((b) => b.addEventListener("click", () => {
    const z = +b.dataset.z;
    if (z === 0) { svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity); return; }
    const nk = Math.max(1, Math.min(80, k * (z > 0 ? 1.8 : 1 / 1.8)));
    if (nk === 1) { svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity); return; }
    const [x, y] = centro(D.porId.get(estado.seleccion));
    svg.transition().duration(350).call(zoom.transform, d3.zoomIdentity.translate(W / 2, H / 2).scale(nk).translate(-x, -y));
  }));
  document.querySelectorAll(".mapa-herr button").forEach((b) => b.addEventListener("click", () => {
    filtro = b.dataset.f;
    document.querySelectorAll(".mapa-herr button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    pintar();
  }));
  for (const sel of [simbolos, polis]) {
    sel.style("cursor", "pointer").on("click", (ev, p) => seleccionar(p.id, "mapa"));
    conTip(sel, htmlParcela);
  }
  const marcar = (id) => {
    const [x, y] = centro(D.porId.get(id));
    resaltado.selectAll("*").remove();
    resaltado.append("circle").attr("cx", x).attr("cy", y).attr("fill", "none").attr("stroke", "#2F6FD6");
    pintar();
  };
  alSeleccionar((id) => marcar(id));
  marcar(estado.seleccion);

  const ley = d3.select("#mapa-ley");
  ley.append("div").style("font-weight", 650).text("Rendimiento (t/ha)");
  const fil = ley.append("div").attr("class", "fil");
  RAMPA.forEach((c) => fil.append("span").attr("class", "sw").style("background", c));
  const eti = ley.append("div").attr("class", "eti");
  ["", "3", "3.5", "4", "4.5", "5"].forEach((t) => eti.append("span").text(t));
  ley.append("div").attr("class", "estado").html(
    `<span><svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="#946A1C" stroke="${TINTA}" stroke-width=".7"/></svg>Conocido</span>
     <span><svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="url(#m-s2)" stroke="${TINTA}" stroke-width=".7"/></svg>Estimado</span>`);
}

function cifras() {
  const obs = D.REP.map((p) => p.obs), pr = D.EST.map((p) => p.pred);
  const filas = [
    ["197", `parcelas en <strong>9 municipios</strong> de Hidalgo, Puebla y Tlaxcala`],
    ["138", `con rendimiento conocido: de ${f(d3.min(obs), 1)} a ${f(d3.max(obs), 1)} t/ha, promedio <strong>${f(d3.mean(obs))}</strong>`],
    ["59", `estimadas por el modelo: de ${f(d3.min(pr), 1)} a ${f(d3.max(pr), 1)} t/ha`],
    [pct(D.EV.varianza_municipio), `de la variación del rendimiento se explica con solo saber el <strong>municipio</strong>`],
    [f(D.EV.escalera.E_JK), `t/ha de error típico esperado por parcela (RMSE en validación cruzada)`],
  ];
  d3.select("#cifras").selectAll("div").data(filas).join("div").attr("class", "cifra")
    .html((d) => `<b class="num">${d[0]}</b><span>${d[1]}</span>`);
}

function tira() {
  const mun = D.MUNICIPIOS.map(([m, ps]) => ({ m, ps, media: d3.mean(ps.filter((p) => !p.oculta), (p) => p.obs) }))
    .sort((a, b) => d3.descending(a.media ?? 0, b.media ?? 0));
  const cont = document.getElementById("tira");
  alAncho(cont, (W) => {
    const angosto = W < 440, fila = 30, mg = { l: Math.min(160, W * (angosto ? 0.42 : 0.36)), r: 14, t: 6, b: 26 };
    const H = mg.t + mun.length * fila + mg.b;
    const svg = d3.select(cont).html("").append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("width", W).attr("height", H);
    const x = d3.scaleLinear([2, 6], [mg.l, W - mg.r]);
    svg.append("g").attr("transform", `translate(0,${H - mg.b})`)
      .call(d3.axisBottom(x).ticks(W < 420 ? 4 : 8).tickSize(-(H - mg.b - mg.t)).tickFormat((d) => f(d, d % 1 ? 1 : 0)))
      .call((a) => a.select(".domain").remove()).call((a) => a.selectAll("line").attr("stroke", LINEA))
      .call((a) => a.selectAll("text").attr("fill", GRIS).attr("font-size", 12.5));
    const g = svg.selectAll(".m").data(mun).join("g").attr("transform", (d, i) => `translate(0,${mg.t + i * fila + fila / 2})`);
    g.append("text").attr("x", mg.l - 10).attr("dy", ".35em").attr("text-anchor", "end").attr("font-size", angosto ? 12.5 : 13.5).attr("fill", TINTA)
      .text((d) => `${corto(d.m)} (${d.ps.length})`);
    g.filter((d) => d.media).append("line").attr("x1", (d) => x(d.media)).attr("x2", (d) => x(d.media)).attr("y1", -10).attr("y2", 10)
      .attr("stroke", TINTA).attr("stroke-width", 2.2);
    const azar = d3.randomLcg(7);
    g.each(function (d) {
      const pts = d3.select(this).selectAll("circle").data(d.ps).join("circle")
        .attr("cx", (p) => x(p.oculta ? p.pred : p.obs)).attr("cy", () => (azar() - 0.5) * 13).attr("r", 3.6)
        .attr("fill", (p) => (p.oculta ? "#fff" : "rgba(28,39,51,.5)")).attr("stroke", (p) => (p.oculta ? "#C27A12" : "none")).attr("stroke-width", 1.7)
        .style("cursor", "pointer").on("click", (ev, p) => seleccionar(p.id, "tira"));
      conTip(pts, htmlParcela);
    });
  });
  const media = (m) => d3.mean(D.REP.filter((p) => p.mun === m), (p) => p.obs);
  document.getElementById("tira-nota").innerHTML =
    `Línea: media de las parcelas conocidas. Círculos huecos: estimadas. El municipio pesa más que cualquier otra variable: Calpulalpan ronda ${f(media("Calpulalpan"), 1)} t/ha y Chignahuapan ${f(media("Chignahuapan"), 1)} t/ha.`;
}

export function iniciarTablero() {
  mapa();
  cifras();
  tira();
}
