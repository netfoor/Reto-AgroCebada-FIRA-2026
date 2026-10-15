// Descargas desde S3 con vista previa: CSV (huella comprobada aquí), Excel y hoja para PDF.
import * as d3 from "d3";
import { D, f, corto, clase, colorV } from "./comun.js";
import { verificarArchivo } from "./datos.js";

const CSV = "descargas/predicciones_59.csv", XLSX = "descargas/agrocebada_estimaciones.xlsx";

function mapaEstatico(W, H, pref) {
  const svg = d3.create("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("width", "100%");
  const defs = svg.append("defs");
  ["#CBA03A", "#B08528", "#946A1C", "#775114", "#5A3A0D", "#3F280A"].forEach((c, i) => {
    const pt = defs.append("pattern").attr("id", `${pref}-s${i}`).attr("patternUnits", "userSpaceOnUse").attr("width", 5).attr("height", 5).attr("patternTransform", "rotate(45)");
    pt.append("rect").attr("width", 5).attr("height", 5).attr("fill", "#fff");
    pt.append("rect").attr("width", 2.8).attr("height", 5).attr("fill", c);
  });
  const proy = d3.geoIdentity().reflectY(true).fitExtent([[10, 10], [W - 10, H - 10]], D.COLECCION);
  svg.append("g").selectAll("circle").data(D.P).join("circle")
    .attr("cx", (q) => proy([q.x, q.y])[0]).attr("cy", (q) => proy([q.x, q.y])[1]).attr("r", 3.6)
    .attr("fill", (q) => (q.oculta ? `url(#${pref}-s${clase(q.pred)})` : colorV(q.obs))).attr("stroke", "#1C2733").attr("stroke-width", 0.5);
  return svg.node();
}

/** Hoja A4 con mapa y las 59; `pref` separa los patrones de la copia impresa y la miniatura. */
function hojaA4(pref) {
  const hoja = document.createElement("div");
  const filas = D.EST.map((p) => `<tr><td>${p.id}</td><td>${corto(p.mun)}</td><td style="text-align:right"><b>${f(p.pred)}</b></td><td>${f(p.lo80)} a ${f(p.hi80)}</td></tr>`);
  const mitad = Math.ceil(filas.length / 2);
  const tabla = (rows) => `<table><tr><th>Parcela</th><th>Municipio</th><th style="text-align:right">t/ha</th><th>Rango 80 %</th></tr>${rows.join("")}</table>`;
  const man = D.MAN;
  hoja.innerHTML = `<div class="hoja"><h1>Estimaciones de rendimiento de cebada</h1>
    <p class="sub">59 parcelas del Reto AgroCebada FIRA 2026. Modelo E_JK (½ J + ½ K), referencia MIX. Campaña de abril a octubre de 2025.</p>
    <div class="mapa"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6mm">${tabla(filas.slice(0, mitad))}${tabla(filas.slice(mitad))}</div>
    <p class="pie">Error típico esperado por parcela: ±${f(D.EV.escalera.E_JK)} t/ha. Rango 80 %: cuantiles empíricos de errores de validación por zona (Chignahuapan y resto); aproximado.
    Commit ${man.commit || "—"}. SHA-256 de predicciones_59.csv: ${man.entrega["predicciones_59.csv"].sha256}</p></div>`;
  const m = mapaEstatico(720, 250, pref);
  m.style.height = "50mm";
  hoja.querySelector(".mapa").appendChild(m);
  return hoja.firstElementChild;
}

export function construirHoja() {
  const hoja = document.getElementById("hoja");
  hoja.replaceChildren(hojaA4("pdf"));
  return hoja;
}

export function iniciarDescargas() {
  const previa = document.getElementById("previa");
  const activo = (t) => document.querySelectorAll(".desc").forEach((d) => d.classList.toggle("activo", d.dataset.d === t));
  const sha = D.MAN.entrega["predicciones_59.csv"].sha256;
  let csvTexto = null;

  async function verCSV() {
    activo("csv");
    previa.innerHTML = `<p class="nota">Leyendo el archivo de S3…</p>`;
    const { buf, h } = await verificarArchivo(CSV, D.MAN);
    csvTexto = new TextDecoder().decode(buf);
    const lineas = csvTexto.trim().split("\n");
    const pre = document.createElement("pre");
    pre.textContent = `${lineas.slice(0, 12).join("\n")}\n… ${lineas.length - 12} líneas más`;
    previa.innerHTML = "";
    previa.append(pre);
    previa.insertAdjacentHTML("beforeend", `<div class="meta">predicciones_59.csv: ${lineas.length - 1} filas, ${buf.byteLength.toLocaleString("es-MX")} bytes.<br>
      SHA-256 de la entrega: ${sha}<br>${h === null ? "Este navegador no permite calcular la huella." : h === sha ? `<span class="ok">Huella calculada aquí: coincide con la entrega.</span>` : "Atención: la huella calculada no coincide con la entrega."}</div>`);
  }

  let hojaActiva = "Estimaciones";
  function hojas() {
    const filasCSV = (csvTexto ?? "").trim().split("\n").slice(1).map((l) => l.split(","));
    return {
      Estimaciones: [["ID_POLIGONO", "RENDIMIENTO_T_HA"], ...(filasCSV.length ? filasCSV : D.EST.map((p) => [p.id, p.pred.toFixed(4)]))],
      Rangos: [["ID_POLIGONO", "Municipio", "Zona", "Estimado", "Inf. 80 %", "Sup. 80 %", "Inf. 90 %", "Sup. 90 %"], ...D.EST.map((p) => [p.id, p.mun, p.zona, f(p.pred, 4), f(p.lo80, 3), f(p.hi80, 3), f(p.lo90, 3), f(p.hi90, 3)])],
      Componentes: [["ID_POLIGONO", "Municipio", "MUN", "MIX", "K", "J", "E_JK"], ...D.EST.map((p) => [p.id, p.mun, f(p.mun_p, 4), f(p.mix, 4), f(p.kv, 4), f(p.jv, 4), f(p.pred, 4)])],
      Metadatos: [["Campo", "Valor"], ["Modelo", "E_JK = ½·J + ½·K"], ["Referencia", "MIX = ½·media municipal + ½·IDW (20 vecinas)"], ["Campaña", "abril a octubre de 2025"], ["Commit", D.MAN.commit || "—"], ["SHA-256 de predicciones_59.csv", sha]],
    };
  }
  async function verXLSX() {
    activo("xlsx");
    const H = hojas();
    previa.innerHTML = `<div class="hojas" role="group" aria-label="Hojas del libro">${Object.keys(H).map((h) => `<button aria-pressed="${h === hojaActiva}" data-h="${h}">${h}</button>`).join("")}</div>
      <div class="tabla-x" style="overflow:auto"></div><div class="meta" id="meta-xlsx">agrocebada_estimaciones.xlsx: 4 hojas. Se muestran las primeras 8 filas de cada una.</div>`;
    const pintar = () => {
      const filas = H[hojaActiva];
      previa.querySelector(".tabla-x").innerHTML = `<table><tr>${filas[0].map((c) => `<th>${c}</th>`).join("")}</tr>${filas.slice(1, 9).map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table>`;
      previa.querySelectorAll(".hojas button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.h === hojaActiva)));
    };
    previa.querySelectorAll(".hojas button").forEach((b) => b.addEventListener("click", () => { hojaActiva = b.dataset.h; pintar(); }));
    pintar();
    const { buf, ok } = await verificarArchivo(XLSX, D.MAN);
    const meta = document.getElementById("meta-xlsx");
    if (meta) meta.insertAdjacentHTML("beforeend", `<br>${(buf.byteLength / 1024).toFixed(1)} KB. ${ok === null ? "" : ok ? `<span class="ok">Huella SHA-256 comprobada contra el manifiesto.</span>` : "Atención: la huella no coincide con el manifiesto."}`);
  }

  function verPDF() {
    activo("pdf");
    previa.innerHTML = `<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start"><div class="miniatura"><div class="esc"></div></div>
      <div class="meta" style="flex:1;min-width:220px;word-break:normal">Una hoja A4: mapa, las 59 estimaciones en dos columnas, rangos al 80 % y la huella del archivo. «Guardar como PDF» abre el diálogo de impresión del navegador; ahí elige Guardar como PDF.</div></div>`;
    const esc = previa.querySelector(".esc"), mini = previa.querySelector(".miniatura");
    const copia = hojaA4("pdfm");
    esc.appendChild(copia);
    esc.style.transform = `scale(${mini.clientWidth / (copia.getBoundingClientRect().width || 703)})`;
  }

  const ver = { csv: verCSV, xlsx: verXLSX, pdf: verPDF };
  document.querySelectorAll("[data-ver]").forEach((b) => b.addEventListener("click", () => ver[b.dataset.ver]()));
  document.querySelector("[data-pdf]").addEventListener("click", () => { construirHoja(); window.print(); });
}
