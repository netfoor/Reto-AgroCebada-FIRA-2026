// Encabezado: nombre de la sección actual, lista de secciones y riel de avance.
export function iniciarNavegacion() {
  const boton = document.getElementById("ubic-boton");
  const lista = document.getElementById("ubic-lista");
  const nombre = document.getElementById("ubic-nombre");
  const pos = document.getElementById("ubic-pos");
  const enlaces = [...lista.querySelectorAll("a[data-sec]")];
  const ids = enlaces.map((a) => a.dataset.sec);
  const secciones = ids.map((id) => document.getElementById(id));
  const marcas = new Map([...document.querySelectorAll(".riel-marca")].map((m) => [m.dataset.sec, m]));
  const encabezado = document.querySelector(".encabezado");
  let actual = 0;

  /* abrir y cerrar la lista */
  const abrir = (si) => {
    boton.setAttribute("aria-expanded", String(si));
    lista.hidden = !si;
  };
  boton.addEventListener("click", () => abrir(lista.hidden));
  document.addEventListener("click", (e) => { if (!lista.hidden && !e.target.closest(".ubicacion")) abrir(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !lista.hidden) { abrir(false); boton.focus(); } });
  enlaces.forEach((a) => a.addEventListener("click", () => abrir(false)));

  /* sección actual: la que cruza la franja de lectura */
  const marcar = (i) => {
    actual = i;
    nombre.textContent = enlaces[i].textContent;
    pos.textContent = `${i + 1} de ${ids.length}`;
    enlaces.forEach((a, j) => {
      a.setAttribute("aria-current", String(j === i));
      a.classList.toggle("pasada", j < i);
    });
    ids.forEach((id, j) => marcas.get(id)?.classList.toggle("pasada", j <= i));
  };
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) marcar(secciones.indexOf(e.target));
  }), { rootMargin: "-40% 0px -55% 0px" });
  secciones.forEach((s) => s && io.observe(s));
  marcar(0);

  /* riel: avance de la página y una marca donde empieza cada sección */
  let maximo = 1;
  const medir = () => {
    maximo = Math.max(1, document.documentElement.scrollHeight - innerHeight);
    const enc = encabezado.offsetHeight;
    ids.forEach((id, j) => {
      const m = marcas.get(id);
      if (!m) return;
      const y = secciones[j].getBoundingClientRect().top + scrollY - enc;
      m.style.left = `${Math.min(100, Math.max(0, (y / maximo) * 100))}%`;
    });
    avanzar();
  };
  let pendiente = false;
  const avanzar = () => {
    pendiente = false;
    encabezado.style.setProperty("--avance", Math.min(1, Math.max(0, scrollY / maximo)).toFixed(4));
  };
  addEventListener("scroll", () => { if (!pendiente) { pendiente = true; requestAnimationFrame(avanzar); } }, { passive: true });
  new ResizeObserver(medir).observe(document.body);
  medir();
  return { estadoDatos: (html) => { document.getElementById("ubic-pie").innerHTML = html; }, actual: () => actual };
}
