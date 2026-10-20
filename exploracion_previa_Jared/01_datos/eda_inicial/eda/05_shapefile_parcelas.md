# EDA — Shapefile de parcelas (Parcelas_Reto_AGC_CONJUNTO.shp)

Script: `outputs/scripts/05_shapefile_parcelas.R`

## Estructura y validación
- **197 parcelas confirmadas**, tipo geometría `POLYGON` (con Z, coordenada Z siempre 0 — se descarta al usar `sf_use_s2()`).
- CRS: WGS 84 (EPSG:4326, geográfico) — compatible directamente con los rásters CHIRPS/CHIRTS (también EPSG:4326), requiere reproyección para cruzar con la topografía (EPSG:6372).
- Campos: `Cultivo`, `ID_POLIGON` (nombre truncado a 10 caracteres por el formato .dbf — renombrado a `ID_POLIGONO` en el script para ser consistente con los CSV), `área_ha`, `Municipio`, `Estado`, `CONJUNTO`.
- Sin geometrías vacías ni IDs duplicados.
- **2 geometrías inválidas**: `AGC_070` y `AGC_078` (ENTRENAMIENTO), ambas por "edge degenerado (vértice duplicado)" — un problema topológico menor y común en digitalización manual, corregible con `sf::st_make_valid()`. No afecta al cálculo de área (ver abajo) pero puede causar errores en operaciones geométricas más estrictas (intersección, buffer).

## Campo CONJUNTO
- ENTRENAMIENTO: 138 parcelas / PREDICCION: 59 parcelas — coincide exactamente con el split 70/30 documentado y con el archivo `ID_area_rendimiento`.

## Área por parcela
- Estadísticos (atributo `área_ha` del shapefile) por CONJUNTO: ENTRENAMIENTO media 6.58 ha (rango 0.38–64.3), PREDICCION media 6.67 ha (rango 0.35–60.9) — coincide con lo ya visto en `01_id_area_rendimiento.md`.
- **Verificación cruzada:** se recalculó el área geométrica real (reproyectando a EPSG:6372, CRS métrico) y se comparó contra el atributo `área_ha`. La diferencia es sistemática y pequeña: el atributo reportado es en promedio **0.68% menor** que el área geométrica calculada (rango -1.94% a -0.16%), consistente en todas las parcelas. **Ninguna parcela tiene diferencia >5%** — no hay errores de atributo de área, solo un pequeño sesgo sistemático probablemente por el método de cálculo de área usado por el proveedor (ej. área geodésica vs proyectada, o redondeo).

Figuras: `05_mapa_parcelas_por_conjunto.png`, `05_box_area_geometrica_por_conjunto.png`.

## Metadatos adicionales
- `Cultivo`: presenta **inconsistencia de formato** — "Cebada" (50 parcelas) vs "CEBADA" (147 parcelas), mismo valor semántico con distinta capitalización. Se recomienda normalizar (`toupper()`/`tolower()`) antes de cualquier filtro por este campo.
- `Estado`: Puebla 100, Hidalgo 51, Tlaxcala 46.
- `Municipio`: 9 municipios distintos; el más numeroso es Chignahuapan (Puebla, 100 parcelas = el total de Puebla), seguido de Calpulalpan (Tlaxcala, 44) y Almoloya (Hidalgo, 14).

## Hallazgos clave
1. El shapefile es consistente con el resto de archivos (197 parcelas, mismo split 70/30, mismos IDs).
2. Dos geometrías con defecto topológico menor (vértice duplicado) — reparables con `st_make_valid()`, no afectan el área reportada.
3. El área en el atributo del shapefile es confiable (diferencia sistemática <2% frente al cálculo geométrico directo, sin outliers).
4. Inconsistencia trivial de mayúsculas en `Cultivo` — normalizar antes de usar como filtro/variable categórica.
5. Las parcelas se concentran en 3 municipios (Chignahuapan, Calpulalpan, Singuilucan) que agrupan la mayoría de los casos — relevante para entender la heterogeneidad geográfica real de la muestra (menos diversa de lo que sugiere "3 estados").

## Dudas / sugerencias para los organizadores
- Confirmar si el pequeño sesgo sistemático (~0.68%) entre el área reportada y el área geométrica es esperado (p.ej. por el método de cálculo de área usado) o si el atributo `área_ha` debe considerarse la fuente oficial para el reto en lugar del área geométrica recalculada.
- Informar sobre las 2 geometrías con vértices duplicados (AGC_070, AGC_078) por si los organizadores desean corregir el shapefile fuente para futuras ediciones.
