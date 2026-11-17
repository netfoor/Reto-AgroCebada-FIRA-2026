// Ejecutar el modelo: paso a paso en el navegador, las 59 de una vez, o reentrenando en AWS Lambda.
import * as d3 from "d3";
import { createTimeline, stagger, svg as asvg } from "animejs";
import {
  D, QUIETO, NUBE, f, fs, r4, grupoTxt, modeloFinal, cajaUTM, mostrarTip, ocultarTip, seleccionar, alSeleccionar, estado, sha256hex,
  clase, colorV, featureDe, TINTA,
} from "./comun.js";
import { fondoSatelital, cajaDeLienzo } from "./satelite.js";

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

  const titFig = document.getElementById("ej-tit-fig"), titCalc = document.getElementById("ej-tit-calc");
  /** Recuadro blanco, igual que en las demás figuras con satélite. */
  const panel = (g, x, y, w, h) => g.append("rect").attr("x", x).attr("y", y).attr("width", w).attr("height", h).attr("fill", "#fff").attr("fill-opacity", 0.94);

  function dibujarVecinas(p, r) {
    const R = Math.max(d3.max(r.vecinas, (v) => v.d) * 1.12, 900);
    const proy = d3.geoIdentity().reflectY(true).fitExtent([[0, 0], [W, H]], cajaUTM(p.x - R, p.y - R, p.x + R, p.y + R));
    const ruta = d3.geoPath(proy);
    svg.html("");
    svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#0b1c30");
    fondoSatelital(svg.append("g"), (x, y) => proy([x, y]), cajaDeLienzo(proy, W, H), { pixeles: W });
    const cerca = D.P.filter((q) => q.id !== p.id && Math.abs(q.x - p.x) < R * 1.1 && Math.abs(q.y - p.y) < R * 1.1);
    svg.append("g").selectAll("path").data(cerca).join("path").attr("d", (q) => ruta(featureDe(q)))
      .attr("fill", (q) => (q.oculta ? `url(#t-s${clase(q.pred)})` : colorV(q.obs))).attr("stroke", "#fff").attr("stroke-width", 0.6);
    const [cx, cy] = proy([p.x, p.y]);
    const wmax = d3.max(r.vecinas, (v) => v.w);
    const lineas = svg.append("g").selectAll("line").data(r.vecinas).join("line")
      .attr("x1", cx).attr("y1", cy).attr("x2", (v) => proy([v.q.x, v.q.y])[0]).attr("y2", (v) => proy([v.q.x, v.q.y])[1])
      .attr("stroke", "#E3C772").attr("stroke-opacity", 0.95).attr("stroke-linecap", "round").attr("stroke-width", (v) => 0.8 + (7 * v.w) / wmax);
    svg.append("path").attr("d", ruta(featureDe(p))).attr("fill", "#E3C772").attr("fill-opacity", 0.35).attr("stroke", "#E3C772").attr("stroke-width", 2.5);
    svg.append("circle").attr("cx", cx).attr("cy", cy).attr("r", 7).attr("fill", "#022448").attr("stroke", "#E3C772").attr("stroke-width", 3);
    const et = svg.append("g").attr("transform", `translate(${Math.min(cx + 12, W - 86)},${Math.min(cy + 12, H - 80)})`);
    panel(et, 0, 0, 76, 22);
    et.append("text").attr("x", 7).attr("y", 15.5).attr("font-size", 12.5).attr("font-weight", 700).attr("fill", "#7A4708").text(p.id);
    const L = R >= 4000 ? 2000 : 1000, lp = L * proy.scale();
    const g = svg.append("g").attr("transform", `translate(${W - 20 - lp},${H - 14})`);
    panel(g, -8, -26, lp + 16, 34);
    g.append("rect").attr("width", lp).attr("height", 4).attr("fill", TINTA);
    g.append("text").attr("y", -8).attr("fill", "#5A6570").attr("font-size", 12).text(L >= 1000 ? `${L / 1000} km` : `${L} m`);
    const ley = svg.append("g").attr("transform", `translate(12,${H - 40})`);
    panel(ley, 0, 0, 190, 28);
    ley.append("rect").attr("x", 10).attr("y", 9).attr("width", 11).attr("height", 11).attr("fill", "#946A1C");
    ley.append("text").attr("x", 26).attr("y", 18.5).attr("font-size", 12).attr("fill", TINTA).text("conocida");
    ley.append("rect").attr("x", 92).attr("y", 9).attr("width", 11).attr("height", 11).attr("fill", "url(#t-s2)").attr("stroke", "#946A1C");
    ley.append("text").attr("x", 108).attr("y", 18.5).attr("font-size", 12).attr("fill", TINTA).text("estimada");
    titFig.textContent = `Las ${r.vecinas.length} vecinas que usa ${p.id}`;
    nota.textContent = `Cada línea une ${p.id} con una de sus 20 vecinas conocidas; entre más gruesa, más pesa en la referencia.`;
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
      { t: `Media de su municipio (${r.nMun} ${r.nMun === 1 ? "parcela conocida" : "parcelas conocidas"})`, x: "Si el municipio no tuviera parcelas conocidas, se usaría la media general.", r: f(r.MUN, 3) },
      { t: `Promedio de sus ${r.vecinas.length} vecinas conocidas, pesando más las más cercanas`, x: `Pesan más: ${top.map((v) => `${v.id} a ${f(v.d, 0)} m (${f(v.w * 100, 0)} %)`).join(", ")}.`, r: f(r.IDW, 3) },
      { t: `Referencia (municipio + vecinas), MIX = ½ · ${f(r.MUN, 3)} + ½ · ${f(r.IDW, 3)}`, r: f(r.MIX, 3) },
      p.k1 == null
        ? { t: "NDVI contra las cercanas: no tiene al menos 2 parcelas a menos de 1 km", x: "K queda igual a MIX.", r: f(r.K, 3) }
        : { t: `NDVI contra las parcelas cercanas (a menos de 1 km): ${fs(p.k1)} (${p.k1 > 0 ? "más" : "menos"} vegetación que ellas)`, x: `Ajustada a la escala del modelo, la diferencia vale ${r.z < 0 ? "−" : ""}${f(Math.abs(r.z), 3)}. K = MIX ${M.K.beta < 0 ? "−" : "+"} ${f(Math.abs(M.K.beta), 4)} × ${r.z < 0 ? `(−${f(-r.z, 3)})` : f(r.z, 3)} = ${f(r.MIX, 3)} ${M.K.beta * r.z < 0 ? "−" : "+"} ${f(Math.abs(M.K.beta * r.z), 3)}`, r: f(r.K, 3) },
      { t: `Lluvia de octubre de 2025 frente a 2022–2024: ${fs(p.anom, 1)} %`, x: `J = ${f(M.J[p.grupo], 3)} (nivel del grupo ${grupoTxt(p.grupo)}, con lluvia normal) + ${f(M.J.pendiente, 5)} × ${f(p.anom, 2)}`, r: f(r.J, 3) },
      { t: `Estimación final: promedio de K y J = ½ · ${f(r.K, 3)} + ½ · ${f(r.J, 3)}`, r: `${f(r.E)} t/ha`, c: "fin" },
    ];
    if (p.oculta) {
      const igual = Math.abs(r4(r.E) - p.pred) < 1e-9;
      filas.push({ t: `Rango 80 %: ${f(p.lo80)} a ${f(p.hi80)} t/ha. Su ancho depende de si la parcela está en Chignahuapan o en el resto de la zona.`, c: "ok" });
      filas.push({ t: igual ? `Coincide con predicciones_59.csv: ${f(p.pred, 4)} t/ha, a 4 decimales.` : `No coincide con el archivo: diferencia de ${f(Math.abs(r.E - p.pred), 5)} t/ha.`, x: "Comprobando la huella del archivo…", c: "ok" });
    } else {
      filas.push({ t: `Rendimiento conocido: ${f(p.obs)} t/ha. Error de esta estimación: ${fs(r.E - p.obs)} t/ha.`, x: `En la validación cruzada, sin verla, el promedio de 10 repeticiones fue ${f(p.oof)} t/ha. Aquí los coeficientes son los del ajuste final, que sí la incluyen: es una aproximación.`, c: "ok" });
    }
    titCalc.textContent = `Cálculo de ${p.id}`;
    consola.innerHTML = lista(filas);
    const lineas = dibujarVecinas(p, r);
    animarConsola((tl) => tl.add(asvg.createDrawable(lineas.nodes()), { draw: ["0 0", "0 1"], duration: 700, delay: stagger(30) }, 520));
    if (p.oculta) {
      const h = await huellaEntrega();
      const x = consola.querySelector("li:last-child .x");
      if (x) x.textContent = h === null ? "La huella no se puede calcular en este navegador." : h === sha ? `Archivo verificado: es el mismo de la entrega (huella SHA-256 ${sha.slice(0, 16)}…).` : "La huella no coincide con la entrega.";
    }
  }

  async function recalcularTodas() {
    const t0 = performance.now();
    const res = D.EST.map((p) => ({ p, r: modeloFinal(p) }));
    const ms = performance.now() - t0;
    const iguales = res.filter((o) => Math.abs(r4(o.r.E) - o.p.pred) < 1e-9).length;
    const dmax = d3.max(res, (o) => Math.abs(o.r.E - o.p.e_jk));
    consola.innerHTML = lista([
      { t: "Recalculadas las 59 estimaciones con la fórmula de E_JK, desde las 138 parcelas conocidas.", x: "Para cada una: media municipal, 20 vecinas, NDVI contra las cercanas y lluvia de octubre.", r: `${f(Math.max(ms, 1), 0)} ms` },
      { t: "Iguales a predicciones_59.csv al redondear a 4 decimales, como el archivo", r: `${iguales} de 59` },
      { t: "Diferencia máxima con detalle_59.csv, sin redondear", x: "detalle_59.csv guarda E_JK con todos sus decimales.", r: dmax < 1e-9 ? "menos de 10⁻⁹ t/ha" : `${f(dmax, 9)} t/ha` },
      { t: "Comprobando la huella del archivo…", c: "ok" },
    ]);
    titCalc.textContent = "Las 59 recalculadas";
    titFig.textContent = "Archivo de entrega frente a este navegador";
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
      { t: "K: peso del NDVI recalculado con las 138 parcelas", x: `Se validó dividiendo los datos en 4 partes (semilla ${r.semilla_interna_K}).`, r: fs(r.K.beta, 4) },
      { t: "J eligió su variable de clima entre 148 candidatas", x: `Nombre en los datos: ${r.J_variable}`, r: r.J_variable === "anom_precip_pct_d" ? "lluvia de octubre" : r.J_variable },
      { t: "Estimaciones iguales a predicciones_59.csv a 4 decimales", r: `${iguales} de ${r.parcelas_estimadas}` },
      { t: r.coincide ? `El CSV reentrenado tiene la misma huella SHA-256 que la entrega: ${r.csv_sha256.slice(0, 16)}…` : "La huella del CSV reentrenado no coincide con la entrega.", c: "ok" },
    ]);
    csvNube.hidden = false;
    titCalc.textContent = "Reentrenado en AWS";
    titFig.textContent = "Archivo de entrega frente a AWS";
    const pts = dispersion(r.predicciones.map((q) => ({ id: q.id, x: D.porId.get(q.id).pred, y: q.E_JK })), "reentrenado en AWS (t/ha)", "AWS");
    nota.textContent = "Cada punto es una de las 59: el archivo de entrega frente al modelo reentrenado en AWS Lambda.";
    animarConsola((tl) => tl.add(pts.nodes(), { opacity: [0, 1], duration: 300, delay: stagger(12) }, 200));
  }

  const estadoNube = document.getElementById("estado-nube");
  NUBE.then((s) => {
    if (!s) {
      estadoNube.querySelector("span").textContent = "Esta opción funciona en la versión publicada del sitio. Aquí puedes usar el cálculo paso a paso.";
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
  alSeleccionar((id, origen) => { if (origen !== "ejecutar" && origen !== "inicio") { sel.value = id; ejecutar(); } });
  sel.value = estado.seleccion;
  ejecutar();
  return { cargar: (id) => { sel.value = id; ejecutar(); } };
}
