// Tablero: mapa satelital con recorrido, cifras del reto y rendimiento por municipio.
import * as d3 from "d3";
import { D, TINTA, GRIS, LINEA, f, pct, corto, conTip, htmlParcela, seleccionar, alAncho } from "./comun.js";
import { mapaSatelite } from "./mapaSatelite.js";
import { iniciarRecorrido } from "./recorrido.js";

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
  const mapa = mapaSatelite();
  cifras();
  tira();
  iniciarRecorrido(mapa);
}
