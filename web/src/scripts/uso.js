// Para qué sirve: boleta de producción de la parcela estimada elegida.
import * as d3 from "d3";
import { D, f, clase, alSeleccionar, estado, alAncho } from "./comun.js";

export function iniciarUso() {
  const el = document.getElementById("boleta");
  let actual = null;
  const pintar = (id) => {
    let p = D.porId.get(id);
    if (!p.oculta) p = D.porId.get(D.VIT.id);
    actual = p;
    const prod = p.ha * p.pred, lo = p.ha * p.lo80, hi = p.ha * p.hi80;
    const totHa = d3.sum(D.EST, (q) => q.ha), totProd = d3.sum(D.EST, (q) => q.ha * q.pred);
    el.innerHTML = `<h3>Evidencia productiva de ${p.id}</h3><p class="nota" style="margin:4px 0 12px">${p.mun}, ${p.edo}. Elige otra parcela estimada en el mapa, la tabla o la lámina.</p>
      <div class="linea"><span>Superficie del polígono</span><b>${f(p.ha)} ha</b></div>
      <div class="linea"><span>Rendimiento estimado</span><b>${f(p.pred)} t/ha</b></div>
      <div class="linea total"><span>Producción estimada</span><b>${f(prod, 1)} t</b></div>
      <div class="linea"><span>Rango 80 % (8 de cada 10 veces)</span><b>${f(lo, 1)} a ${f(hi, 1)} t</b></div>
      <div class="linea"><span>Escenario prudente: límite inferior</span><b>${f(lo, 1)} t</b></div>
      <div id="banda-prod"></div>
      <p class="nota" style="margin:12px 0 0">Las 59 parcelas suman ${f(totHa, 0)} ha y ${f(totProd, 0)} t estimadas.</p>`;
    banda(document.getElementById("banda-prod").clientWidth || 480);
  };
  const banda = (W) => {
    const p = actual, cont = document.getElementById("banda-prod");
    if (!p || !cont) return;
    const prod = p.ha * p.pred, lo = p.ha * p.lo80, hi = p.ha * p.hi80, H = 64;
    const x = d3.scaleLinear([0, Math.max(hi * 1.15, 1)], [8, W - 12]);
    const s = d3.select(cont).html("").append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
      .attr("aria-label", `Producción estimada ${f(prod, 1)} t, rango de ${f(lo, 1)} a ${f(hi, 1)} t`);
    s.append("rect").attr("x", x(lo)).attr("width", x(hi) - x(lo)).attr("y", 16).attr("height", 18).attr("fill", `url(#t-s${clase(p.pred)})`);
    s.append("line").attr("x1", x(prod)).attr("x2", x(prod)).attr("y1", 8).attr("y2", 42).attr("stroke", "#1C2733").attr("stroke-width", 3);
    s.append("g").attr("transform", `translate(0,${H - 20})`).call(d3.axisBottom(x).ticks(W < 400 ? 4 : 6).tickFormat((d) => `${d} t`).tickSize(4))
      .call((a) => a.select(".domain").attr("stroke", "#C9CFC6")).call((a) => a.selectAll("text").attr("fill", "#5A6570").attr("font-size", 12.5));
  };
  alSeleccionar((id) => pintar(id));
  pintar(estado.seleccion);
  alAncho(el, () => banda(document.getElementById("banda-prod")?.clientWidth || 480));
}
