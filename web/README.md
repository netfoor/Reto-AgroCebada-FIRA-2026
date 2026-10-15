# Sitio

Página estática que consulta las 59 estimaciones, ejecuta el modelo en el navegador y lo reentrena en AWS. Está hecha con [Astro](https://astro.build), d3 para mapas y gráficas, y anime.js para la animación de la portada y las figuras que avanzan con el scroll. Terraform la publica desde `web/dist` (ver [`infra/`](../infra/README.md)).

| Carpeta | Contenido |
|---|---|
| `src/components/` | Secciones de la página: portada, tablero, estimaciones, ejecutar, cómo se hizo, para qué sirve, preguntas guía y pie. |
| `src/scripts/` | La parte interactiva. `comun.js` tiene la fórmula del modelo final, la misma del cuaderno 04; `escenas.js`, las figuras de «Cómo se hizo». |
| `public/datos/` | JSON que lee la página y su manifiesto con SHA-256. Los genera `scripts/exportar_web.py`. |
| `public/descargas/` | Los tres CSV de la entrega (copias exactas) y el libro de Excel. |
| `public/logos/`, `public/img/` | Logos de UTP, Tec de Monterrey y FIRA, y la imagen de la cebada. |

Al abrir la página, el navegador descarga el manifiesto, calcula la SHA-256 de cada archivo de datos y la compara antes de usarlo; si alguno no coincide, avisa y no muestra datos. El botón «Reentrenar en AWS» llama a `/api/reentrenar`, que CloudFront envía a la función de Lambda.

## Actualizar y publicar

Desde la raíz del repositorio:

```bash
# 1. Datos del sitio (usa data/raw/DataSet.zip y las carpetas de data/ del cuaderno 04)
uv run --group geo python scripts/exportar_web.py

# 2. Construir (Node 22.12 o posterior)
cd web
npm ci
npm run build          # deja el sitio en web/dist

# 3. Publicar
cd ../infra
terraform apply
```

El exportador comprueba que, con los datos que escribe, el cálculo del navegador da las 59 estimaciones del CSV entregado. Si nada cambió, sus archivos salen idénticos y Terraform no vuelve a subirlos.

Para trabajar en local: `npm run dev` dentro de `web/` y abrir http://localhost:4321. Las llamadas a `/api` se envían a la distribución desplegada; para usar otra, define `AGRO_API=https://…` antes de arrancar.

## Diseño

- Tipografía: Amazon Ember cuando el equipo la tiene; si no, la del sistema (San Francisco, Segoe UI o Roboto). Ninguna fuente se descarga.
- Azul marino y verde de la portada de las bases del reto y del logo de FIRA; paja de la cebada. El rendimiento usa una rampa café de 6 clases, con cortes fijos en 3, 3.5, 4, 4.5 y 5 t/ha; las parcelas estimadas llevan surcos.
- El encabezado muestra la sección actual; la línea verde de abajo es el avance de la página y cada marca, el inicio de una sección.
