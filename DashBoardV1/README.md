# DashBoardV1

Versión combinada del sitio del equipo (carpeta `web/`) con el mapa satelital interactivo.

## Qué cambia frente a `web/`

- **Tablero:** el mapa ahora es una imagen de satélite (Leaflet + Esri World Imagery) con vista azul o natural, ficha flotante al elegir una parcela, anillo de 1 km con sus vecinas y un recorrido de 7 pasos que avanza con scroll o con clic.
- **Glosario:** debajo del tablero se explican MUN, MIX, K, J, E_JK, RMSE y el rango 80 % en palabras simples.
- **Cómo se hizo:** las figuras que son mapas llevan satélite y las etapas se pueden elegir con clic.
- **Ejecutar el modelo:** flujo en tres pasos, con el cálculo como lista numerada y la figura de vecinas sobre satélite.
- **Cómo está hecho este sitio:** sección final con las bibliotecas usadas y el código aplicado.

Los datos, las fórmulas y la verificación SHA-256 son los mismos del sitio original.

## Correrlo

```bash
# datos (desde la raíz del repositorio)
uv run --group geo python scripts/exportar_web.py

# sitio (Node 22.12 o posterior)
cd DashBoardV1
npm ci
npm run dev      # http://localhost:4321
npm run build    # deja el sitio en DashBoardV1/dist
```

`dist/` ya viene construido: se puede servir tal cual en cualquier hosting estático (por ejemplo con `npx serve dist`).
