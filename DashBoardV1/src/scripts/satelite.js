// Imagen satelital para las figuras en SVG: convierte entre UTM 14N y grados y dibuja las teselas de Esri
// debajo de cualquier proyección de d3, con el mismo tinte azul del mapa del tablero.
import * as d3 from "d3";
const A = 6378137, FL = 1 / 298.257223563, K0 = 0.9996, E2 = FL * (2 - FL), EP2 = E2 / (1 - E2), RAD = Math.PI / 180;
export const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

/** UTM 14N (metros) a [lat, lon]. */
export function utm2ll(E, N, zona = 14) {
  const x = E - 5e5, M = N / K0;
  const mu = M / (A * (1 - E2 / 4 - (3 * E2 * E2) / 64 - (5 * E2 ** 3) / 256));
  const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
  const p1 = mu + ((3 * e1) / 2 - (27 * e1 ** 3) / 32) * Math.sin(2 * mu) + ((21 * e1 * e1) / 16 - (55 * e1 ** 4) / 32) * Math.sin(4 * mu)
    + ((151 * e1 ** 3) / 96) * Math.sin(6 * mu) + ((1097 * e1 ** 4) / 512) * Math.sin(8 * mu);
  const s = Math.sin(p1), c = Math.cos(p1), C1 = EP2 * c * c, T1 = Math.tan(p1) ** 2;
  const N1 = A / Math.sqrt(1 - E2 * s * s), R1 = (A * (1 - E2)) / (1 - E2 * s * s) ** 1.5, D = x / (N1 * K0);
  const lat = p1 - ((N1 * Math.tan(p1)) / R1) * ((D * D) / 2 - ((5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * EP2) * D ** 4) / 24
    + ((61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * EP2 - 3 * C1 * C1) * D ** 6) / 720);
  const lon = ((zona - 1) * 6 - 177) * RAD
    + (D - ((1 + 2 * T1 + C1) * D ** 3) / 6 + ((5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * EP2 + 24 * T1 * T1) * D ** 5) / 120) / c;
  return [lat / RAD, lon / RAD];
}

/** [lat, lon] a UTM 14N [x, y] en metros. */
export function ll2utm(lat, lon, zona = 14) {
  const f = lat * RAD, s = Math.sin(f), c = Math.cos(f), t = Math.tan(f);
  const N = A / Math.sqrt(1 - E2 * s * s), T = t * t, C = EP2 * c * c, Aa = c * (lon - ((zona - 1) * 6 - 177)) * RAD;
  const M = A * ((1 - E2 / 4 - (3 * E2 ** 2) / 64 - (5 * E2 ** 3) / 256) * f - ((3 * E2) / 8 + (3 * E2 ** 2) / 32 + (45 * E2 ** 3) / 1024) * Math.sin(2 * f)
    + ((15 * E2 ** 2) / 256 + (45 * E2 ** 3) / 1024) * Math.sin(4 * f) - ((35 * E2 ** 3) / 3072) * Math.sin(6 * f));
  const x = K0 * N * (Aa + ((1 - T + C) * Aa ** 3) / 6 + ((5 - 18 * T + T * T + 72 * C - 58 * EP2) * Aa ** 5) / 120) + 5e5;
  const y = K0 * (M + N * t * ((Aa * Aa) / 2 + ((5 - T + 9 * C + 4 * C * C) * Aa ** 4) / 24 + ((61 - 58 * T + T * T + 600 * C - 330 * EP2) * Aa ** 6) / 720));
  return [x, y];
}

const tx = (lon, z) => ((lon + 180) / 360) * 2 ** z;
const ty = (lat, z) => ((1 - Math.log(Math.tan(lat * RAD) + 1 / Math.cos(lat * RAD)) / Math.PI) / 2) * 2 ** z;
const tlon = (x, z) => (x / 2 ** z) * 360 - 180;
const tlat = (y, z) => Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / 2 ** z))) / RAD;

let nTinte = 0;
const MATRIZ = [[0.19, 0.37, 0.07, 0.03], [0.21, 0.41, 0.08, 0.06], [0.23, 0.46, 0.09, 0.12]];
const cache = new Map();
/** Descarga una tesela como ImageBitmap (Esri permite CORS). */
const tesela = (url) => {
  if (!cache.has(url)) cache.set(url, fetch(url).then((r) => (r.ok ? r.blob() : Promise.reject(r.status))).then((b) => createImageBitmap(b)));
  return cache.get(url);
};

/**
 * Dibuja la imagen satelital en `g` (un grupo de d3) para la caja UTM [x0, y0, x1, y1].
 * `aPunto(x, y)` lleva metros UTM a unidades del lienzo; `pixeles` es el ancho aproximado en pantalla de esa caja.
 * Las teselas se juntan y se tiñen una sola vez en un canvas, y el SVG recibe una sola imagen ligera.
 * Si el navegador no puede (sin CORS o sin canvas), usa las teselas sueltas con un filtro SVG.
 */
export function fondoSatelital(g, aPunto, [x0, y0, x1, y1], { pixeles = 800, nitidez = 1.6, max = 90, tinte = true, opacidad = 1 } = {}) {
  const sw = utm2ll(x0, y0), ne = utm2ll(x1, y1), nw = utm2ll(x0, y1), se = utm2ll(x1, y0);
  const lat0 = Math.min(sw[0], se[0]), lat1 = Math.max(nw[0], ne[0]), lon0 = Math.min(sw[1], nw[1]), lon1 = Math.max(se[1], ne[1]);
  const mpp = (x1 - x0) / pixeles / nitidez;
  let z = Math.max(5, Math.min(17, Math.round(Math.log2((156543.03 * Math.cos(((lat0 + lat1) / 2) * RAD)) / mpp))));
  const rango = (zz) => [Math.floor(tx(lon0, zz)), Math.floor(tx(lon1, zz)), Math.floor(ty(lat1, zz)), Math.floor(ty(lat0, zz))];
  let [a, b, c, d] = rango(z);
  while ((b - a + 1) * (d - c + 1) > max && z > 5) { z--; [a, b, c, d] = rango(z); }
  const capa = g.append("g").attr("class", "sat-fondo").attr("opacity", opacidad);
  const piezas = [];
  for (let i = a; i <= b; i++) for (let j = c; j <= d; j++) {
    const [px0, py0] = aPunto(...ll2utm(tlat(j, z), tlon(i, z)));
    const [px1, py1] = aPunto(...ll2utm(tlat(j + 1, z), tlon(i + 1, z)));
    piezas.push({ url: ESRI.replace("{z}", z).replace("{y}", j).replace("{x}", i), x: Math.min(px0, px1), y: Math.min(py0, py1), w: Math.abs(px1 - px0), h: Math.abs(py1 - py0) });
  }
  const bx0 = d3.min(piezas, (p) => p.x), by0 = d3.min(piezas, (p) => p.y);
  const bw = d3.max(piezas, (p) => p.x + p.w) - bx0, bh = d3.max(piezas, (p) => p.y + p.h) - by0;
  const esc = Math.min(2, 2400 / Math.max(bw, bh));

  const sueltas = () => {
    if (tinte) {
      const id = `tinte-sat-${++nTinte}`, svg = g.node().ownerSVGElement;
      let defs = d3.select(svg).select("defs");
      if (defs.empty()) defs = d3.select(svg).insert("defs", ":first-child");
      defs.append("filter").attr("id", id).attr("color-interpolation-filters", "sRGB").append("feColorMatrix").attr("type", "matrix")
        .attr("values", MATRIZ.map((r) => `${r[0]} ${r[1]} ${r[2]} 0 ${r[3]}`).join(" ") + " 0 0 0 1 0");
      capa.attr("filter", `url(#${id})`);
    }
    piezas.forEach((p) => capa.append("image").attr("href", p.url).attr("x", p.x).attr("y", p.y)
      .attr("width", p.w + 1.6).attr("height", p.h + 1.6).attr("preserveAspectRatio", "none"));
  };

  if (typeof createImageBitmap !== "function") { sueltas(); return capa; }
  Promise.all(piezas.map((p) => tesela(p.url))).then((imgs) => {
    const cv = document.createElement("canvas");
    cv.width = Math.round(bw * esc); cv.height = Math.round(bh * esc);
    const ctx = cv.getContext("2d");
    imgs.forEach((im, k) => { const p = piezas[k]; ctx.drawImage(im, (p.x - bx0) * esc, (p.y - by0) * esc, p.w * esc + 1, p.h * esc + 1); });
    if (tinte) {
      const datos = ctx.getImageData(0, 0, cv.width, cv.height), px = datos.data;
      for (let k = 0; k < px.length; k += 4) {
        const r = px[k] / 255, gg = px[k + 1] / 255, bb = px[k + 2] / 255;
        px[k] = 255 * Math.min(1, MATRIZ[0][0] * r + MATRIZ[0][1] * gg + MATRIZ[0][2] * bb + MATRIZ[0][3]);
        px[k + 1] = 255 * Math.min(1, MATRIZ[1][0] * r + MATRIZ[1][1] * gg + MATRIZ[1][2] * bb + MATRIZ[1][3]);
        px[k + 2] = 255 * Math.min(1, MATRIZ[2][0] * r + MATRIZ[2][1] * gg + MATRIZ[2][2] * bb + MATRIZ[2][3]);
      }
      ctx.putImageData(datos, 0, 0);
    }
    cv.toBlob((blob) => {
      if (!blob) { sueltas(); return; }
      capa.append("image").attr("href", URL.createObjectURL(blob)).attr("x", bx0).attr("y", by0).attr("width", bw).attr("height", bh)
        .attr("preserveAspectRatio", "none").attr("opacity", 0).transition().duration(400).attr("opacity", 1);
    }, "image/jpeg", 0.86);
  }).catch(() => sueltas());
  return capa;
}

/** Caja UTM que cubre todo el lienzo de una proyección de d3 (geoIdentity con invert). */
export function cajaDeLienzo(proy, W, H) {
  const [xa, ya] = proy.invert([0, H]), [xb, yb] = proy.invert([W, 0]);
  return [Math.min(xa, xb), Math.min(ya, yb), Math.max(xa, xb), Math.max(ya, yb)];
}
