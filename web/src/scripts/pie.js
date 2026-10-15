// Pie: manifiesto de archivos con la comprobación hecha en este navegador.
import { D, NUBE } from "./comun.js";
import { verificarArchivo } from "./datos.js";

export function iniciarPie(estadoDatos) {
  const M = D.MAN, filas = Object.entries(M.archivos);
  const fecha = M.fecha_commit ? new Date(M.fecha_commit).toLocaleString("es-MX", { dateStyle: "long", timeStyle: "short" }) : null;
  document.getElementById("pie-gen").textContent = `Datos exportados desde el commit ${M.commit || "—"}${fecha ? ` (${fecha})` : ""} del repositorio. Las tres tablas de descarga son copias exactas de resultados/04_seleccion_modelo_final.`;
  const tbody = document.querySelector("#manif tbody");
  tbody.innerHTML = filas.map(([n, m]) => `<tr data-r="${n}"><td><a href="/${n}">${n.split("/")[1]}</a></td><td><code>${m.sha256}</code><br><span>${m.bytes.toLocaleString("es-MX")} bytes</span></td><td class="v">pendiente</td></tr>`).join("");
  const marcar = (ruta, ok) => {
    const td = tbody.querySelector(`tr[data-r="${ruta}"] .v`);
    if (!td) return;
    td.className = ok === null ? "v" : ok ? "v ok" : "v mal";
    td.textContent = ok === null ? "sin cálculo" : ok ? "coincide" : "no coincide";
  };
  Object.entries(D.verificacion).forEach(([r, ok]) => marcar(r, ok));
  const resumen = () => {
    const vals = [...tbody.querySelectorAll(".v")].map((td) => td.textContent);
    const ok = vals.filter((v) => v === "coincide").length;
    return `<b>${ok} de ${vals.length}</b> archivos de datos verificados con SHA-256 en este navegador.`;
  };
  estadoDatos(resumen());
  // las descargas se comprueban cuando el pie se acerca a la vista
  let hecho = false;
  new IntersectionObserver(async (es) => {
    if (hecho || !es.some((e) => e.isIntersecting)) return;
    hecho = true;
    for (const [ruta] of filas.filter(([r]) => !(r in D.verificacion))) {
      try { marcar(ruta, (await verificarArchivo(ruta, M)).ok); } catch { marcar(ruta, false); }
    }
    estadoDatos(resumen() + (await NUBE ? "<br>Modelo en AWS Lambda: activo." : ""));
  }, { rootMargin: "300px 0px" }).observe(document.getElementById("datos"));
  NUBE.then((s) => {
    document.getElementById("pie-nube").textContent = s
      ? `Sitio en Amazon S3 y CloudFront; reentrenamiento en AWS Lambda (${s.region}), Python ${s.python}, numpy ${s.numpy}, pandas ${s.pandas}, commit ${s.commit}.`
      : "Sitio estático; la función de reentrenamiento no respondió desde este navegador.";
    estadoDatos(resumen() + (s ? "<br>Modelo en AWS Lambda: activo." : ""));
  });
}
