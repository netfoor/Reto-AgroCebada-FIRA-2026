// Preguntas guía: escalera de error en validación cruzada.
import * as d3 from "d3";
import { D, COLORES, TINTA, GRIS, f, alAncho } from "./comun.js";

export function iniciarPreguntas() {
  const E = D.EV.escalera;
  const pasos = [["Media general", E.GLOBAL, "#C9CFC6"], ["Media del municipio", E.MUN, COLORES.MUN], ["MIX: municipio y vecinas", E.MIX, COLORES.MIX],
    ["K: más NDVI contra cercanas", E.K, COLORES.K], ["E_JK: con J, lluvia y región", E.E_JK, COLORES.E_JK]];
  const cont = document.getElementById("escalera");
  const caja = document.createElement("div");
  cont.append(caja);
  alAncho(cont, (W) => {
    const m = W < 640;
    const fila = m ? 52 : 34, mg = { l: m ? 8 : 230, r: 60, t: m ? 24 : 6, b: 46 };
    const H = mg.t + pasos.length * fila + mg.b;
    const x = d3.scaleLinear([0, 0.9], [mg.l, W - mg.r]);
    const y = d3.scaleBand(pasos.map((p) => p[0]), [mg.t, H - mg.b]).paddingInner(m ? 0.45 : 0.3);
    const s = d3.select(caja).html("").append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
      .attr("aria-label", "Error en validación cruzada al agregar cada paso del modelo");
    s.append("g").attr("transform", `translate(0,${H - mg.b})`).call(d3.axisBottom(x).ticks(m ? 4 : 9).tickFormat((d) => f(d, 1)).tickSize(-(H - mg.b - mg.t)))
      .call((a) => a.select(".domain").remove()).call((a) => a.selectAll("line").attr("stroke", "#E6E8E2"))
      .call((a) => a.selectAll("text").attr("fill", GRIS).attr("font-size", 12.5));
    const g = s.selectAll(".e").data(pasos).join("g").attr("transform", (d) => `translate(0,${y(d[0])})`);
    if (m) g.append("text").attr("x", mg.l).attr("y", -6).attr("font-size", 14).attr("fill", TINTA).text((d) => d[0]);
    else g.append("text").attr("x", mg.l - 12).attr("y", y.bandwidth() / 2).attr("dy", ".35em").attr("text-anchor", "end").attr("font-size", 14.5).attr("fill", TINTA).text((d) => d[0]);
    g.append("rect").attr("x", mg.l).attr("width", (d) => x(d[1]) - mg.l).attr("height", y.bandwidth()).attr("fill", (d) => d[2]);
    g.append("text").attr("x", (d) => x(d[1]) + 8).attr("y", y.bandwidth() / 2).attr("dy", ".35em").attr("font-size", 14).attr("font-weight", 700).attr("fill", TINTA).text((d) => f(d[1], 3));
    s.append("text").attr("x", mg.l).attr("y", H - 6).attr("font-size", 12.5).attr("fill", GRIS)
      .text(m ? "Error típico, RMSE en t/ha. Menos es mejor." : "Error típico en validación cruzada (RMSE, t/ha). Menos es mejor.");
  });
}
