# EXP_10 · Resultados y cierre

8 de octubre de 2026 (CDMX). Autor: Claude (asistente), a pedido de Fortino, tras una revisión del equipo que detectó la discrepancia temporal. Registro previo: 17:36 h CDMX (23:36:47 UTC). Corrida registrada y réplica: después del registro, en el mismo día.

## a) Discrepancia técnica

**Confirmada.** En la receta publicada de K1 (EXP_09, y en la variante "hasta 31 oct" de EXP_08), la curva se suaviza e interpola con capturas de todo el año y el corte al día 304 se aplica después. Las capturas de noviembre modificaban valores de octubre.

- Afectaba **130 de 197 integrales** (|Δ| mediana 0.082, máx. 1.24 NDVI·día, sobre integrales de ≈46) y **131 de 158 contrastes** (Spearman 0.998).
- La receta corregida descarta lo posterior al 31/10 antes de suavizar. Es invariante a cambiar, borrar o añadir capturas posteriores (0 cambios en los tres escenarios; la publicada cambia 114, 130 y 131).
- La cobertura es la misma: 108 etiquetadas y 50 ocultas con contraste. Ningún contraste depende de una sola vecina válida, así que la regla de vecinos no se modificó.

## b) Mejora predictiva observada (SEEN135)

| Procedimiento | RMSE históricas | MAE históricas | RMSE nuevas | MAE nuevas |
|---|---|---|---|---|
| MUN | 0.49340 | 0.32127 | 0.49222 | 0.32133 |
| MIX | 0.48720 | 0.33421 | 0.48567 | 0.33571 |
| K1 publicado (reproduce EXP_09) | 0.48159 | 0.33300 | 0.48069 | 0.33472 |
| **K1 corregido** | **0.48198** | 0.33337 | **0.48096** | 0.33488 |

- **K1 corregido frente a MIX:** −0.0052 (históricas) y −0.0047 (nuevas) t/ha de RMSE. Mejora en 10/10 repeticiones de cada juego; la menos favorable de las nuevas es −0.0004.
- **K1 corregido frente al publicado:** +0.0004 y +0.0003, peor en las 20 repeticiones. La discrepancia inflaba la ganancia en ~7 %, pero no la explicaba.
- FULL138 (secundario): MIX 0.4938/0.4923; K1 corregido 0.4879/0.4870.

## c) Estabilidad y concentración

- **Por zona:** mejora en Chignahuapan (0.5736 → 0.5687), Singuilucan y Almoloya. En Calpulalpan queda ligeramente peor que MIX. Fuera de Chignahuapan, MUN sigue siendo mejor que ambos.
- **Retirando parcelas solo al evaluar:**
  - Sin las 2 más favorecidas (AGC_162, AGC_172), la mejora sigue, pero es mínima: −0.0010 (históricas) y −0.0006 (nuevas).
  - Sin las 5, se invierte en ambos juegos (+0.0033 y +0.0035).
- **Nulos de familia** (mejor de seis candidatos, 200 sorteos cada uno, ejecutados una vez):
  - N0 reproduce exactamente el p = 0.13 de EXP_09.
  - Con K1 corregido: **p = 0.184** con la permutación municipal (N1) y **p = 0.129** con la aleatorización espectral de Moran (N2), que conserva la dependencia espacial y la ubicación de los faltantes.

## d) Regla registrada y recomendación provisional

| Condición (SEEN135, ambos juegos) | K1 corregido |
|---|---|
| R1 RMSE < MIX | Sí |
| R2 ≥8/10 repeticiones | Sí (10 y 10) |
| R3 MAE ≤ MIX | Sí |
| R4 no se invierte quitando 2 parcelas | Sí (por poco) |
| S p de familia ≤ 0.10 en N1 y N2 | **No** (0.184 y 0.129) |

**K1 corregido cumple los requisitos predictivos de desarrollo, pero no hay evidencia estadística suficiente para adoptarlo.** Recomendación provisional según la regla: **conservar MIX como referencia oficial**. K1 corregido queda como alternativa documentada. Elegirlo para la entrega es una decisión explícita del equipo, con estos límites a la vista.

El cierre de EXP_09 (recomendar MIX) se conserva y es consistente con este resultado.

## Qué incertidumbre permanece

- **Selección previa:** K1 se eligió tras explorar estas mismas 138 etiquetas. Ningún registro posterior lo convierte en una confirmación independiente.
- **Repeticiones:** las 10 de cada juego reutilizan las mismas parcelas. El acuerdo entre juegos indica que el resultado no depende de la semilla, pero no de las parcelas.
- **Nulos:**
  - Los dos nulos usan supuestos distintos (intercambio dentro de municipio; invariancia espectral) y ninguno es exacto.
  - Con 200 sorteos, la resolución del p es de ~±0.02.
  - La familia de calibración usa K2/K3 con su receta publicada, que comparte la discrepancia temporal.
- **Concentración:** el error esperado en las 59 depende de si contienen parcelas como AGC_162/172. Un ~1 % de mejora media es pequeño frente a la variación entre particiones.
- **Soporte de las ocultas:** 9 de 59 no tienen contraste y recibirían MIX. Nanacamilpa (AGC_120) tiene una sola etiqueta y no tiene caso OOF equivalente.

## Presupuesto real (por corrida; la réplica repite exactamente lo mismo)

| Concepto | Cantidad |
|---|---|
| Evaluaciones de referencias exteriores (MUN+MIX) | 100 |
| Evaluaciones MIX internas (residuos) | 400 |
| Ajustes de corrección (2 K1 × 100 pliegues) | 200 |
| Control de fuga (validación con etiquetas sustituidas) | 100 + 400 + 200; predicciones idénticas |
| Ajustes de corrección en nulos | 180,900 = 3 nulos × (200 sorteos + observado) × 6 candidatos × 50 pliegues |
| Réplica de determinismo | Mismo presupuesto; 13 archivos científicos idénticos byte a byte |
| Lectura del notebook | 0 ajustes (dos kernels limpios; Colab real no probado) |

## Evidencia

- [Protocolo](protocolo.md) y [registro previo](registro_previo.json).
- [Notebook](exp_10_verificacion_contraste_vecinal.ipynb).
- [Verificación independiente](verificacion_independiente.json): predicciones reimplementadas, diferencia máx. 2.7e-15; métricas 1.1e-16; réplica idéntica; N0 = 0.13.
- Resultados en `resultados/exp_10_verificacion_contraste_vecinal/registrada/` y `.../replica_determinismo/`.
- Datos derivados en `data/exp_10_verificacion_contraste_vecinal/`.
- Código: `scripts/modelo_10.py`, `factibilidad_10.py`, `experimento_10.py`, `verificar_exp_10_resultados.py`, `construir_exp_10.py`, `ejecutar_notebook_exp_10.py`; pruebas en `tests/test_modelo_10.py`.
