// Arranque: navegación, carga verificada de datos y cada sección.
import { fijarDatos, seleccionar, estado } from "./comun.js";
import { cargarDatos } from "./datos.js";
import { iniciarNavegacion } from "./navegacion.js";
import { iniciarPortada } from "./portada.js";
import { iniciarTablero } from "./tablero.js";
import { iniciarEstimaciones, defsGlobales } from "./estimaciones.js";
import { iniciarDescargas } from "./descargas.js";
import { iniciarEjecutar } from "./ejecutar.js";
import { iniciarMetodo } from "./metodo.js";
import { iniciarUso } from "./uso.js";
import { iniciarPreguntas } from "./preguntas.js";
import { iniciarPie } from "./pie.js";

export async function iniciar() {
  const nav = iniciarNavegacion();
  let D;
  try {
    D = await cargarDatos();
  } catch (e) {
    const aviso = document.getElementById("aviso-datos");
    aviso.textContent = `No se pudieron cargar los datos verificados (${e.message}). Recarga la página; si persiste, los archivos publicados no coinciden con su manifiesto.`;
    aviso.hidden = false;
    nav.estadoDatos("Los datos no se pudieron verificar.");
    console.error(e);
    return;
  }
  fijarDatos(D);
  estado.seleccion = D.VIT.id;
  defsGlobales();
  iniciarPortada();
  iniciarTablero();
  let ejecutar = null;
  iniciarEstimaciones((id) => ejecutar?.cargar(id));
  iniciarDescargas();
  ejecutar = iniciarEjecutar();
  iniciarUso();
  iniciarPreguntas();
  iniciarPie(nav.estadoDatos);
  await iniciarMetodo();
  seleccionar(estado.seleccion, "inicio");
  // las secciones crecen al dibujarse: si se abrió con #seccion, se vuelve a llevar ahí
  const ancla = location.hash && document.querySelector(location.hash);
  if (ancla) [60, 600].forEach((t) => setTimeout(() => ancla.scrollIntoView({ behavior: "instant", block: "start" }), t));
}
