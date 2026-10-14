# Prueba final independiente con caja cerrada (11 oct 2026)

Exploración aislada de Claude (Opus) a pedido de Fortino. **No es un experimento oficial del proyecto, no modifica archivos existentes y no genera las 59 predicciones.** Resultado: **NO FAVORABLE**: ningún procedimiento nuevo superó a E_JK ni a MIX en la caja cerrada.

## Cronología real (CDMX)

| Hora | Paso | Archivo |
|---|---|---|
| 14:09:29 | Caja cerrada (35 parcelas, semilla 20261011) y registro previo, antes de leer cualquier rendimiento | `registro_previo.json`, `00_registrar.py` |
| 14:11 | Validación cruzada 10×5 con las 103 de desarrollo (semilla 20261012): congelados y F1–F5 | `01_desarrollo.py`, `resultados_desarrollo/` |
| 14:12 | F6 y F7 añadidas y anotadas antes de calcularse, tras ver la CV; después no se añadió nada | `intentos.csv`, `01b_desarrollo_adicional.py` |
| 14:13 | Nulo (Reality Check de White sobre las 7 familias) y congelación de F7 | `02_nulo_y_congelar.py`, `congelado.json` |
| 14:14 | Apertura única de la caja | `03_evaluar_caja.py`, `resultados_caja/resultado_caja.json` |
| después | Descriptivos posteriores sin reentrenar; soporte de las 59 solo con X | `05_descriptivo_caja.py`, `04_soporte_59.py` |

## Reproducir (desde `agrocebada-uv`)

```bash
cd validacion_independiente
PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/python 01_desarrollo.py   # se niega si ya existe la salida
```

Los scripts 00, 01, 01b, 02 y 03 se niegan a correr dos veces para preservar el orden. Para reproducir desde cero hay que copiar la carpeta y borrar las salidas en la copia, nunca en esta.

## Notas de transparencia

- El asistente ya había visto las 138 etiquetas en EXP_08–EXP_11. Todas las familias estaban informadas por esa exploración, igual que los candidatos congelados. La caja solo protege contra la selección dentro de esta ronda.
- `congelado.json` tiene una fe de erratas: el texto de `receta_final` se corrigió antes de abrir la caja. El procedimiento congelado siempre fue F7.

---

**Nota de mantenimiento (13 oct 2026).** La carpeta y su biblioteca se renombraron después de cerrar ambas rondas: la carpeta pasó a `validacion_independiente/` y la biblioteca a `lib_validacion.py`. En los scripts solo cambió la línea de importación. Los hashes de `registro_previo.json` y `congelado.json` corresponden a la versión anterior al renombrado, por lo que `03_evaluar_caja.py` ya no pasa su comprobación de integridad. La caja cerrada era de un solo uso y no debe reejecutarse. Los resultados guardados no cambiaron.
