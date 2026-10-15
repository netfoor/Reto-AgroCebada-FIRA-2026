// Ejecutar el modelo: paso a paso en el navegador, las 59 de una vez, o reentrenando en AWS Lambda.
import * as d3 from "d3";
import { createTimeline, stagger, svg as asvg } from "animejs";
import {
  D, QUIETO, NUBE, f, fs, r4, grupoTxt, modeloFinal, cajaUTM, mostrarTip, ocultarTip, seleccionar, alSeleccionar, estado, sha256hex,
} from "./comun.js";

const W = 420, H = 420;
let anim = null;
const parar = () => { if (anim) { anim.revert(); anim = null; } };

export function iniciarEjecutar() {
  const sel = document.getElementById("ej-parcela");
  const consola = document.getElementById("consola");
  const nota = document.getElementById("ej-nota");
  const svg = d3.select("#ej-svg");
  const sha = D.MAN.entrega["predicciones_59.csv"].sha256;
  let csvEntrega = null;
  const huellaEntrega = async () => {
    if (csvEntrega === null) {
      const r = await fetch("/descargas/predicciones_59.csv", { cache: "no-cache" });
      csvEntrega = r.ok ? await r.arrayBuffer() : new ArrayBuffer(0);
    }
    return sha256hex(csvEntrega);
  };

  sel.innerHTML = `<optgroup label="Estimadas (59)">${D.EST.map((p) => `<option value="${p.id}">${p.id}, ${p.mun}</option>`).join("")}</optgroup>
    <optgroup label="Con rendimiento conocido (138), como si estuvieran ocultas">${D.REP.map((p) => `<option value="${p.id}">${p.id}, ${p.mun}</option>`).join("")}</optgroup>`;
  sel.value = estado.seleccion;

  function dibujarVecinas(p, r) {
    const R = Math.max(d3.max(r.vecinas, (v) => v.d) * 1.12, 900);
    const proy = d3.geoIdentity().reflectY(true).fitExtent([[14, 14], [W - 14, H - 14]], cajaUTM(p.x - R, p.y - R, p.x + R, p.y + R));
    svg.html("");
    const cerca = D.P.filter((q) => Math.abs(q.x - p.x) < R && Math.abs(q.y - p.y) < R);
    const [cx, cy] = proy([p.x, p.y]);
    const wmax = d3.max(r.vecinas, (v) => v.w);
    const lineas = svg.append("g").selectAll("line").data(r.vecinas).join("line")
      .attr("x1", cx).attr("y1", cy).attr("x2", (v) => proy([v.q.x, v.q.y])[0]).attr("y2", (v) => proy([v.q.x, v.q.y])[1])
      .attr("stroke", "#E3C772").attr("stroke-opacity", 0.9).attr("stroke-width", (v) => 0.8 + (7 * v.w) / wmax);
    svg.append("g").selectAll("circle").data(cerca).join("circle")
      .attr("cx", (q) => proy([q.x, q.y])[0]).attr("cy", (q) => proy([q.x, q.y])[1])
      .attr("r", (q) => (q.id === p.id ? 7 : 3.8)).attr("fill", (q) => (q.id === p.id ? "#fff" : q.oculta ? "none" : "#9FB3CB"))
      .attr("stroke", (q) => (q.id === p.id ? "#E3C772" : q.oculta ? "#6f8db0" : "none")).attr("stroke-width", (q) => (q.id === p.id ? 3 : 1.2));
    const L = R >= 4000 ? 2000 : 1000;
    const g = svg.append("g").attr("transform", `translate(16,${H - 18})`);
    g.append("rect").attr("width", L * proy.scale()).attr("height", 4).attr("fill", "#C9D6E6");
    g.append("text").attr("y", -7).attr("fill", "#C9D6E6").attr("font-size", 13).text(L >= 1000 ? `${L / 1000} km` : `${L} m`);
    const ley = svg.append("g").attr("transform", `translate(${W - 16},${H - 14})`).attr("text-anchor", "end").attr("font-size", 12.5).attr("fill", "#9FB3CB");
    ley.append("text").text("Relleno: conocida. Hueco: estimada.");
    nota.textContent = `Las líneas unen ${p.id} con las 20 vecinas conocidas que usa la referencia territorial; su grosor es el peso de cada una.`;
    return lineas;
  }

  function dispersion(lista, etiquetaY, nombreY) {
    const m = 48;
    const x = d3.scaleLinear([2.7, 4.8], [m, W - 16]), y = d3.scaleLinear([2.7, 4.8], [H - m, 16]);
    svg.html("");
    const ejes = (sel) => sel.call((a) => a.select(".domain").remove()).call((a) => a.selectAll("line").attr("stroke", "#1b4673"))
      .call((a) => a.selectAll("text").attr("fill", "#9FB3CB").attr("font-size", 12.5));
    svg.append("g").attr("transform", `translate(0,${H - m})`).call(d3.axisBottom(x).ticks(5).tickSize(-(H - m - 16))).call(ejes);
    svg.append("g").attr("transform", `translate(${m},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(W - m - 16))).call(ejes);
    svg.append("line").attr("x1", x(2.7)).attr("y1", y(2.7)).attr("x2", x(4.8)).attr("y2", y(4.8)).attr("stroke", "#6f8db0").attr("stroke-dasharray", "4 4");
    const pts = svg.append("g").selectAll("circle").data(lista).join("circle").attr("cx", (o) => x(o.x)).attr("cy", (o) => y(o.y)).attr("r", 5.2)
      .attr("fill", "#E3C772").attr("fill-opacity", 0.9).attr("stroke", "#011a35").attr("stroke-width", 1)
      .on("pointerenter pointermove", (ev, o) => { if (ev.pointerType !== "touch") mostrarTip(`<b>${o.id}</b><br>Archivo ${f(o.x, 4)}<br>${nombreY} ${f(o.y, 6)}`, ev); })
      .on("pointerleave", ocultarTip);
    svg.append("text").attr("x", W - 16).attr("y", H - 8).attr("text-anchor", "end").attr("fill", "#9FB3CB").attr("font-size", 12.5).text("predicciones_59.csv (t/ha)");
    svg.append("text").attr("x", 12).attr("y", 11).attr("fill", "#9FB3CB").attr("font-size", 12.5).text(etiquetaY);
    return pts;
  }

  const lista = (filas) => `<ol>${filas.map((x) => `<li class="${x.c || ""}"><span>${x.t}${x.x ? `<span class="x">${x.x}</span>` : ""}</span>${x.r != null ? `<span class="r">${x.r}</span>` : ""}</li>`).join("")}</ol>`;
  const animarConsola = (extra) => {
    parar();
    if (QUIETO) return;
    const tl = createTimeline({ defaults: { ease: "outQuad" } })
      .add(consola.querySelectorAll("li"), { opacity: [0, 1], x: [-8, 0], duration: 320, delay: stagger(220) });
    if (extra) extra(tl);
    anim = tl;
  };

  async function ejecutar() {
    const p = D.porId.get(sel.value);
    if (estado.seleccion !== p.id) seleccionar(p.id, "ejecutar");
    const r = modeloFinal(p);
    const top = [...r.vecinas].sort((a, b) => b.w - a.w).slice(0, 3);
    const M = D.M;
    const filas = [
      { t: `Parcela ${p.id} en ${p.mun}, ${p.edo}. Grupo regional: ${grupoTxt(p.grupo)}.`, x: p.oculta ? "Su rendimiento no se conoce." : "Para probar el modelo, su rendimiento se excluye de los cálculos de abajo.", r: p.oculta ? "" : `conocido: ${f(p.obs)}` },
      { t: `Media de su municipio (${r.nMun} parcelas conocidas)`, x: "Si el municipio no tuviera parcelas conocidas, se usaría la media general.", r: f(r.MUN, 3) },
      { t: `Promedio de sus ${r.vecinas.length} vecinas conocidas, ponderado por 1/distancia²`, x: `Pesan más: ${top.map((v) => `${v.id} a ${f(v.d, 0)} m (${f(v.w * 100, 0)} %)`).join(", ")}.`, r: f(r.IDW, 3) },
      { t: `Referencia territorial MIX = ½ · ${f(r.MUN, 3)} + ½ · ${f(r.IDW, 3)}`, r: f(r.MIX, 3) },
      p.k1 == null
        ? { t: "Verdor contra vecinas: no tiene al menos 2 vecinas a menos de 1 km", x: "K queda igual a MIX.", r: f(r.K, 3) }
        : { t: `Verdor contra sus vecinas a menos de 1 km: ${fs(p.k1)} NDVI·día, z = ${f(r.z, 3)}`, x: `K = MIX ${M.K.beta < 0 ? "−" : "+"} ${f(Math.abs(M.K.beta), 4)} × ${f(r.z, 3)} = ${f(r.MIX, 3)} ${M.K.beta * r.z < 0 ? "−" : "+"} ${f(Math.abs(M.K.beta * r.z), 3)}`, r: f(r.K, 3) },
      { t: `Lluvia de octubre de 2025 frente a 2022–2024: ${fs(p.anom, 1)} %`, x: `J = ${f(M.J[p.grupo], 3)} (grupo ${grupoTxt(p.grupo)}) + ${f(M.J.pendiente, 5)} × ${f(p.anom, 1)}`, r: f(r.J, 3) },
      { t: `Estimación final E_JK = ½ · ${f(r.K, 3)} + ½ · ${f(r.J, 3)}`, r: `${f(r.E)} t/ha`, c: "fin" },
    ];
    if (p.oculta) {
      const igual = Math.abs(r4(r.E) - p.pred) < 1e-9;
      filas.push({ t: `Rango 80 % para la zona ${p.zona === "Chignahuapan" ? "Chignahuapan" : "resto"}: ${f(p.lo80)} a ${f(p.hi80)} t/ha.`, c: "ok" });
      filas.push({ t: igual ? `Coincide con predicciones_59.csv: ${f(p.pred, 4)} t/ha, a 4 decimales.` : `No coincide con el archivo: diferencia de ${f(Math.abs(r.E - p.pred), 5)} t/ha.`, x: "Comprobando la huella del archivo…", c: "ok" });
    } else {
      filas.push({ t: `Rendimiento conocido: ${f(p.obs)} t/ha. Error de esta estimación: ${fs(r.E - p.obs)} t/ha.`, x: `En la validación cruzada, sin verla, el promedio de 10 repeticiones fue ${f(p.oof)} t/ha. Aquí los coeficientes son los del ajuste final, que sí la incluyen: es una aproximación.`, c: "ok" });
    }
    consola.innerHTML = lista(filas);
    const lineas = dibujarVecinas(p, r);
    animarConsola((tl) => tl.add(asvg.createDrawable(lineas.nodes()), { draw: ["0 0", "0 1"], duration: 700, delay: stagger(30) }, 520));
    if (p.oculta) {
      const h = await huellaEntrega();
      const x = consola.querySelector("li:last-child .x");
      if (x) x.textContent = h === null ? "La huella no se puede calcular en este navegador." : h === sha ? `Huella SHA-256 ${sha.slice(0, 16)}… verificada.` : "La huella no coincide con la entrega.";
    }
  }

  async function recalcularTodas() {
    const t0 = performance.now();
    const res = D.EST.map((p) => ({ p, r: modeloFinal(p) }));
    const ms = performance.now() - t0;
    const iguales = res.filter((o) => Math.abs(r4(o.r.E) - o.p.pred) < 1e-9).length;
    const dmax = d3.max(res, (o) => Math.abs(o.r.E - o.p.e_jk));
    consola.innerHTML = lista([
      { t: "Recalculadas las 59 estimaciones con la fórmula de E_JK, desde las 138 parcelas conocidas.", x: "Para cada una: media municipal, 20 vecinas, verdor relativo y lluvia de octubre.", r: `${f(Math.max(ms, 1), 0)} ms` },
      { t: "Iguales a predicciones_59.csv al redondear a 4 decimales, como el archivo", r: `${iguales} de 59` },
      { t: "Diferencia máxima con detalle_59.csv, sin redondear", x: "detalle_59.csv guarda E_JK con todos sus decimales.", r: dmax < 1e-9 ? "menos de 10⁻⁹ t/ha" : `${f(dmax, 9)} t/ha` },
      { t: "Comprobando la huella del archivo…", c: "ok" },
    ]);
    const pts = dispersion(res.map((o) => ({ id: o.p.id, x: o.p.pred, y: o.r.E })), "calculado aquí (t/ha)", "Navegador");
    nota.textContent = "Cada punto es una de las 59: el archivo de entrega frente al cálculo de este navegador. Todas caen sobre la diagonal.";
    animarConsola((tl) => tl.add(pts.nodes(), { opacity: [0, 1], duration: 300, delay: stagger(12) }, 200));
    const h = await huellaEntrega();
    consola.querySelector("li:last-child > span").textContent = h === null ? "Este navegador no permite calcular la huella." : h === sha ? `Huella SHA-256 del archivo verificada: ${sha.slice(0, 16)}…` : "La huella del archivo no coincide con la entrega.";
  }

  const bNube = document.getElementById("ej-nube");
  const csvNube = document.getElementById("ej-nube-csv");
  async function reentrenarNube() {
    bNube.disabled = true;
    consola.innerHTML = `<p class="vacia">Reentrenando en AWS Lambda con las 138 parcelas conocidas…</p>`;
    const t0 = performance.now();
    let r;
    try {
      const res = await fetch("/api/reentrenar", { cache: "no-store" });
      if (!res.ok) throw new Error(`respuesta ${res.status}`);
      r = await res.json();
    } catch (e) {
      consola.innerHTML = `<p class="vacia">No se pudo reentrenar en AWS (${e.message}). Intenta de nuevo o usa el cálculo en el navegador.</p>`;
      bNube.disabled = false;
      return;
    }
    bNube.disabled = false;
    const ida = (performance.now() - t0) / 1000;
    const iguales = r.predicciones.filter((q) => { const p = D.porId.get(q.id); return p && Math.abs(r4(q.E_JK) - p.pred) < 1e-9; }).length;
    consola.innerHTML = lista([
      { t: `Reentrenado en AWS Lambda con ${r.parcelas_entrenamiento} parcelas conocidas.`, x: `${r.arranque_en_frio ? "Primera llamada: la función arrancó en frío." : "La función ya estaba activa."} Ida y vuelta: ${f(ida, 2)} s.`, r: `${f(r.segundos_ajuste, 3)} s` },
      { t: `K: β ajustada con 4 pliegues internos (semilla ${r.semilla_interna_K})`, r: fs(r.K.beta, 4) },
      { t: "J eligió su variable entre 148", x: r.J_variable, r: r.J_variable === "anom_precip_pct_d" ? "lluvia de octubre" : r.J_variable },
      { t: "Estimaciones iguales a predicciones_59.csv a 4 decimales", r: `${iguales} de ${r.parcelas_estimadas}` },
      { t: r.coincide ? `El CSV reentrenado tiene la misma huella SHA-256 que la entrega: ${r.csv_sha256.slice(0, 16)}…` : "La huella del CSV reentrenado no coincide con la entrega.", c: "ok" },
    ]);
    csvNube.hidden = false;
    const pts = dispersion(r.predicciones.map((q) => ({ id: q.id, x: D.porId.get(q.id).pred, y: q.E_JK })), "reentrenado en AWS (t/ha)", "AWS");
    nota.textContent = "Cada punto es una de las 59: el archivo de entrega frente al modelo reentrenado en AWS Lambda.";
    animarConsola((tl) => tl.add(pts.nodes(), { opacity: [0, 1], duration: 300, delay: stagger(12) }, 200));
  }

  const estadoNube = document.getElementById("estado-nube");
  NUBE.then((s) => {
    if (!s) {
      estadoNube.querySelector("span").textContent = "La función de AWS no responde desde aquí. El cálculo en el navegador sigue disponible.";
      return;
    }
    estadoNube.classList.add("activa");
    estadoNube.querySelector("span").textContent = `Función activa en AWS Lambda (${s.region}): Python ${s.python}, numpy ${s.numpy}, pandas ${s.pandas}; ${s.insumos_verificados} insumos verificados.`;
    bNube.disabled = false;
    bNube.addEventListener("click", reentrenarNube);
  });
  document.getElementById("ej-correr").addEventListener("click", ejecutar);
  document.getElementById("ej-todas").addEventListener("click", recalcularTodas);
  sel.addEventListener("change", ejecutar);
  alSeleccionar((id, origen) => { if (origen !== "ejecutar") sel.value = id; });
  dibujarVecinas(D.porId.get(estado.seleccion), modeloFinal(D.porId.get(estado.seleccion)));
  return { cargar: (id) => { sel.value = id; ejecutar(); } };
}
