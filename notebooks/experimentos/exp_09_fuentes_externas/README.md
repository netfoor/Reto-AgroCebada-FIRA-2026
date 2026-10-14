# EXP_09 · Fuentes externas y contrastes vecinales

8 de octubre de 2026. **Ronda registrada antes de ver resultados** (`REGISTRO_PREVIO.md`). Sin las 59 predicciones.

> **Fe de erratas (8 oct 2026, posterior; ver [EXP_10](../exp_10_verificacion_contraste_vecinal/RESULTADOS_Y_CIERRE.md)).** El registro decía "todas las curvas se cortan el 31 de octubre", pero `curva()` suavizaba e interpolaba con todo el año y `integral()` recortaba después. Así, noviembre influía en octubre en K1, K2 y K3.
> - EXP_10 corrige K1: SEEN135 0.48198 (históricas) y 0.48096 (nuevas), frente a 0.48159 y 0.48069 publicados. Mejora a MIX en 20/20 repeticiones; p de familia 0.18 (permutación) y 0.13 (nulo espacial).
> - K2 y K3 no se reevaluaron.
> - El cierre de esta ronda (recomendar MIX) se conserva.

## Archivos

| Archivo | Qué es |
| --- | --- |
| `REGISTRO_PREVIO.md` | Candidatos, recetas, evaluación y regla de decisión, escritos antes de la corrida |
| `exp_09_fuentes_externas.ipynb` | Cuaderno ejecutado (~4.5 min): validación de la extracción, candidatos, evaluación, nulo de familia y decisión |
| `IDEAS_FUERA_DEL_PLAZO.md` | Lista aparte: lo que no cabe en jueves–viernes, con quién podría tomarlo en paralelo |
| `../../../data/exp_09_fuentes_externas/` | Extracciones por parcela (S2, S1, AlphaEarth), escenas usadas y particiones nuevas |
| `../../../scripts/exp_09_extraer_externos.py` | Descarga reproducible (S2 ~15 min, S1 ~9 min, AEF ~5 min). Probado: reproduce las filas guardadas sin diferencias. |
| `../../../scripts/construir_exp_09.py` | Generador del cuaderno |

## Resultado (SEEN135)

| Candidato | Fuente | RMSE hist. | RMSE nuevas | Reps < MIX (hist./nuevas) | p familia |
| --- | --- | --- | --- | --- | --- |
| MIX | — | 0.4872 | 0.4857 | — | — |
| **K1** | NDVI Planet entregado, contraste 1 km, al 31 oct | **0.4816** | **0.4807** | 10/10 · 10/10 | 0.13 |
| K2 | Borde rojo (NDRE), Sentinel-2 propio | 0.4846 | 0.4848 | 7 · 6 | 0.26 |
| K3 | Radar VH/VV, Sentinel-1 propio | 0.4858 | 0.4835 | 8 · 9 | 0.38 |
| K4 | Embeddings AlphaEarth 2025 | 0.4899 | 0.4867 | 3 · 6 | 0.96 |
| K5 | Historia 2022–2024 (contraste) | 0.4881 | 0.4869 | 5 · 5 | 0.72 |
| K6 | Todo junto | 0.4867 | 0.4872 | 4 · 5 | 0.47 |

**Regla registrada:** ninguno cumple las cuatro condiciones. K1 cumple (b) repeticiones, (c) MAE ≤ MIX y (d) robustez a quitar 2 parcelas, pero no (a), con p de familia 0.13 > 0.10. **Recomendación formal: MIX, con K1 como candidato con reservas.**

## Para el reporte

- **Los datos entregados bastan.** Borde rojo, radar, embeddings y máscara de nubes propia, con extracción validada (r = 0.994 frente al NDVI entregado), no superan al contraste del NDVI Planet entregado.
- **Signos coherentes.** El exceso de verdor frente a las vecinas *en 2025* se asocia con menor rendimiento, y NDVI, borde rojo y radar coinciden. Ser más verde que las vecinas *históricamente* se asocia con mayor rendimiento.
- **Más variables empeoran** (K6). El modelo final debe ser simple.

## Pendiente de integrar

Fila en `docs/bitacora_experimentos.md`, enlaces en los README y atribución de AlphaEarth en el reporte final ("The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind", CC-BY 4.0).
