// Estimaciones: tabla de las 59, ficha de la parcela elegida y minimapa.
import * as d3 from "d3";
import {
  D, COLORES, TINTA, f, fs, corto, clase, colorV, surcos, featureDe, cajaUTM, seleccionar, alSeleccionar, estado, QUIETO,
} from "./comun.js";

/** Patrones de surcos con fondo blanco para tabla, ficha, boleta y hoja impresa. */
export function defsGlobales() {
  const svg = d3.select("body").append("svg").attr("width", 0).attr("height", 0).attr("aria-hidden", "true")
    .style("position", "absolute");
  surcos(svg.append("defs"), "t", 5);
}

export const notasDe = (p) => {
  const n = [];
  if (p.id === "AGC_120") n.push(["1 conocida", "Su municipio tiene una sola parcela conocida y no tiene vecinas a menos de 1 km"]);
  if (p.sin_k1) n.push(["sin verdor", "Sin vecinas suficientes a menos de 1 km: K usa solo la referencia MIX"]);
  if (p.celda_sin) n.push(["celda nueva", "Su celda de lluvia no tiene parcelas conocidas"]);
  return n;
};

function tabla() {
  const x = d3.scaleLinear([2, 6], [4, 136]);
  let orden = "id", asc = true, texto = "";
  const tbody = d3.select("#t59 tbody");
  const pintar = () => {
    const filas = D.EST.filter((p) => !texto || `${p.id} ${p.mun}`.toLowerCase().includes(texto));
    const clave = { id: (p) => p.id, mun: (p) => p.mun + p.id, pred: (p) => p.pred, ancho: (p) => p.hi80 - p.lo80, dif: (p) => p.pred - p.mix }[orden];
    filas.sort((a, b) => (asc ? 1 : -1) * d3.ascending(clave(a), clave(b)));
    document.getElementById("conteo").textContent = `${filas.length} de 59 parcelas`;
    tbody.selectAll("tr").data(filas, (p) => p.id).join((enter) => {
      const t = enter.append("tr").attr("tabindex", 0);
      t.append("td").text((p) => p.id);
      t.append("td").attr("class", "col-mun").text((p) => corto(p.mun));
      t.append("td").attr("class", "v").text((p) => f(p.pred));
      const s = t.append("td").attr("class", "rango").append("svg").attr("width", 140).attr("height", 18).attr("viewBox", "0 0 140 18").attr("aria-hidden", "true");
      s.append("rect").attr("x", (p) => x(p.lo80)).attr("width", (p) => x(p.hi80) - x(p.lo80)).attr("y", 5).attr("height", 8).attr("fill", (p) => `url(#t-s${clase(p.pred)})`);
      s.append("line").attr("x1", (p) => x(p.mix)).attr("x2", (p) => x(p.mix)).attr("y1", 3).attr("y2", 15).attr("stroke", "#5B636B").attr("stroke-width", 1.5);
      s.append("line").attr("x1", (p) => x(p.pred)).attr("x2", (p) => x(p.pred)).attr("y1", 1).attr("y2", 17).attr("stroke", TINTA).attr("stroke-width", 2.5);
      t.append("td").attr("class", "d col-dif").text((p) => fs(p.pred - p.mix));
      t.append("td").attr("class", "col-notas").html((p) => notasDe(p).map((n) => `<span class="marca-n" title="${n[1]}">${n[0]}</span>`).join(""));
      t.on("click", (ev, p) => seleccionar(p.id, "tabla"))
        .on("keydown", (ev, p) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); seleccionar(p.id, "tabla"); } });
      return t;
    }).order().classed("sel", (p) => p.id === estado.seleccion);
    d3.selectAll("#t59 th button").attr("data-orden", function () { return this.dataset.o === orden ? (asc ? "asc" : "desc") : null; });
  };
  d3.selectAll("#t59 th button").on("click", function () {
    const o = this.dataset.o;
    asc = orden === o ? !asc : true;
    orden = o;
    pintar();
  });
  document.getElementById("buscar").addEventListener("input", (e) => { texto = e.target.value.trim().toLowerCase(); pintar(); });
  alSeleccionar((id, origen) => {
    tbody.selectAll("tr").classed("sel", (p) => p.id === id);
    if (origen !== "tabla" && origen !== "inicio") {
      const n = tbody.selectAll("tr").filter((p) => p.id === id).node();
      const marco = document.querySelector(".tabla-marco");
      if (n && marco) marco.scrollTop = n.offsetTop - marco.clientHeight / 2;
    }
  });
  pintar();
}

/** Minimapa de 1.5 km alrededor de una parcela, con el círculo de 1 km del verdor relativo. */
export function miniMapa(cont, p, { W = 360, H = 220, radio = 1500 } = {}) {
  const ry = Math.max((radio * H) / W, 1180), rx = (ry * W) / H; // el círculo de 1 km cabe completo
  const proy = d3.geoIdentity().reflectY(true).fitSize([W, H], cajaUTM(p.x - rx, p.y - ry, p.x + rx, p.y + ry));
  const ruta = d3.geoPath(proy);
  const svg = d3.select(cont).html("").append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
    .attr("aria-label", `Parcelas alrededor de ${p.id}`);
  svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#FAFBF8");
  const cerca = D.P.filter((q) => Math.abs(q.x - p.x) < rx * 1.3 && Math.abs(q.y - p.y) < ry * 1.3);
  const [cx, cy] = proy([p.x, p.y]);
  svg.append("circle").attr("cx", cx).attr("cy", cy).attr("r", 1000 * proy.scale()).attr("fill", "none").attr("stroke", "#8A949D").attr("stroke-dasharray", "3 3");
  svg.append("text").attr("x", cx).attr("y", cy - 1000 * proy.scale() - 6).attr("text-anchor", "middle").attr("font-size", 12).attr("fill", "#5A6570").text("1 km");
  svg.selectAll("path").data(cerca).join("path").attr("d", (q) => ruta(featureDe(q)))
    .attr("fill", (q) => (q.oculta ? `url(#t-s${clase(q.pred)})` : colorV(q.obs)))
    .attr("stroke", (q) => (q.id === p.id ? "#2F6FD6" : TINTA)).attr("stroke-width", (q) => (q.id === p.id ? 2.6 : 0.6));
  return svg;
}

function ficha(irAEjecutar) {
  const el = document.getElementById("ficha");
  const pintar = (id) => {
    const p = D.porId.get(id);
    if (!p.oculta) {
      el.innerHTML = `<h3>${p.id}</h3><p class="sub">${p.mun}, ${p.edo}. Parcela con rendimiento conocido.</p>
        <div class="val"><b class="num">${f(p.obs)}</b><span>t/ha, rendimiento conocido</span></div>
        <p class="rango-txt">Cuando la ocultamos en la validación, el modelo estimó ${f(p.oof)} t/ha (promedio de 10 repeticiones).</p>
        <div class="mini"></div>
        <div class="acc"><button class="btn sec" data-ir="${p.id}">Ejecutar paso a paso</button></div>`;
    } else {
      const comp = [["MUN", "Media del municipio", p.mun_p], ["MIX", "Referencia territorial MIX", p.mix], ["K", "K, MIX corregida por verdor", p.kv], ["J", "J, región y lluvia de octubre", p.jv]];
      el.innerHTML = `<h3>${p.id}</h3><p class="sub">${p.mun}, ${p.edo}. ${f(p.ha)} ha.</p>
        <div class="val"><b class="num">${f(p.pred)}</b><span>t/ha estimadas</span></div>
        <p class="rango-txt">8 de cada 10 veces entre ${f(p.lo80)} y ${f(p.hi80)}; 9 de cada 10, entre ${f(p.lo90)} y ${f(p.hi90)}.</p>
        <div class="mini"></div>
        <table class="comp">${comp.map((c) => `<tr><td><i style="background:${COLORES[c[0]]}"></i>${c[1]}</td><td>${f(c[2])}</td></tr>`).join("")}
          <tr class="fin"><td>E_JK = ½ K + ½ J</td><td>${f(p.pred)}</td></tr></table>
        ${notasDe(p).map((n) => `<p class="nota" style="margin:0 0 6px">${n[1]}.</p>`).join("")}
        <div class="acc"><button class="btn" data-ir="${p.id}">Ejecutar paso a paso</button>
          <a class="btn sec" target="_blank" rel="noopener" href="https://www.google.com/maps/@${p.lat},${p.lon},700m/data=!3m1!1e3">Ver en satélite</a></div>`;
    }
    miniMapa(el.querySelector(".mini"), p);
    el.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => {
      irAEjecutar(b.dataset.ir);
      document.getElementById("ejecutar").scrollIntoView({ behavior: QUIETO ? "auto" : "smooth" });
    }));
  };
  alSeleccionar((id) => pintar(id));
  pintar(estado.seleccion);
}

export function iniciarEstimaciones(irAEjecutar) {
  tabla();
  ficha(irAEjecutar);
}
