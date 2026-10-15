// Figuras de «Cómo se hizo». Cada escena se dibuja en unidades del lienzo: 800×600 en escritorio y
// 400 de ancho en teléfono (≈1 unidad por píxel), así el texto conserva su tamaño en ambos.
import * as d3 from "d3";
import {
  D, f, fs, pct, corto, colorV, RAMPA, COLORES, NOMBRES, TINTA, GRIS, featureDe, cajaUTM, modeloFinal, mostrarTip, ocultarTip,
} from "./comun.js";

export const CAPAS_FIN = 0.15;
const RAYA = "#E6E8E2";

const limpiarEje = (size = 13) => (a) => a.call((s) => s.select(".domain").remove())
  .call((s) => s.selectAll("line").attr("stroke", RAYA)).call((s) => s.selectAll("text").attr("fill", GRIS).attr("font-size", size));

/** Texto en varias líneas. */
function lineas(g, x, y, txt, { size = 13.5, color = GRIS, peso = 400, alto = 1.35, ancla = "start" } = {}) {
  const t = g.append("text").attr("x", x).attr("y", y).attr("font-size", size).attr("fill", color).attr("font-weight", peso).attr("text-anchor", ancla);
  [].concat(txt).forEach((l, i) => t.append("tspan").attr("x", x).attr("dy", i ? size * alto : 0).text(l));
  return t;
}
function punta(g, id) {
  g.append("defs").append("marker").attr("id", id).attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5)
    .attr("markerWidth", 7).attr("markerHeight", 7).attr("orient", "auto")
    .append("path").attr("d", "M0,0 L10,5 L0,10 z").attr("fill", "#7A848D");
}
const vit = () => D.porId.get(D.VIT.id);
/** Recorre los textos centrados que se salen del lienzo para que queden completos. */
function dentro(g, W, mg = 8) {
  requestAnimationFrame(() => g.selectAll("text[text-anchor='middle']").each(function () {
    let w = 0;
    try { w = this.getComputedTextLength(); } catch { return; }
    if (!w) return;
    const x = +this.getAttribute("x");
    const nx = Math.min(W - mg - w / 2, Math.max(mg + w / 2, x));
    if (nx !== x) this.setAttribute("x", nx);
  }));
}

/* 1. Las 59 ocultas entre las conocidas */
function oculto(g, W, H, m) {
  const proy = d3.geoIdentity().reflectY(true).fitExtent([[20, m ? 64 : 48], [W - 20, H - 14]], D.COLECCION);
  g.selectAll("circle").data(D.P).join("circle")
    .attr("cx", (p) => proy([p.x, p.y])[0]).attr("cy", (p) => proy([p.x, p.y])[1])
    .attr("r", (p) => (p.oculta ? (m ? 4.4 : 5.5) : m ? 2.8 : 3.6))
    .attr("fill", (p) => (p.oculta ? "#fff" : "#9AA1A8")).attr("stroke", (p) => (p.oculta ? "#C27A12" : "none")).attr("stroke-width", 2);
  lineas(g, 20, 24, m ? ["Gris: rendimiento conocido.", "Anillo: ocultas para calificar."] : "Gris: rendimiento conocido. Anillo: ocultas para calificar.", { size: 14 });
}

/* 2. Cuatro capas que se juntan en la fila de una parcela (avance ligado al scroll) */
function capas(g, W, H, m) {
  const V = D.VIT, p = vit(), E = V.elev;
  const lado = E.paso * E.n, L = m ? 150 : 250, S = L / lado;
  const x0 = p.x - lado / 2, y0 = p.y - lado / 2;
  const loc = (x, y) => [(x - x0) * S, (y0 + lado - y) * S];
  const trazo = (r) => "M" + r.map(([x, y]) => loc(x, y).map((v) => v.toFixed(1)).join(",")).join("L") + "Z";
  const iso = "matrix(0.866,0.5,-0.866,0.5,0,0)";
  const clip = `corte-capa-${m ? "m" : "e"}`;
  g.append("defs").append("clipPath").attr("id", clip).append("rect").attr("width", L).attr("height", L);
  const cx = m ? 142 : 300;
  const base = m ? 184 : 235, paso = m ? 58 : 75, junto = m ? 97 : 122;
  const etqX = m ? 140 : 226, notaSize = m ? 12 : 12.5;
  const lista = [];
  const nueva = (nombre, nota, color) => {
    const c = g.append("g");
    const dentro = c.append("g").attr("transform", iso).append("g").attr("clip-path", `url(#${clip})`);
    const etq = c.append("g");
    etq.append("rect").attr("x", etqX).attr("y", L / 2 - 20).attr("width", 4).attr("height", 36).attr("fill", color);
    etq.append("text").attr("x", etqX + 12).attr("y", L / 2 - 5).attr("font-size", m ? 13.5 : 14.5).attr("font-weight", 700).attr("fill", TINTA).text(nombre);
    etq.append("text").attr("x", etqX + 12).attr("y", L / 2 + 13).attr("font-size", notaSize).attr("fill", GRIS).text(nota);
    lista.push({ c, etq });
    return dentro;
  };
  // 1. elevación (abajo)
  const e = nueva(m ? "Elevación" : "Elevación INEGI, cada 120 m", m ? "cada 120 m" : "probada; no entró al modelo final", "#59645D");
  const ev = E.valores.flat().filter((v) => v != null);
  const gris = d3.scaleLinear(d3.extent(ev), ["#EEF0EA", "#59645D"]);
  const pe = E.paso * S;
  E.valores.forEach((fila, i) => fila.forEach((v, j) => {
    if (v == null) return;
    const [px, py] = loc(E.x0 + j * E.paso - E.paso / 2, E.y0 - i * E.paso + E.paso / 2);
    e.append("rect").attr("x", px).attr("y", py).attr("width", pe + 0.4).attr("height", pe + 0.4).attr("fill", gris(v));
  }));
  e.append("rect").attr("width", L).attr("height", L).attr("fill", "none").attr("stroke", "#59645D");
  // 2. lluvia
  const l = nueva(m ? "Lluvia" : "Lluvia CHIRPS, octubre de 2025", m ? "octubre de 2025" : "celdas de unos 5 km por lado", "#2F6FD6");
  const azul = d3.scaleLinear([110, 175], ["#cde2fb", "#256abf"]);
  V.celdas["2025"].forEach((c) => l.append("path").attr("d", trazo(c.poly)).attr("fill", azul(c.valor)).attr("fill-opacity", 0.82).attr("stroke", "#fff").attr("stroke-width", 1.2));
  l.append("rect").attr("width", L).attr("height", L).attr("fill", "none").attr("stroke", "#256abf");
  // 3. polígono
  const pc = nueva(m ? "Polígono" : `Polígono de ${V.id}`, m ? `${f(p.ha)} ha` : `${f(p.ha)} ha, entregado por el reto`, "#C27A12");
  pc.append("rect").attr("width", L).attr("height", L).attr("fill", "#fff").attr("fill-opacity", 0.2).attr("stroke", "#C27A12");
  const [vx, vy] = loc(p.x, p.y);
  pc.append("path").attr("d", p.poly.map(trazo).join("")).attr("fill", "#C27A12");
  pc.append("circle").attr("cx", vx).attr("cy", vy).attr("r", m ? 8 : 11).attr("fill", "none").attr("stroke", "#C27A12").attr("stroke-width", 1.6);
  // 4. verdor de la parcela y de sus vecinas a menos de 1 km (arriba)
  const vd = nueva(m ? "Verdor" : "Verdor Planet, temporada 2025", m ? "por parcela" : "área bajo la curva, por parcela", "#3A9E6E");
  vd.append("rect").attr("width", L).attr("height", L).attr("fill", "none").attr("stroke", "#3A9E6E");
  const integ = new Map(V.curvas.map((c) => [c.id, c.integral]));
  const verde = d3.scaleLinear(d3.extent([...integ.values()]), ["#bfe3cd", "#1f6e47"]);
  vd.append("circle").attr("cx", vx).attr("cy", vy).attr("r", 1000 * S).attr("fill", "none").attr("stroke", "#3A9E6E").attr("stroke-dasharray", "3 3");
  [...integ.keys()].forEach((id) => vd.append("path").attr("d", D.porId.get(id).poly.map(trazo).join(""))
    .attr("fill", verde(integ.get(id))).attr("stroke", id === p.id ? TINTA : "none").attr("stroke-width", 1.2));
  // la fila que resulta
  const centro = E.valores[(E.n - 1) / 2][(E.n - 1) / 2];
  const celdas = [
    ["Parcela", V.id, TINTA], ["Elevación", `${f(centro, 0)} m`, "#59645D"],
    ["Lluvia oct. 2025", `${f(V.lluvia_pond["2025"], 0)} mm (${fs(V.anom, 0)} %)`, "#2F6FD6"],
    ["Superficie", `${f(p.ha)} ha`, "#C27A12"], ["Verdor", `${f(V.integral, 1)} (${fs(V.k1, 1)} vs vecinas)`, "#3A9E6E"],
  ];
  const pos = m
    ? [[0, 0, 120], [130, 0, 110], [0, 66, 190], [250, 0, 130], [200, 66, 190]]
    : [[0, 0, 120], [120, 0, 118], [238, 0, 186], [424, 0, 112], [536, 0, 214]];
  const fila = g.append("g").attr("transform", m ? `translate(14,${H - 196})` : "translate(24,500)");
  const nodos = celdas.map(([t, v, c], i) => {
    const [x, y, w] = pos[i];
    const k = fila.append("g").attr("transform", `translate(${x},${y})`);
    k.append("rect").attr("width", w - 10).attr("height", 3).attr("fill", c);
    k.append("text").attr("y", 21).attr("font-size", 13).attr("fill", GRIS).text(t);
    k.append("text").attr("y", 43).attr("font-size", m ? 15.5 : 16.5).attr("font-weight", 700).attr("fill", TINTA).text(v);
    return k;
  });
  const nota = lineas(fila, 0, m ? 150 : 76, m
    ? ["Cada capa deja un número en la fila de la parcela.", "Así se arma la tabla: una fila por parcela."]
    : "Cada capa deja un número en la fila de la parcela. Así se arma la tabla: una fila por parcela.", { size: 13 });
  const lim = (v) => Math.max(0, Math.min(1, v));
  /** t = 1: capas separadas; t = CAPAS_FIN: capas juntas y fila completa. */
  const colocar = (t, todo = false) => {
    const u = lim((1 - t) / (1 - CAPAS_FIN));
    lista.forEach((o, i) => {
      const y = junto + (base - i * paso - junto) * t;
      o.c.attr("transform", `translate(${cx},${y.toFixed(1)})`);
      o.etq.attr("opacity", todo ? 1 : lim((t - 0.55) / 0.3));
    });
    nodos.forEach((k, i) => k.attr("opacity", todo ? 1 : lim(u * 6 - i)));
    nota.attr("opacity", todo ? 1 : lim(u * 6 - 5));
  };
  colocar(1);
  return { colocar };
}

/* 3. El territorio: rendimiento conocido y media de los municipios grandes */
function territorio(g, W, H, m) {
  const proy = d3.geoIdentity().reflectY(true).fitExtent([[24, m ? 30 : 44], [W - 24, H - (m ? 70 : 24)]], D.COLECCION);
  g.selectAll("circle").data(D.REP).join("circle").attr("cx", (p) => proy([p.x, p.y])[0]).attr("cy", (p) => proy([p.x, p.y])[1])
    .attr("r", m ? 3.8 : 5).attr("fill", (p) => colorV(p.obs)).attr("stroke", "#fff").attr("stroke-width", 0.8);
  D.MUNICIPIOS.filter(([, ps]) => ps.filter((p) => !p.oculta).length > 8).forEach(([mun, ps]) => {
    const rep = ps.filter((p) => !p.oculta);
    g.append("text").attr("x", d3.mean(rep, (p) => proy([p.x, p.y])[0])).attr("y", d3.min(rep, (p) => proy([p.x, p.y])[1]) - 12)
      .attr("text-anchor", "middle").attr("font-size", m ? 13 : 14.5).attr("font-weight", 700).attr("fill", TINTA)
      .attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4)
      .text(`${corto(mun)}: ${f(d3.mean(rep, (p) => p.obs))} t/ha`);
  });
  dentro(g, W);
  const ley = g.append("g").attr("transform", m ? `translate(24,${H - 40})` : "translate(540,548)");
  ley.append("text").attr("y", -9).attr("font-size", 12.5).attr("fill", GRIS).text("Rendimiento conocido (t/ha)");
  RAMPA.forEach((c, i) => ley.append("rect").attr("x", i * 37).attr("width", 35).attr("height", 10).attr("fill", c));
  ["3", "3.5", "4", "4.5", "5"].forEach((t, i) => ley.append("text").attr("x", (i + 1) * 37 - 1).attr("y", 25).attr("text-anchor", "middle").attr("font-size", 12).attr("fill", GRIS).text(t));
}

/* 4. Vecinas de la parcela de ejemplo (las líneas se trazan con el scroll) */
function vecinas(g, W, H, m) {
  const p = vit(), r = modeloFinal(p);
  const arriba = m ? 128 : 20;
  const R = d3.max(r.vecinas, (v) => v.d) * 1.1;
  const asp = (W - 40) / (H - arriba - 20);
  const proy = d3.geoIdentity().reflectY(true).fitExtent([[20, arriba], [W - 20, H - 20]], cajaUTM(p.x - R * asp, p.y - R, p.x + R * asp, p.y + R));
  const ruta = d3.geoPath(proy);
  const [cx, cy] = proy([p.x, p.y]);
  const wmax = d3.max(r.vecinas, (v) => v.w);
  const ls = g.append("g").selectAll("line").data(r.vecinas).join("line").attr("x1", cx).attr("y1", cy)
    .attr("x2", (v) => proy([v.q.x, v.q.y])[0]).attr("y2", (v) => proy([v.q.x, v.q.y])[1])
    .attr("stroke", "#5B636B").attr("stroke-opacity", 0.75).attr("stroke-width", (v) => 0.7 + (9 * v.w) / wmax);
  const cerca = D.P.filter((q) => Math.abs(q.x - p.x) < R * asp * 1.1 && Math.abs(q.y - p.y) < R * 1.1);
  g.append("g").selectAll("path").data(cerca).join("path").attr("d", (q) => ruta(featureDe(q)))
    .attr("fill", (q) => (q.id === p.id || q.oculta ? "#fff" : colorV(q.obs))).attr("stroke", (q) => (q.id === p.id ? "#C27A12" : TINTA))
    .attr("stroke-width", (q) => (q.id === p.id ? 3 : 0.6));
  g.append("circle").attr("cx", cx).attr("cy", cy).attr("r", 8).attr("fill", "#fff").attr("stroke", "#C27A12").attr("stroke-width", 3);
  g.append("text").attr("x", cx + 12).attr("y", cy + 22).attr("font-size", 14).attr("font-weight", 700).attr("fill", "#A9650C")
    .attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4).text(p.id);
  const top = [...r.vecinas].sort((a, b) => b.w - a.w).slice(0, 3);
  const marca = (sel, i) => {
    sel.append("circle").attr("r", 9).attr("fill", TINTA).attr("stroke", "#fff").attr("stroke-width", 1.5);
    sel.append("text").attr("text-anchor", "middle").attr("dy", ".35em").attr("font-size", 11).attr("font-weight", 700).attr("fill", "#fff").text(i + 1);
  };
  top.forEach((v, i) => { const [x, y] = proy([v.q.x, v.q.y]); marca(g.append("g").attr("transform", `translate(${x},${y})`), i); });
  const lista = g.append("g").attr("transform", m ? "translate(12,22)" : "translate(30,44)");
  lista.append("rect").attr("x", -10).attr("y", -22).attr("width", m ? W - 4 : 340).attr("height", 34 + top.length * 25).attr("fill", "#fff").attr("stroke", "#D2D6CE");
  lista.append("text").attr("font-size", 13.5).attr("font-weight", 700).attr("fill", TINTA).text("Las tres vecinas que más pesan");
  top.forEach((v, i) => {
    const t = lista.append("g").attr("transform", `translate(0,${25 * (i + 1)})`);
    marca(t.append("g").attr("transform", "translate(9,0)"), i);
    t.append("text").attr("x", 26).attr("dy", ".35em").attr("font-size", 13).attr("fill", TINTA).text(`${v.id}: ${f(v.obs)} t/ha, a ${f(v.d, 0)} m, peso ${f(v.w * 100, 0)} %`);
  });
  const b = g.append("g").attr("transform", `translate(${W - 20 - 1000 * proy.scale()},${H - 12})`);
  b.append("rect").attr("x", -8).attr("y", -24).attr("width", 1000 * proy.scale() + 16).attr("height", 34).attr("fill", "#fff").attr("fill-opacity", 0.85);
  b.append("rect").attr("width", 1000 * proy.scale()).attr("height", 4).attr("fill", TINTA);
  b.append("text").attr("y", -7).attr("font-size", 12.5).attr("fill", GRIS).text("1 km");
  return { lineas: ls.nodes() };
}

/* 5. Curvas de verdor (la curva se traza con el scroll) */
function verdor(g, W, H, m) {
  const V = D.VIT, c0 = V.curvas[0];
  const mg = m ? { l: 40, r: 12, t: 44, b: 40 } : { l: 70, r: 30, t: 48, b: 60 };
  const x = d3.scaleLinear([91, 304], [mg.l, W - mg.r]), y = d3.scaleLinear([0.15, 0.9], [H - mg.b, mg.t]);
  const meses = m ? [[91, "abr"], [152, "jun"], [213, "ago"], [274, "oct"]] : [[91, "abr"], [121, "may"], [152, "jun"], [182, "jul"], [213, "ago"], [244, "sep"], [274, "oct"], [304, "31 oct"]];
  g.append("g").attr("transform", `translate(0,${H - mg.b})`)
    .call(d3.axisBottom(x).tickValues(meses.map((d) => d[0])).tickFormat((d, i) => meses[i][1]).tickSize(-(H - mg.b - mg.t))).call(limpiarEje());
  g.append("g").attr("transform", `translate(${mg.l},0)`).call(d3.axisLeft(y).ticks(5).tickSize(0).tickPadding(8)).call(limpiarEje());
  g.append("text").attr("x", mg.l).attr("y", mg.t - 22).attr("font-size", 13).attr("fill", GRIS).text("NDVI (verdor)");
  const linea = d3.line().defined((d) => d[1] != null).x((d) => x(d[0])).y((d) => y(d[1]));
  const serie = (c) => c.curva.map((v, i) => [i + 1, v]).filter((d) => d[0] >= 91);
  V.curvas.slice(1).forEach((c) => g.append("path").attr("d", linea(serie(c))).attr("fill", "none").attr("stroke", "#9AA1A8").attr("stroke-width", 1.2));
  const area = d3.area().defined((d) => d[1] != null).x((d) => x(d[0])).y0(y(c0.base)).y1((d) => y(Math.max(d[1], c0.base)));
  const ar = g.append("path").attr("d", area(serie(c0).filter((d) => d[0] >= c0.inicio && d[0] <= c0.fin))).attr("fill", "#3A9E6E").attr("fill-opacity", 0.22);
  g.append("line").attr("x1", x(91)).attr("x2", x(304)).attr("y1", y(c0.base)).attr("y2", y(c0.base)).attr("stroke", "#3A9E6E").attr("stroke-dasharray", "5 4");
  g.append("text").attr("x", x(302)).attr("y", y(c0.base) + 18).attr("text-anchor", "end").attr("font-size", 12.5).attr("fill", "#2b7a54").text("nivel de abril–mayo (mediana)");
  g.selectAll("circle").data(c0.capturas.filter((c) => c[0] >= 91)).join("circle").attr("cx", (c) => x(c[0])).attr("cy", (c) => y(c[1])).attr("r", 2.4).attr("fill", "#3A9E6E").attr("opacity", 0.45);
  const cu = g.append("path").attr("d", linea(serie(c0))).attr("fill", "none").attr("stroke", "#3A9E6E").attr("stroke-width", 3);
  g.append("text").attr("x", x(c0.dia_pico)).attr("y", y(c0.pico) - 12).attr("text-anchor", "middle").attr("font-size", 14).attr("font-weight", 700).attr("fill", TINTA).text(`${V.id}: área ${f(V.integral, 1)}`);
  lineas(g, x(m ? 95 : 128), y(0.86), m ? [`Gris: ${V.vecinas_1km.length} vecinas a menos de 1 km,`, `mediana ${f(V.mediana_vecinas, 1)}`] : `Gris: sus ${V.vecinas_1km.length} vecinas a menos de 1 km, mediana ${f(V.mediana_vecinas, 1)}`, { size: 13 });
  return { curva: cu.node(), area: ar.node() };
}

/* 6. Lluvia de octubre por celdas y por año */
function lluvia(g, W, H, m) {
  const V = D.VIT, p = vit(), todas = V.celdas["2025"];
  const xs = todas.flatMap((c) => c.poly.map((q) => q[0])), ys = todas.flatMap((c) => c.poly.map((q) => q[1]));
  const zona = m ? [[14, 14], [W - 14, 330]] : [[20, 30], [470, 570]];
  const proy = d3.geoIdentity().reflectY(true).fitExtent(zona, cajaUTM(d3.min(xs), d3.min(ys), d3.max(xs), d3.max(ys)));
  const ruta = d3.geoPath(proy);
  const azul = d3.scaleLinear([110, 175], ["#cde2fb", "#256abf"]);
  todas.forEach((c) => {
    g.append("path").attr("d", "M" + c.poly.map((q) => proy(q).join(",")).join("L") + "Z").attr("fill", azul(c.valor))
      .attr("stroke", c.area > 0 ? TINTA : "#fff").attr("stroke-width", c.area > 0 ? 2 : 1.5);
    const cxy = proy([d3.mean(c.poly.slice(0, 4), (q) => q[0]), d3.mean(c.poly.slice(0, 4), (q) => q[1])]);
    g.append("text").attr("x", cxy[0]).attr("y", cxy[1] + 5).attr("text-anchor", "middle").attr("font-size", m ? 12 : 13).attr("fill", c.valor > 150 ? "#fff" : TINTA).text(`${f(c.valor, 0)} mm`);
  });
  g.append("path").attr("d", ruta(featureDe(p))).attr("fill", "#C27A12").attr("stroke", "#C27A12").attr("stroke-width", 2);
  const [px, py] = proy([p.x, p.y]);
  g.append("circle").attr("cx", px).attr("cy", py).attr("r", 10).attr("fill", "none").attr("stroke", "#C27A12").attr("stroke-width", 2);
  g.append("text").attr("x", px).attr("y", py + 30).attr("text-anchor", "middle").attr("font-size", 13.5).attr("font-weight", 700).attr("fill", TINTA)
    .attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4).text(V.id);
  const anios = ["2022", "2023", "2024", "2025"];
  const [bx0, bx1, by0, by1, ty] = m ? [20, W - 20, H - 40, 420, 360] : [520, 770, 520, 90, 52];
  const xb = d3.scaleBand(anios, [bx0, bx1]).padding(0.28), yb = d3.scaleLinear([0, 170], [by0, by1]);
  g.append("text").attr("x", bx0).attr("y", ty).attr("font-size", 13.5).attr("font-weight", 700).attr("fill", TINTA).text("Lluvia de octubre en la parcela (mm)");
  g.append("text").attr("x", bx0).attr("y", ty + 19).attr("font-size", 12.5).attr("fill", GRIS).text(`línea: promedio 2022–2024, ${f(V.lluvia_ref, 0)} mm`);
  anios.forEach((a) => {
    const v = V.lluvia_pond[a];
    g.append("rect").attr("x", xb(a)).attr("y", yb(v)).attr("width", xb.bandwidth()).attr("height", yb(0) - yb(v)).attr("fill", a === "2025" ? "#2F6FD6" : "#9ec5f4");
    g.append("text").attr("x", xb(a) + xb.bandwidth() / 2).attr("y", yb(v) - 6).attr("text-anchor", "middle").attr("font-size", 12.5).attr("fill", TINTA).text(f(v, 0));
    g.append("text").attr("x", xb(a) + xb.bandwidth() / 2).attr("y", by0 + 19).attr("text-anchor", "middle").attr("font-size", 12.5).attr("fill", GRIS).text(a);
  });
  g.append("line").attr("x1", bx0 - 5).attr("x2", bx1 + 5).attr("y1", yb(V.lluvia_ref)).attr("y2", yb(V.lluvia_ref)).attr("stroke", TINTA).attr("stroke-dasharray", "5 4");
  if (!m) g.append("text").attr("x", bx0).attr("y", 576).attr("font-size", 14).attr("font-weight", 700).attr("fill", "#2F6FD6").text(`2025: ${fs(V.anom, 1)} % sobre el promedio`);
}

/* 7. Composición del modelo para la parcela de ejemplo */
function modelo(g, W, H, m) {
  const p = vit(), r = modeloFinal(p), M = D.M;
  const caja = (x, y, w, tit, val, color, sub) => {
    const c = g.append("g").attr("transform", `translate(${x},${y})`);
    c.append("rect").attr("width", w).attr("height", 74).attr("fill", "#fff").attr("stroke", color).attr("stroke-width", 2);
    c.append("rect").attr("width", 6).attr("height", 74).attr("fill", color);
    c.append("text").attr("x", 18).attr("y", 26).attr("font-size", m ? 13 : 14).attr("fill", GRIS).text(tit);
    c.append("text").attr("x", 18).attr("y", 58).attr("font-size", m ? 23 : 26).attr("font-weight", 800).attr("fill", TINTA).text(val);
    if (sub) c.append("text").attr("x", w - 12).attr("y", 58).attr("text-anchor", "end").attr("font-size", 13).attr("fill", GRIS).text(sub);
  };
  const id = `punta-mod-${m ? "m" : "e"}`;
  punta(g, id);
  const flecha = (x1, y1, x2, y2) => g.append("path").attr("d", `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}`)
    .attr("fill", "none").attr("stroke", "#7A848D").attr("stroke-width", 1.6).attr("marker-end", `url(#${id})`);
  const gr = corto(p.mun);
  if (m) {
    caja(8, 8, 186, `Media de ${gr}`, f(r.MUN), COLORES.MUN);
    caja(206, 8, 186, "20 vecinas (IDW)", f(r.IDW), COLORES.MUN);
    caja(8, 128, 186, "MIX, referencia", f(r.MIX), COLORES.MIX);
    caja(206, 128, 186, `Grupo ${gr}`, f(M.J[p.grupo]), COLORES.J);
    caja(8, 248, 186, "K, con verdor", f(r.K), COLORES.K, fs(r.K - r.MIX));
    caja(206, 248, 186, "J, con lluvia", f(r.J), COLORES.J, fs(r.J - M.J[p.grupo]));
    caja(70, 380, 260, "E_JK = ½ K + ½ J", `${f(r.E)} t/ha`, COLORES.E_JK);
    flecha(101, 82, 101, 126); flecha(299, 82, 120, 126); flecha(101, 202, 101, 246); flecha(299, 202, 299, 246);
    flecha(101, 322, 160, 378); flecha(299, 322, 240, 378);
  } else {
    caja(30, 30, 220, `Media de ${gr}`, f(r.MUN), COLORES.MUN);
    caja(270, 30, 220, "20 vecinas (IDW)", f(r.IDW), COLORES.MUN);
    caja(150, 160, 230, "MIX, referencia", f(r.MIX), COLORES.MIX);
    caja(150, 290, 230, "K, con verdor relativo", f(r.K), COLORES.K, fs(r.K - r.MIX));
    caja(520, 160, 250, `Nivel del grupo ${gr}`, f(M.J[p.grupo]), COLORES.J);
    caja(520, 290, 250, "J, con lluvia de octubre", f(r.J), COLORES.J, fs(r.J - M.J[p.grupo]));
    caja(290, 450, 260, "E_JK = ½ K + ½ J", `${f(r.E)} t/ha`, COLORES.E_JK);
    flecha(140, 104, 230, 158); flecha(380, 104, 300, 158); flecha(265, 234, 265, 288); flecha(645, 234, 645, 288);
    flecha(265, 364, 380, 448); flecha(645, 364, 470, 448);
  }
}

/* 8. Once experimentos frente a MIX */
function experimentos(g, W, H, m) {
  const E = D.EV.experimentos;
  const mg = m ? { l: 16, r: 16, t: 54, b: 52 } : { l: 330, r: 40, t: 56, b: 60 };
  const x = d3.scaleLinear([-0.016, 0.028], [mg.l, W - mg.r]);
  const y = d3.scaleBand(E.map((e) => e.id), [mg.t, H - mg.b]).padding(m ? 0.15 : 0.4);
  g.append("g").attr("transform", `translate(0,${H - mg.b})`)
    .call(d3.axisBottom(x).ticks(m ? 4 : 6).tickFormat((d) => (d === 0 ? "MIX" : fs(d, 2))).tickSize(-(H - mg.b - mg.t)))
    .call(limpiarEje(12.5)).call((a) => a.selectAll("line").attr("stroke", (d) => (d === 0 ? TINTA : RAYA)).attr("stroke-width", (d) => (d === 0 ? 1.5 : 1)));
  lineas(g, mg.l, H - 14, m ? "Diferencia de RMSE con MIX (t/ha)" : "Diferencia de RMSE con MIX (t/ha): a la izquierda, mejor", { size: 12.5 });
  const fila = g.selectAll(".e").data(E).join("g").attr("transform", (e) => `translate(0,${y(e.id) + y.bandwidth() * (m ? 0.72 : 0.5)})`);
  if (m) fila.append("text").attr("x", mg.l).attr("y", -13).attr("font-size", 12.5).attr("fill", TINTA).attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4).text((e) => `${e.id.replace("EXP_", "")}. ${e.nombre}`);
  else fila.append("text").attr("x", mg.l - 14).attr("dy", ".35em").attr("text-anchor", "end").attr("font-size", 13.5).attr("fill", TINTA).text((e) => `${e.id.replace("EXP_", "")}. ${e.nombre}`);
  fila.append("line").attr("x1", x(0)).attr("x2", (e) => x(e.rmse - e.mix)).attr("stroke", "#C9CFC6").attr("stroke-width", 2);
  fila.append("path").attr("d", (e) => (e.escenario === "FULL" ? d3.symbol(d3.symbolSquare, 70)() : d3.symbol(d3.symbolCircle, 80)()))
    .attr("transform", (e) => `translate(${x(e.rmse - e.mix)},0)`)
    .attr("fill", (e) => (e.id === "EXP_11" ? "#C27A12" : e.rmse < e.mix ? TINTA : "#9AA1A8"))
    .on("pointerenter pointermove", (ev, e) => { if (ev.pointerType !== "touch") mostrarTip(`<b>${e.id}</b> ${e.nombre}<br>RMSE ${f(e.rmse, 4)} frente a MIX ${f(e.mix, 4)}<br><span class="s">${e.fuente}</span>`, ev); })
    .on("pointerleave", ocultarTip);
  fila.filter((e) => e.id === "EXP_11").append("text").attr("x", (e) => x(e.rmse - e.mix)).attr("y", 22).attr("text-anchor", "middle")
    .attr("font-size", 12.5).attr("font-weight", 700).attr("fill", "#A9650C").text("entrega");
  const ley = g.append("g").attr("transform", `translate(${mg.l},${m ? 18 : 24})`);
  ley.append("path").attr("d", d3.symbol(d3.symbolSquare, 60)()).attr("transform", "translate(6,0)").attr("fill", GRIS);
  ley.append("text").attr("x", 16).attr("dy", ".35em").attr("font-size", 12.5).attr("fill", GRIS).text("138 parcelas (FULL)");
  ley.append("path").attr("d", d3.symbol(d3.symbolCircle, 70)()).attr("transform", "translate(166,0)").attr("fill", GRIS);
  ley.append("text").attr("x", 176).attr("dy", ".35em").attr("font-size", 12.5).attr("fill", GRIS).text("municipio visto (SEEN)");
}

/* 9. Cinco evaluaciones */
function evaluaciones(g, W, H, m) {
  const EV = D.EV.evaluaciones, orden = ["MUN", "MIX", "J", "K", "E_JK"];
  const mg = m ? { l: 16, r: 16, t: 60, b: 52 } : { l: 320, r: 30, t: 76, b: 60 };
  const x = d3.scaleLinear([0.465, 0.512], [mg.l, W - mg.r]);
  const y = d3.scaleBand(EV.map((e) => e.nombre), [mg.t, H - mg.b]).padding(m ? 0.2 : 0.5);
  g.append("g").attr("transform", `translate(0,${H - mg.b})`).call(d3.axisBottom(x).ticks(5).tickFormat((d) => f(d, 2)).tickSize(-(H - mg.b - mg.t))).call(limpiarEje(12.5));
  lineas(g, mg.l, H - 14, "RMSE (t/ha): a la izquierda, menor error", { size: 12.5 });
  const fila = g.selectAll(".v").data(EV).join("g").attr("transform", (e) => `translate(0,${y(e.nombre) + y.bandwidth() * (m ? 0.7 : 0.5)})`);
  if (m) fila.append("text").attr("x", mg.l).attr("y", -16).attr("font-size", 12.5).attr("fill", TINTA).attr("paint-order", "stroke").attr("stroke", "#fff").attr("stroke-width", 4).text((e) => `${e.corto} (${e.parcelas})`);
  else fila.append("text").attr("x", mg.l - 14).attr("dy", ".35em").attr("text-anchor", "end").attr("font-size", 13.5).attr("fill", TINTA).text((e) => `${e.corto} (${e.parcelas})`);
  fila.append("line").attr("x1", (e) => x(d3.min(orden, (k) => e.rmse[k]))).attr("x2", (e) => x(d3.max(orden, (k) => e.rmse[k]))).attr("stroke", "#D2D6CE").attr("stroke-width", 1.5);
  fila.each(function (e) {
    const s = d3.select(this);
    orden.forEach((k) => s.append("circle").attr("cx", x(e.rmse[k])).attr("r", k === "E_JK" ? 8 : 6).attr("fill", COLORES[k]).attr("stroke", "#fff").attr("stroke-width", 1.5)
      .on("pointerenter pointermove", (ev) => { if (ev.pointerType !== "touch") mostrarTip(`<b>${NOMBRES[k]}</b><br>${e.nombre}<br>RMSE <b class="num">${f(e.rmse[k], 4)}</b>`, ev); })
      .on("pointerleave", ocultarTip));
  });
  const ley = g.append("g").attr("transform", `translate(${mg.l + 6},${m ? 20 : 30})`);
  orden.forEach((k, i) => {
    const c = ley.append("g").attr("transform", `translate(${[0, 70, 132, 182, 234][i]},0)`);
    c.append("circle").attr("r", 6).attr("fill", COLORES[k]);
    c.append("text").attr("x", 10).attr("dy", ".35em").attr("font-size", 12.5).attr("fill", TINTA).text(k);
  });
}

/* 10. El techo: varianza explicada y curva de aprendizaje */
function techo(g, W, H, m) {
  const EV = D.EV, x = d3.scaleLinear([0, 1], [m ? 16 : 40, W - (m ? 16 : 40)]);
  const vm = EV.varianza_municipio, quita = EV.quita_error_mun[0];
  const barra = (y, titulo, parte, color, txtParte, txtResto, fuera) => {
    lineas(g, x(0), y, titulo, { size: m ? 14 : 15, color: TINTA, peso: 700 });
    g.append("rect").attr("x", x(0)).attr("y", y + 12).attr("width", x(parte) - x(0)).attr("height", 32).attr("fill", color);
    g.append("rect").attr("x", x(parte) + 2).attr("y", y + 12).attr("width", x(1) - x(parte) - 2).attr("height", 32).attr("fill", "#E8EAE3");
    if (m) {
      g.append("text").attr("x", x(0)).attr("y", y + 64).attr("font-size", 13).attr("font-weight", 700).attr("fill", TINTA).text(txtParte);
      g.append("text").attr("x", x(1)).attr("y", y + 64).attr("text-anchor", "end").attr("font-size", 13).attr("fill", GRIS).text(txtResto);
    } else {
      g.append("text").attr("x", fuera ? x(parte) + 12 : x(0) + 12).attr("y", y + 33).attr("font-size", 13.5).attr("font-weight", 700).attr("fill", fuera ? TINTA : "#fff").text(txtParte);
      g.append("text").attr("x", x(1) - 12).attr("y", y + 33).attr("text-anchor", "end").attr("font-size", 13.5).attr("fill", TINTA).text(txtResto);
    }
  };
  barra(m ? 20 : 34, m ? "Variación del rendimiento (138 parcelas)" : "Variación del rendimiento entre las 138 parcelas", vm, "#5B636B", `El municipio: ${pct(vm, 1)}`, `dentro del municipio: ${pct(1 - vm, 1)}`);
  barra(m ? 118 : 124, m ? "Error que deja la media municipal" : "Error que deja la media municipal (validación cruzada)", quita, "#C27A12", `E_JK quita ${pct(quita, 1)}`, `sin explicar: ${pct(1 - quita, 1)}`, true);
  // curva de aprendizaje: MIX con submuestras de las 138 (200 sorteos por tamaño), ajuste MSE = s² + c/n
  const A = EV.aprendizaje, s2 = A.techo ** 2, c = 220 * (A.con_220 ** 2 - s2);
  const ajuste = d3.range(41, 221).map((n) => [n, Math.sqrt(s2 + c / n)]);
  const top = m ? 270 : 290, bot = m ? H - 46 : 540;
  const xc = d3.scaleLinear([30, 230], [m ? 54 : 84, W - (m ? 14 : 40)]), yc = d3.scaleLinear([0.465, 0.515], [bot, top]);
  lineas(g, m ? 16 : 40, top - 36, m ? ["Error de MIX con más parcelas", "del mismo tipo (RMSE, t/ha)"] : "Error de MIX con más parcelas del mismo tipo (RMSE, t/ha)", { size: m ? 14 : 15, color: TINTA, peso: 700 });
  g.append("g").attr("transform", `translate(0,${bot})`).call(d3.axisBottom(xc).tickValues(m ? [41, 124, 220] : [41, 83, 124, 138, 180, 220]).tickSize(-(bot - top))).call(limpiarEje(12.5));
  g.append("g").attr("transform", `translate(${xc(30)},0)`).call(d3.axisLeft(yc).ticks(5).tickFormat((d) => f(d, 2)).tickSize(0).tickPadding(8)).call(limpiarEje(12.5));
  g.append("line").attr("x1", xc(30)).attr("x2", xc(230)).attr("y1", yc(A.techo)).attr("y2", yc(A.techo)).attr("stroke", "#7A848D").attr("stroke-dasharray", "2 4");
  g.append("text").attr("x", xc(230)).attr("y", yc(A.techo) + 17).attr("text-anchor", "end").attr("font-size", 12.5).attr("fill", GRIS).text(`techo estimado: ${f(A.techo)}`);
  g.append("line").attr("x1", xc(138)).attr("x2", xc(138)).attr("y1", top).attr("y2", bot).attr("stroke", TINTA).attr("stroke-width", 1.2);
  g.append("text").attr("x", xc(138) + 7).attr("y", top + 14).attr("font-size", 12.5).attr("fill", TINTA).text("hoy: 138");
  g.append("path").attr("d", d3.line().x((d) => xc(d[0])).y((d) => yc(d[1]))(ajuste)).attr("fill", "none").attr("stroke", "#5B636B").attr("stroke-width", 2).attr("stroke-dasharray", "6 4");
  A.n.forEach((n, i) => g.append("circle").attr("cx", xc(n)).attr("cy", yc(A.rmse_mix[i])).attr("r", 5).attr("fill", "#5B636B").attr("stroke", "#fff").attr("stroke-width", 1.5));
  const fin = ajuste.at(-1);
  g.append("circle").attr("cx", xc(fin[0])).attr("cy", yc(fin[1])).attr("r", 5).attr("fill", "#fff").attr("stroke", "#5B636B").attr("stroke-width", 2);
  g.append("text").attr("x", xc(fin[0])).attr("y", yc(fin[1]) - 13).attr("text-anchor", "end").attr("font-size", 12.5).attr("fill", TINTA).text(`con 220: ${f(fin[1], 3)}`);
  g.append("text").attr("x", xc(230)).attr("y", bot + 36).attr("text-anchor", "end").attr("font-size", 12.5).attr("fill", GRIS).text(m ? "parcelas para entrenar" : "parcelas con rendimiento conocido para entrenar");
}

/* 11. Despliegue real */
function despliegue(g, W, H, m, salud) {
  const nodo = (x, y, w, h, t1, t2, oscuro) => {
    const c = g.append("g").attr("transform", `translate(${x},${y})`);
    c.append("rect").attr("width", w).attr("height", h).attr("fill", oscuro ? "#022448" : "#fff").attr("stroke", oscuro ? "#022448" : TINTA).attr("stroke-width", 1.5);
    c.append("text").attr("x", 14).attr("y", 25).attr("font-size", m ? 14 : 15).attr("font-weight", 700).attr("fill", oscuro ? "#fff" : TINTA).text(t1);
    lineas(c, 14, 46, t2, { size: m ? 12 : 12.5, color: oscuro ? "#C9D6E6" : GRIS });
  };
  const id = `punta-dep-${m ? "m" : "e"}`;
  punta(g, id);
  const fl = (x1, y1, x2, y2, t, lado = "der") => {
    g.append("line").attr("x1", x1).attr("y1", y1).attr("x2", x2).attr("y2", y2).attr("stroke", "#7A848D").attr("stroke-width", 1.6).attr("marker-end", `url(#${id})`);
    if (t) g.append("text").attr("x", (x1 + x2) / 2 + (lado === "der" ? 8 : -8)).attr("y", (y1 + y2) / 2 + 4).attr("text-anchor", lado === "der" ? "start" : "end").attr("font-size", 12.5).attr("fill", GRIS).text(t);
  };
  const lambda = salud ? `Python ${salud.python.split(".").slice(0, 2).join(".")}, ${salud.region}` : "Python 3.13 en arm64";
  if (m) {
    nodo(10, 10, 380, 66, "Repositorio del equipo", "cuadernos, recetas del modelo y datos");
    fl(60, 78, 60, 126);
    fl(340, 78, 340, 126);
    lineas(g, 200, 96, ["uv y npm: sitio y datos", "uv: paquete de la API"], { size: 12, ancla: "middle" });
    nodo(10, 128, 185, 78, "Amazon S3", ["página, datos y", "descargas (privado)"]);
    nodo(205, 128, 185, 78, "AWS Lambda", ["reentrena E_JK;", lambda], true);
    fl(102, 208, 102, 262, "/*");
    fl(298, 208, 298, 262, "/api/*", "izq");
    nodo(10, 264, 380, 66, "CloudFront", "un dominio con HTTPS; firma las llamadas a la API");
    fl(200, 332, 200, 380, "página, datos y reentrenamiento");
    nodo(10, 382, 380, 66, "Navegador del jurado", "consulta, ejecuta, reentrena y descarga", true);
    lineas(g, 10, 486, ["Terraform crea el bucket, la función y la", "distribución; nada se configura a mano."], { size: 13 });
  } else {
    nodo(40, 30, 330, 70, "Repositorio del equipo", "cuadernos, recetas del modelo y datos del reto");
    nodo(430, 30, 330, 70, "Terraform", "crea el bucket, la función y la distribución");
    nodo(40, 180, 330, 70, "Amazon S3 (privado)", "esta página, datos JSON y descargas");
    nodo(430, 180, 330, 70, "AWS Lambda", `reentrena E_JK; ${lambda}`, true);
    nodo(40, 330, 720, 70, "CloudFront", "un solo dominio con HTTPS: /* va a S3 y /api/* a Lambda, con llamadas firmadas");
    nodo(235, 480, 330, 70, "Navegador del jurado", "consulta, ejecuta, reentrena y descarga", true);
    fl(205, 102, 205, 177, "uv y npm: sitio y datos");
    fl(370, 66, 500, 177, "uv: paquete de la API");
    fl(205, 252, 205, 327, "/*");
    fl(595, 252, 595, 327, "/api/*");
    fl(400, 402, 400, 477, "HTTPS");
  }
}

/** Alto en teléfono (el ancho es 400) y pie de cada escena. */
export function escenas(salud) {
  const V = D.VIT, p = vit();
  const c25 = V.celdas["2025"].filter((c) => c.area > 0), tot = d3.sum(c25, (c) => c.area), mayor = d3.max(c25, (c) => c.area);
  const lado = ((V.elev.paso * V.elev.n) / 1000).toLocaleString("es-MX", { maximumFractionDigits: 1 });
  return {
    oculto: { alto: 500, fn: oculto, pie: "Las 59 ocultas están repartidas entre las 138 con rendimiento conocido." },
    capas: { alto: 560, fn: capas, pie: `Escala real alrededor de ${V.id}: ${lado} km por lado. Al juntarse, cada capa deja un número en la fila de la parcela.` },
    territorio: { alto: 520, fn: territorio, pie: "Rendimiento conocido y media de los municipios con más parcelas." },
    vecinas: { alto: 540, fn: vecinas, pie: "Grosor de cada línea: peso de la vecina en la referencia territorial." },
    verdor: { alto: 400, fn: verdor, pie: "Curva de verdor suavizada (mediana móvil de 15 días). Área: lo que queda sobre el nivel de abril–mayo entre el inicio y el fin de la temporada." },
    lluvia: { alto: 640, fn: lluvia, pie: `Celdas CHIRPS de octubre de 2025 alrededor de la parcela. Contorno oscuro: las ${c25.length} celdas que toca; el ${f((mayor / tot) * 100, 1)} % de su área cae en una. En 2025 llovió ${fs(V.anom, 1)} % sobre el promedio.` },
    modelo: { alto: 470, fn: modelo, pie: `Números de ${p.id}, calculados en este navegador.` },
    experimentos: { alto: 640, fn: experimentos, pie: "Mejor procedimiento de cada experimento frente a MIX en su mismo escenario de validación. Cuadros y círculos usan escenarios distintos: no se comparan entre sí." },
    evaluaciones: { alto: 520, fn: evaluaciones, pie: "RMSE de cada modelo en cada evaluación. Con solo 35 parcelas, la caja cerrada no distingue diferencias de 1 a 2 %." },
    techo: { alto: 600, fn: techo, pie: "Arriba: varianza dentro de muestra y error fuera de muestra. Abajo: MIX entrenado con submuestras de las 138, 200 sorteos por tamaño; línea discontinua: ajuste MSE = s² + c/n." },
    despliegue: { alto: 530, fn: (g, W, H, m) => despliegue(g, W, H, m, salud), pie: salud ? `Así está desplegada esta página. La función respondió desde ${salud.region} con el commit ${salud.commit}.` : "Así está desplegada esta página." },
  };
}
