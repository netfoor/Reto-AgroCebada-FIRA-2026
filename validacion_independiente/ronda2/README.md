# Ronda 2: información externa que cambie dentro del municipio (11–12 oct 2026)

Exploración aislada (Claude Opus, a pedido de Fortino). No modifica archivos existentes ni genera las 59 predicciones.

| Hora CDMX | Paso | Archivo |
|---|---|---|
| 22:10 | Descargas reproducibles: Copernicus DEM GLO-30 y SoilGrids SOC (URL, fecha, SHA-256) | `00_descargar.py`, `datos/registro_descargas.json` |
| 22:14 | Registro previo: H1 (TPI a 1 km, bolsas de aire frío) y H2 (carbono orgánico 0–30 cm), con receta y mecanismo | `00b_registrar.py`, `registro_previo.json` |
| 22:15 | Chequeo solo con X: ambas varían dentro del municipio (R² por celda 0.47 y 0.60 < 0.90) | `01_variables_x.py`, `chequeo_x.json`, `variables_externas.csv` |
| 22:16 | CV 10×5 (semilla 20261021) con las 103 de desarrollo: congelados, F1–F7 y H×{E_JK, MIX} | `02_cv.py`, `resultados_cv/` |
| 22:17 | Reality Check frente a E_JK con 11 familias (p = 1.0) y congelación de H1_E_JK (variante H1_MIX) | `03_nulo_congelar.py`, `congelado.json` |
| 22:19 | Segundo uso, declarado, de la caja de la ronda 1 | `04_caja.py`, `resultados_caja/resultado.json` |

**Resultado:** la etiqueta de la regla es PARCIAL, pero en sustancia es nulo. El final (E_JK + TPI) supera a MIX en la caja solo porque E_JK ya lo hacía. La corrección empeora a su propia base en la CV (2/10) y en la caja (+0.0006). Su pendiente estimada con las 103 parcelas es ≈ 0.

**Atribución:**
- Copernicus DEM: "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA".
- SoilGrids 2.0 (ISRIC), CC-BY 4.0 (Poggio et al., 2021).
