// Recorrido del tablero: cada tarjeta que cruza el centro de la pantalla cambia la capa del mapa satelital.
import { D, seleccionar } from "./comun.js";

export function iniciarRecorrido(mapa) {
  const pasos = [...document.querySelectorAll(".rec-paso")];
  if (!pasos.length) return;
  const vitrina = D.VIT.id;
  const acciones = {
    todo: () => { mapa.modo("rend"); mapa.verTodo(); },
    grupo: () => { mapa.modo("grupo"); mapa.verTodo(); },
    lluvia: () => { mapa.modo("anom"); mapa.verTodo(); },
    vecinas: () => { mapa.modo("rend"); seleccionar(vitrina, "recorrido"); },
    error: () => { mapa.modo("error"); mapa.verMunicipio("Chignahuapan"); },
    estimadas: () => { mapa.modo("est"); mapa.verTodo(); },
    libre: () => { mapa.modo("rend"); },
  };
  const V = D.VIT, txt = document.getElementById("txt-vit");
  if (txt) txt.innerHTML = `${V.id} y sus ${Array.isArray(V.vecinas_1km) ? V.vecinas_1km.length : V.vecinas_1km} vecinas a menos de 1 km (el anillo). Estuvo un poco más verde que ellas y eso se asoció con algo menos de grano, así que su referencia bajó de <span class="dato">${V.mix.toFixed(2)}</span> a <span class="dato">${V.k.toFixed(2)}</span> t/ha.`;
  document.querySelectorAll("[data-txt]").forEach((el) => { el.textContent = mapa.texto[el.dataset.txt] ?? el.textContent; });
  let actual = null;
  const botones = [...document.querySelectorAll("#rec-botones button")];
  const flechas = [...document.querySelectorAll(".rec-flecha")];
  const escritorio = matchMedia("(min-width: 1081px)");
  const activar = (paso) => {
    if (paso === actual) return;
    actual = paso;
    const i = pasos.indexOf(paso);
    pasos.forEach((p) => p.classList.toggle("activo", p === paso));
    botones.forEach((b, j) => { b.setAttribute("aria-current", String(j === i)); b.classList.toggle("hecho", j < i); });
    botones[i]?.scrollIntoView({ block: "nearest", inline: "nearest" });
    flechas[0].disabled = i <= 0;
    flechas[1].disabled = i >= pasos.length - 1;
    acciones[paso.dataset.accion]?.();
  };
  /* con scroll: la tarjeta que cruza el centro de la pantalla */
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) activar(e.target); }), { rootMargin: "-45% 0px -45% 0px" });
  pasos.forEach((p) => io.observe(p));
  /* con clic: en escritorio se lleva la tarjeta al centro; en teléfono el mapa cambia sin mover la página */
  let pedido = null, reloj = null;
  const ir = (i) => {
    pedido = Math.max(0, Math.min(pasos.length - 1, i));
    clearTimeout(reloj); reloj = setTimeout(() => { pedido = null; }, 1200);
    const paso = pasos[pedido];
    if (escritorio.matches) paso.scrollIntoView({ behavior: "smooth", block: "center" });
    else activar(paso);
  };
  botones.forEach((b) => b.addEventListener("click", () => ir(+b.dataset.i)));
  flechas.forEach((b) => b.addEventListener("click", () => ir((pedido ?? pasos.indexOf(actual)) + +b.dataset.d)));
  flechas[0].disabled = true;
}
