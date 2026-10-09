# EXP_09 · Registro previo: fuentes externas y contrastes vecinales

**Escrito el 8 de octubre de 2026, antes de calcular cualquier relación entre las variables nuevas y el rendimiento.** Las descargas de Sentinel-2 propio, Sentinel-1 y embeddings AlphaEarth estaban en curso. Las únicas comprobaciones permitidas antes de la corrida usan solo X: cobertura, nubes, validación de la extracción y correlación entre variables.

Antecedente que esta ronda **no** borra: EXP_08 se diseñó tras explorar las mismas 138 etiquetas, y K1 ya fue visto. Las cifras siguen siendo de desarrollo, no una confirmación independiente.

## Pregunta

¿Alguna fuente que varía a menos de 1 km aporta, como contraste con las vecinas, información sobre el rendimiento que MIX no tiene? Esto incluye borde rojo, radar, embeddings e historia propia de la parcela. ¿Lo hace mejor que el contraste de NDVI Planet de EXP_08?

## Arquitectura común (idéntica a EXP_08)

- Predicción = MIX + Σ β_j · z_j. Los z_j se estandarizan con mediana y desviación del entrenamiento. Sin contraste, z = 0.
- β = (ZᵀZ + αI)⁻¹ Zᵀe, con **α = 10 fijo**. Los residuos e de MIX se obtienen por validación interna con las particiones internas históricas.
- Contraste = valor de la parcela − mediana de las parcelas (entre las 197) a menos de 1 km; se requieren ≥2 vecinas.
- Descriptores de curva: misma función que EXP_08. Base = mediana del día 91–150; pico entre los días 150–304; umbral del 50 %; integral entre inicio y fin del verdor. **Todas las curvas se cortan el 31 de octubre (día 304)**.

## Candidatos (lista cerrada, no se agregan otros después de ver resultados)

| ID | Fuente | Variable | Receta de la curva |
|---|---|---|---|
| K1 | Planet (entregado) | Contraste de la integral NDVI, cortada al 31 oct | Mediana diaria; mediana móvil de 15 días, mínimo 3; nubosidad ≤20 % |
| K2 | Sentinel-2 L2A propio (Planetary Computer) | Contraste de la integral **NDRE** = (B8A − B05)/(B8A + B05) | Píxeles con SCL ∈ {4, 5}; parcela-fecha con ≥50 % de píxeles válidos; mediana móvil de 21 días, mínimo 2 |
| K3 | Sentinel-1 RTC propio, órbita ascendente 5 | Contraste de la integral del **cociente cruzado VH/VV** (lineal) | Media lineal en el polígono; mediana móvil de 25 días, mínimo 2; mismos descriptores |
| K4 | AlphaEarth 2025 (64 dim, 10 m) | **Primer componente principal** de los vectores de contraste (embedding − mediana de vecinas) | PCA sobre las 197 parcelas con contraste, solo X; el signo se fija para que correlacione positivamente con el contraste K1, también solo X |
| K5 | Sentinel-2 entregado, historia | Media 2022–2024 del contraste de `H{año}_S2_ndvi_integral` (tabla v0) | Contraste por año; promedio de los años disponibles |
| K6 | Combinado | K1 + K2 + K3 + K4 + K5 juntos, con la misma α = 10 | — |

## Evaluación

1. **Principal:** las 50 particiones históricas; SEEN135 principal, FULL138 secundario.
2. **Robustez:** 50 particiones nuevas, 5 pliegues × 10 repeticiones con semilla **20261009**, generadas por `KFold(shuffle=True)` sobre los 138 IDs ordenados. Las internas son 4 pliegues con la misma semilla + repetición. Comprueban suerte de partición, no son confirmación independiente.
3. **Nulo de familia:** permutar *juntas* todas las columnas de K1–K5 (misma permutación de filas dentro de cada municipio), recalcular K1–K6 y guardar **el menor RMSE SEEN de los seis**. Con 200 permutaciones, el p de familia es la fracción de nulos ≤ RMSE del candidato elegido.
4. Diagnósticos: concentración (sin las 2 y 5 parcelas más favorecidas), Chignahuapan/resto, soporte en las 59 ocultas.

## Regla de decisión (fijada ahora)

Se elige el candidato con menor RMSE SEEN histórico entre los que cumplen **todas** estas condiciones:

- (a) p de familia ≤ 0.10;
- (b) RMSE < MIX en ≥8/10 repeticiones, en particiones históricas **y** nuevas;
- (c) MAE agrupado ≤ MIX en SEEN histórico;
- (d) la ganancia neta no se invierte al quitar las 2 parcelas más favorecidas.

Si ninguno cumple, se recomienda **MIX** y se reporta K1 como candidato con reservas. Si gana K6, se reporta qué componente pesa más, sin reajustar. El MAE frente a MUN se reporta siempre, pero no decide.

## Presupuesto

6 candidatos × 50 particiones × 2 conjuntos de particiones. Más 200 entrenamientos internos de MIX por conjunto y 200 permutaciones × 6 candidatos × 50 particiones históricas. Son ajustes lineales cerrados, sin búsqueda de hiperparámetros.

## Admisibilidad

Las curvas se cortan al 31 de octubre. **AlphaEarth 2025 resume el año calendario completo** (incluye noviembre–diciembre): se declara como limitación de K4 y K6. Los datos externos son públicos (Sentinel-2/1: Copernicus vía Microsoft Planetary Computer; AlphaEarth: CC-BY 4.0, "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind").
