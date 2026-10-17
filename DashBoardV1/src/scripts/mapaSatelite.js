// Mapa satelital del tablero: Leaflet sobre Esri World Imagery, con la misma selección que el resto de la página.
// Al elegir una parcela: marco que se cierra sobre ella, anillo de 1 km con sus vecinas, ficha flotante y recorrido por pasos.
import * as d3 from "d3";
import L from "leaflet";
import {
  D, RAMPA, COLORES, TINTA, f, fs, pct, corto, clase, colorV, surcos, htmlParcela, mostrarTip, ocultarTip,
  seleccionar, alSeleccionar, estado,
} from "./comun.js";
import { utm2ll, ESRI } from "./satelite.js";

const GRUPOS = { Chignahuapan: "#2F6FD6", Tlaxcala: "#C27A12", Singuilucan: "#B4477A", Otros_Hidalgo: "#3A9E6E", Almoloya: "#7A5CC2" };
const lluvia = d3.scaleSequential([0, 125], d3.interpolateBlues);
const error = d3.scaleLinear([0, 0.3, 0.6, 1], ["#3A9E6E", "#C9D36A", "#E0913A", "#B2412C"]).clamp(true);
const valor = (p) => (p.oculta ? p.pred : p.obs);
const vecinasDe = (p) => D.P.filter((q) => q.id !== p.id && Math.hypot(q.x - p.x, q.y - p.y) < 1000)
  .sort((a, b) => Math.hypot(a.x - p.x, a.y - p.y) - Math.hypot(b.x - p.x, b.y - p.y));

/* Cada modo pinta el mapa de una forma y trae su leyenda. */
const MODOS = {
  rend: {
    estilo: (p) => ({ fillColor: p.oculta ? `url(#L-s${clase(p.pred)})` : colorV(p.obs), fillOpacity: 0.92 }),
    ley: () => `<div class="lt">Rendimiento (t/ha)</div><div class="fil">${RAMPA.map((c) => `<span class="sw" style="background:${c}"></span>`).join("")}</div>
      <div class="eti">${["", "3", "3.5", "4", "4.5", "5"].map((t) => `<span>${t}</span>`).join("")}</div>
      <div class="estado"><span><i style="background:#946A1C"></i>Conocido</span><span><i class="sur"></i>Estimado</span></div>`,
  },
  grupo: {
    estilo: (p) => ({ fillColor: GRUPOS[p.grupo], fillOpacity: p.oculta ? 0.45 : 0.9 }),
    ley: () => `<div class="lt">Grupo regional</div>${Object.entries(GRUPOS).map(([g, c]) => `<div class="li"><i style="background:${c}"></i>${g.replace("_", " ")}</div>`).join("")}`,
  },
  anom: {
    estilo: (p) => ({ fillColor: lluvia(p.anom), fillOpacity: 0.92 }),
    ley: () => `<div class="lt">Lluvia de octubre 2025 frente a 2022–2024</div><div class="grad" style="background:linear-gradient(90deg,${d3.range(0, 1.01, 0.25).map((t) => lluvia(t * 125)).join(",")})"></div><div class="eti2"><span>0 %</span><span>+60 %</span><span>+125 %</span></div>`,
  },
  error: {
    estilo: (p) => (p.oculta ? { fillColor: "#ffffff", fillOpacity: 0.15 } : { fillColor: error(Math.abs(p.oof - p.obs)), fillOpacity: 0.92 }),
    ley: () => `<div class="lt">Error cuando la ocultamos (t/ha)</div><div class="grad" style="background:linear-gradient(90deg,${[0, 0.3, 0.6, 1].map(error).join(",")})"></div><div class="eti2"><span>0</span><span>0.5</span><span>1+ t/ha</span></div><div class="estado"><span><i style="background:#fff;opacity:.5"></i>Estimada (sin real)</span></div>`,
  },
  est: {
    estilo: (p) => (p.oculta ? { fillColor: `url(#L-s${clase(p.pred)})`, fillOpacity: 1, color: p.sin_k1 ? "#B2412C" : "#fff", weight: p.sin_k1 ? 2.6 : 1.2 } : { fillOpacity: 0.12, fillColor: "#fff" }),
    ley: () => `<div class="lt">Las 59 estimadas</div><div class="fil">${RAMPA.map((c) => `<span class="sw" style="background:repeating-linear-gradient(45deg,${c} 0 3px,#fff 3px 6px)"></span>`).join("")}</div>
      <div class="eti">${["", "3", "3.5", "4", "4.5", "5"].map((t) => `<span>${t}</span>`).join("")}</div><div class="estado"><span><i style="border:2px solid #B2412C;background:none"></i>Sin vecinas para comparar verdor</span></div>`,
  },
};

export function mapaSatelite() {
  const cont = document.getElementById("mapa-sat");
  const map = L.map(cont, { zoomControl: false, scrollWheelZoom: false, attributionControl: true, zoomSnap: 0.25 })
    .fitBounds(L.latLngBounds(D.P.map((p) => [p.lat, p.lon])), { padding: [30, 30] });
  L.tileLayer(ESRI, { maxZoom: 18, attribution: "Esri World Imagery" }).addTo(map);
  cont.classList.add("vista-azul");

  /* polígonos y símbolos (los símbolos se ven al alejar, como en el mapa original) */
  const rings = new Map(D.P.map((p) => [p.id, p.poly.map((r) => r.map(([x, y]) => utm2ll(x, y)))]));
  const centro = (p) => [p.lat, p.lon];
  const capa = L.layerGroup().addTo(map), simb = L.layerGroup().addTo(map);
  const poli = new Map(), sim = new Map();
  for (const p of D.P) {
    const pl = L.polygon(rings.get(p.id), { color: TINTA, weight: 0.8, className: "parcela-sat" }).addTo(capa);
    const cm = L.circleMarker(centro(p), { radius: 5, color: TINTA, weight: 0.8 }).addTo(simb);
    for (const l of [pl, cm]) {
      l.on("click", (e) => { L.DomEvent.stop(e); seleccionar(p.id, "mapa"); });
      l.on("mouseover mousemove", (e) => mostrarTip(htmlParcela(p), e.originalEvent));
      l.on("mouseout", ocultarTip);
    }
    poli.set(p.id, pl); sim.set(p.id, cm);
  }
  /* surcos en el SVG de Leaflet: los mismos patrones del sitio, prefijo L */
  const svgL = map.getRenderer(poli.values().next().value)._container;
  surcos(d3.select(svgL).insert("defs", ":first-child"), "L", 7, "rgba(255,255,255,.85)");

  const todo = L.latLngBounds([...poli.values()].map((l) => l.getBounds()));
  map.fitBounds(todo, { padding: [30, 30] });

  /* rótulos de municipio */
  const rot = L.layerGroup().addTo(map);
  for (const [m, ps] of D.MUNICIPIOS) {
    if (ps.length < 9) continue;
    L.marker([d3.max(ps, (p) => p.lat) + 0.006, d3.mean(ps, (p) => p.lon)], {
      interactive: false, icon: L.divIcon({ className: "rot-mun", html: `<span>${corto(m)}</span>` }),
    }).addTo(rot);
  }

  /* estado del mapa */
  let modo = "rend", filtro = "todas";
  const aux = L.layerGroup().addTo(map);
  const visible = (p) => filtro === "todas" || (filtro === "est") === p.oculta;
  function pintar() {
    const lejos = map.getZoom() < 13;
    for (const p of D.P) {
      const sel = p.id === estado.seleccion, v = visible(p);
      const base = { color: TINTA, weight: 0.8, opacity: 1, ...MODOS[modo].estilo(p) };
      if (!v) { base.opacity = 0.1; base.fillOpacity = 0.06; }
      if (sel) Object.assign(base, { color: "#fff", weight: 3, opacity: 1 });
      poli.get(p.id).setStyle({ ...base, opacity: lejos ? 0 : base.opacity, fillOpacity: lejos ? 0 : base.fillOpacity });
      const fc = String(base.fillColor).startsWith("url") ? colorV(p.pred) : base.fillColor;
      sim.get(p.id).setStyle({
        radius: sel ? 8 : 5, color: sel ? "#fff" : base.color === "#fff" ? "#fff" : TINTA, weight: sel ? 2.5 : base.weight,
        fillColor: fc, fillOpacity: lejos ? (p.oculta && modo === "rend" ? 0.35 : base.fillOpacity) : 0,
        opacity: lejos ? base.opacity : 0, dashArray: p.oculta && modo === "rend" ? "2 2" : null,
      });
    }
    document.getElementById("mapa-ley").innerHTML = MODOS[modo].ley();
    poli.get(estado.seleccion)?.bringToFront();
  }
  map.on("zoomend", pintar);

  /* marco de selección: cuatro esquinas que se cierran sobre la parcela elegida */
  const ret = document.createElement("div");
  ret.className = "reticula";
  ret.innerHTML = "<i></i><i></i><i></i><i></i><span></span>";
  cont.appendChild(ret);
  const colocar = () => {
    if (!estado.seleccion) return;
    const b = poli.get(estado.seleccion).getBounds();
    const a = map.latLngToContainerPoint(b.getNorthWest()), z = map.latLngToContainerPoint(b.getSouthEast()), m = 14;
    Object.assign(ret.style, { left: `${a.x - m}px`, top: `${a.y - m}px`, width: `${z.x - a.x + 2 * m}px`, height: `${z.y - a.y + 2 * m}px` });
  };
  map.on("move zoom", colocar);

  /* anillo de 1 km y líneas a las vecinas, como en el verdor relativo (K) */
  function vecindad(p) {
    aux.clearLayers();
    const vs = vecinasDe(p);
    L.circle(centro(p), { radius: 1000, color: "#fff", weight: 1.4, dashArray: "5 6", fill: false, interactive: false }).addTo(aux);
    vs.forEach((q) => L.polyline([centro(p), centro(q)], { color: q.oculta ? "#E3C772" : "#fff", weight: 1.2, dashArray: "2 4", interactive: false }).addTo(aux));
    return vs;
  }

  /* ficha flotante de la parcela elegida */
  const ficha = document.getElementById("ficha-sat");
  function pintarFicha(p, vs) {
    const v = valor(p), x = d3.scaleLinear([2, 6], [0, 100]);
    const conocidas = vs.filter((q) => !q.oculta);
    const comp = p.oculta ? [["MUN", "Municipio", p.mun_p], ["MIX", "Referencia", p.mix], ["K", "Con verdor", p.kv], ["J", "Con lluvia", p.jv], ["E_JK", "Final", p.pred]] : [];
    const xb = d3.scaleLinear([2, 5.5], [0, 100]).clamp(true);
    ficha.innerHTML = `<div class="f-btns"><button class="minimizar" aria-label="Minimizar ficha" title="Minimizar">−</button><button class="cerrar" aria-label="Cerrar ficha" title="Cerrar">×</button></div>
      <div class="f-id">${p.id}</div><div class="f-sub">${p.mun}, ${p.edo} · ${f(p.ha)} ha</div>
      <div class="f-val"><b class="num">${f(v)}</b> t/ha <span>${p.oculta ? "estimadas" : "conocidas"}</span></div>
      <div class="f-cuerpo">
      ${p.oculta ? `<svg class="f-rango" viewBox="0 0 100 12" preserveAspectRatio="none"><rect x="${x(p.lo80)}" y="3" width="${x(p.hi80) - x(p.lo80)}" height="6" fill="url(#t-s${clase(p.pred)})"/><line x1="${x(p.mix)}" x2="${x(p.mix)}" y1="1" y2="11" stroke="#5B636B" stroke-width="1"/><line x1="${x(p.pred)}" x2="${x(p.pred)}" y1="0" y2="12" stroke="${TINTA}" stroke-width="1.6"/></svg>
        <div class="f-nota">80 %: ${f(p.lo80)} a ${f(p.hi80)} · frente a la referencia ${fs(p.pred - p.mix)}</div>
        <div class="f-comp">${comp.map(([k, nom, val]) => `<div title="${k}"><span>${nom}</span><em><i style="width:${xb(val)}%;background:${COLORES[k]}"></i></em><b>${f(val)}</b></div>`).join("")}</div>`
      : `<div class="f-nota">Al ocultarla, el modelo estimó ${f(p.oof)} t/ha (error ${fs(p.oof - p.obs)}).</div>`}
      <div class="f-sec">Lluvia de octubre: <b>${fs(p.anom, 0)} %</b> frente a 2022–2024</div>
      <div class="f-sec">${vs.length ? `${vs.length} vecinas a menos de 1 km${conocidas.length ? `, ${conocidas.length} conocidas con media ${f(d3.mean(conocidas, (q) => q.obs))} t/ha` : ""}` : "Sin vecinas a menos de 1 km"}</div>
      ${vs.length ? `<div class="f-chips">${vs.slice(0, 12).map((q) => `<button data-id="${q.id}" class="${q.oculta ? "e" : ""}">${q.id.slice(4)} · ${f(valor(q), 1)}</button>`).join("")}</div>` : ""}
      ${p.sin_k1 ? `<div class="f-aviso">Sin vecinas suficientes para comparar su verdor: se usa solo la referencia territorial.</div>` : ""}
      <a class="f-mas" href="#estimaciones">Ver ficha completa en la tabla</a></div>`;
    ficha.hidden = false;
    ficha.querySelector(".cerrar").onclick = () => { ficha.hidden = true; };
    ficha.querySelector(".minimizar").onclick = (e) => {
      const mini = ficha.classList.toggle("mini");
      e.currentTarget.textContent = mini ? "+" : "−";
      e.currentTarget.setAttribute("aria-label", mini ? "Abrir ficha" : "Minimizar ficha");
    };
    ficha.querySelectorAll(".f-chips button").forEach((b) => (b.onclick = () => seleccionar(b.dataset.id, "mapa")));
  }

  const pista = document.getElementById("mapa-pista");
  function marcar(id, origen) {
    const p = D.porId.get(id);
    if (origen !== "inicio") pista?.classList.add("oculta");
    if (!p) return;
    const vs = vecindad(p);
    pintar();
    if (origen !== "inicio") {
      const ancho = cont.clientWidth > 560;
      map.flyToBounds(poli.get(id).getBounds(), { paddingTopLeft: ancho ? [300, 120] : [40, 120], paddingBottomRight: ancho ? [70, 70] : [40, 260], maxZoom: 15.5, duration: 1.1 });
      map.once("moveend", () => { colocar(); ret.classList.remove("on"); void ret.offsetWidth; ret.classList.add("on"); });
      pintarFicha(p, vs);
    }
    ret.querySelector("span").textContent = id;
  }
  alSeleccionar(marcar);

  /* herramientas: filtros, zoom, vista, Ctrl + rueda */
  document.querySelectorAll(".mapa-herr button").forEach((b) => b.addEventListener("click", () => {
    filtro = b.dataset.f;
    document.querySelectorAll(".mapa-herr button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    pintar();
  }));
  document.querySelectorAll(".mapa-zoom button").forEach((b) => b.addEventListener("click", () => {
    const z = +b.dataset.z;
    if (z === 0) map.flyToBounds(todo, { padding: [30, 30], duration: 0.8 });
    else map.setZoom(map.getZoom() + z);
  }));
  document.querySelectorAll(".mapa-vista button").forEach((b) => b.addEventListener("click", () => {
    cont.classList.toggle("vista-azul", b.dataset.v === "azul");
    document.querySelectorAll(".mapa-vista button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  }));
  cont.addEventListener("wheel", (ev) => {
    if (!(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    map.setZoomAround(map.mouseEventToContainerPoint(ev), map.getZoom() + (ev.deltaY < 0 ? 0.5 : -0.5));
  }, { passive: false });

  addEventListener("keydown", (e) => { if (e.key === "Escape" && !ficha.hidden) ficha.hidden = true; });
  pintar();
  marcar(estado.seleccion, "inicio");

  /* lo que usa el recorrido */
  return {
    modo: (m) => { modo = m; pintar(); },
    verTodo: () => map.flyToBounds(todo, { padding: [30, 30], duration: 1.1 }),
    verMunicipio: (m) => map.flyToBounds(L.latLngBounds(D.P.filter((p) => p.mun === m).map(centro)), { padding: [40, 40], duration: 1.1 }),
    texto: { varianza: pct(D.EV.varianza_municipio), pendiente: f(D.M.J.pendiente, 4) },
  };
}
