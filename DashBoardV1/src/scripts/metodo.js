// «Cómo se hizo»: pasos con figura fija (escritorio) o figura en línea (teléfono).
// Las capas, las vecinas y la curva de verdor avanzan con el scroll y se deshacen al regresar.
import * as d3 from "d3";
import { animate, onScroll, stagger, svg as asvg } from "animejs";
import { D, QUIETO, NUBE, f, fs, pct, modeloFinal } from "./comun.js";
import { escenas, CAPAS_FIN } from "./escenas.js";

/** Observadores de scroll activos: se vuelven a medir si cambia el alto de la página. */
const observadores = new Set();

const FASES = ["Entender el problema", "Entender los datos", "Preparar los datos", "Modelar", "Evaluar", "Publicar"];
const mqMovil = matchMedia("(max-width: 1080px)");

function textos() {
  const V = D.VIT, EV = D.EV, p = D.porId.get(V.id), r = modeloFinal(p);
  const pon = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
  pon("txt-dist", `${f(EV.distancia_mediana_oculta_conocida_m, 0)} m`);
  pon("txt-planet", `${f(EV.planet.imagenes_mediana_por_parcela, 0)} imágenes Planet por parcela (mediana)`);
  pon("txt-celda", `${f(Math.round(V.celda_ha / 100) * 100, 0)} ha`);
  pon("txt-ha", `${f(p.ha)} ha`);
  pon("txt-global", f(EV.escalera.GLOBAL));
  pon("txt-mun", `${f(EV.escalera.MUN)} t/ha`);
  pon("txt-var", pct(EV.varianza_municipio));
  const caja = EV.evaluaciones[4].rmse;
  pon("txt-caja", `${f(caja.MIX - caja.E_JK, 3)} t/ha`);
  pon("txt-banda", `${f(EV.banda_59[0])} y ${f(EV.banda_59[1])}`);
  pon("txt-cerca", `${f(EV.semivariograma[0].diferencia)} t/ha`);
  pon("txt-vecinas", `Para ${V.id}: media de ${p.mun} <span class="dato">${f(r.MUN)}</span>, vecinas <span class="dato">${f(r.IDW)}</span>, MIX <span class="dato">${f(r.MIX)}</span> t/ha.`);
  pon("txt-verdor", `${V.id} acumuló <span class="dato">${f(V.integral, 1)}</span> y sus ${V.vecinas_1km.length} parcelas cercanas, en mediana, <span class="dato">${f(V.mediana_vecinas, 1)}</span>: un contraste de ${fs(V.k1)}. Tener un NDVI más alto que las cercanas se asoció con un poco menos de grano, así que K baja ${f(Math.abs(r.K - r.MIX), 3)} t/ha.`);
  pon("txt-lluvia", `En octubre de 2025 llovió <span class="dato">${f(Math.abs(V.anom), 1)} % ${V.anom >= 0 ? "más" : "menos"}</span> que el promedio en ${V.id}. La celda explica el 99 % o más de la variación de esta variable, así que funciona como una ubicación más fina y no prueba un efecto de la lluvia.`);
}

export async function iniciarMetodo() {
  textos();
  const salud = await Promise.race([NUBE, new Promise((r) => setTimeout(() => r(null), 2500))]);
  const ESC = escenas(salud);
  const pasos = [...document.querySelectorAll(".paso")];
  const figuras = new Map(pasos.map((p) => [p.dataset.esc, p.querySelector(".figura")]));
  const marco = document.getElementById("escenario-marco");
  const hechas = new Map(); // nombre → { limpiar() }
  let modo = null, activo = null;

  /* sincronía con el scroll (anime.js onScroll) */
  function sincronizar(nombre, partes, fig, paso) {
    if (QUIETO || !partes) {
      partes?.colocar?.(CAPAS_FIN, true);
      return () => {};
    }
    const movil = modo === "movil";
    const objetivo = movil ? fig : paso;
    const umbral = movil ? { enter: "90% top", leave: "35% top" } : { enter: "center top", leave: "center center" };
    const piezas = [];
    if (partes.colocar) {
      // escritorio: separadas el primer 12 % del paso, se juntan hasta el 70 % y se quedan juntas.
      // teléfono: la figura queda fija mientras pasa el relleno de debajo.
      const relleno = paso.querySelector(".relleno-scroll");
      const enc = () => document.querySelector(".encabezado").offsetHeight + 8 + fig.offsetHeight;
      const obs = movil
        ? onScroll({ target: relleno, enter: () => ({ container: enc(), target: "top" }), leave: () => ({ container: enc(), target: "bottom" }), sync: 0.6 })
        : onScroll({ target: paso, enter: "center top", leave: "center bottom", sync: 0.6 });
      const est = { p: 0 };
      const [a, b] = movil ? [0.08, 0.85] : [0.12, 0.7];
      piezas.push(animate(est, {
        p: [0, 1], ease: "linear", duration: 1000, autoplay: obs,
        onUpdate: () => {
          const u = Math.max(0, Math.min(1, (est.p - a) / (b - a)));
          partes.colocar(1 - (1 - CAPAS_FIN) * u);
        },
      }), obs);
    }
    if (partes.lineas) {
      const obs = onScroll({ target: objetivo, ...umbral, sync: 0.6 });
      piezas.push(animate(asvg.createDrawable(partes.lineas), { draw: ["0 0", "0 1"], ease: "outQuad", duration: 600, delay: stagger(40, { from: "random" }), autoplay: obs }), obs);
    }
    if (partes.curva) {
      const obs = onScroll({ target: objetivo, ...umbral, sync: 0.6 });
      piezas.push(animate(asvg.createDrawable(partes.curva), { draw: ["0 0", "0 1"], ease: "inOutSine", duration: 1000, autoplay: obs }), obs);
      const obs2 = onScroll({ target: objetivo, ...umbral, sync: 0.6 });
      piezas.push(animate(partes.area, { opacity: [0, 0, 1], ease: "linear", duration: 1000, autoplay: obs2 }), obs2);
    }
    piezas.filter((x) => typeof x.refresh === "function").forEach((o) => observadores.add(o));
    return () => piezas.forEach((x) => { observadores.delete(x); x.revert(); });
  }

  function construir(nombre) {
    if (hechas.has(nombre)) return;
    const fig = figuras.get(nombre), paso = fig.closest(".paso") ?? pasos.find((p) => p.dataset.esc === nombre);
    const e = ESC[nombre];
    const movil = modo === "movil";
    const W = movil ? 400 : 800, H = movil ? e.alto : 600;
    const svg = d3.select(fig.querySelector("svg")).html("").attr("viewBox", `0 0 ${W} ${H}`);
    const partes = e.fn(svg.append("g"), W, H, movil);
    fig.querySelector("figcaption").textContent = e.pie;
    hechas.set(nombre, { limpiar: sincronizar(nombre, partes, fig, paso) });
  }

  function acomodar() {
    const nuevo = mqMovil.matches ? "movil" : "escritorio";
    if (nuevo === modo) return;
    modo = nuevo;
    hechas.forEach((h) => h.limpiar());
    hechas.clear();
    pasos.forEach((p) => {
      const fig = figuras.get(p.dataset.esc);
      if (modo === "escritorio") marco.appendChild(fig);
      else p.insertBefore(fig, p.querySelector(".relleno-scroll"));
      fig.classList.remove("activa");
    });
    if (modo === "escritorio") {
      // todas en el escenario fijo: se dibujan ya para que el cambio de paso sea inmediato
      pasos.forEach((p) => construir(p.dataset.esc));
      if (activo) figuras.get(activo)?.classList.add("activa");
    }
  }

  /* en teléfono, cada figura se dibuja al acercarse */
  const cerca = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting && modo === "movil") construir(e.target.dataset.esc);
  }), { rootMargin: "120% 0px" });
  figuras.forEach((fig) => cerca.observe(fig));

  /* paso activo e indicador de etapa */
  const seg = [...document.querySelectorAll("#etapa-seg button")];
  const irA = (paso) => paso?.scrollIntoView({ behavior: QUIETO ? "auto" : "smooth", block: "center" });
  seg.forEach((b) => b.addEventListener("click", () => irA(pasos.find((p) => p.dataset.fase === b.dataset.fase))));
  // clics seguidos mientras la página aún se desliza: se cuenta desde el paso pedido, no desde el visible
  let pedido = null, reloj = null;
  const indice = () => pedido ?? pasos.findIndex((p) => p.dataset.esc === activo);
  const saltar = (d) => {
    pedido = Math.max(0, Math.min(pasos.length - 1, indice() + d));
    clearTimeout(reloj); reloj = setTimeout(() => { pedido = null; }, 1200);
    irA(pasos[pedido]);
  };
  document.getElementById("etapa-ant").addEventListener("click", () => saltar(-1));
  document.getElementById("etapa-sig").addEventListener("click", () => saltar(1));
  document.getElementById("etapa-t").textContent = pasos.length;
  const etapa = document.getElementById("etapa");
  const activar = (paso) => {
    activo = paso.dataset.esc;
    pasos.forEach((x) => x.classList.toggle("activo", x === paso));
    if (modo === "escritorio") {
      construir(activo);
      figuras.forEach((fig, n) => fig.classList.toggle("activa", n === activo));
    }
    const fz = +paso.dataset.fase;
    seg.forEach((s, i) => { s.className = i < fz ? "hecho" : i === fz ? "actual" : ""; s.setAttribute("aria-current", String(i === fz)); });
    document.getElementById("etapa-p").textContent = pasos.indexOf(paso) + 1;
    document.getElementById("etapa-ant").disabled = pasos.indexOf(paso) === 0;
    document.getElementById("etapa-sig").disabled = pasos.indexOf(paso) === pasos.length - 1;
    document.getElementById("etapa-nom").textContent = FASES[fz];
    document.getElementById("etapa-n").textContent = fz + 1;
  };
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) activar(e.target); }),
    { rootMargin: "-48% 0px -48% 0px" });
  pasos.forEach((p) => io.observe(p));
  new IntersectionObserver((es) => es.forEach((e) => etapa.classList.toggle("visible", e.isIntersecting)),
    { rootMargin: "-35% 0px -35% 0px" }).observe(document.getElementById("pasos"));

  // indicador de etapa: bajo la figura en escritorio, fijo abajo a la izquierda en teléfono
  const escenario = document.getElementById("escenario"), seccion = document.getElementById("metodo");
  const moverEtapa = () => (modo === "escritorio" ? escenario.appendChild(etapa) : seccion.appendChild(etapa));
  mqMovil.addEventListener("change", () => { acomodar(); moverEtapa(); });
  let espera = null;
  new ResizeObserver(() => {
    clearTimeout(espera);
    espera = setTimeout(() => observadores.forEach((o) => o.refresh()), 150);
  }).observe(document.body);
  acomodar();
  moverEtapa();
  if (!activo) activar(pasos[0]);
}
