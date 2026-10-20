"""ejemplo_modelo_externo.py: plantilla para probar un modelo propio con comparar_modelo_externo.py.

Copia este archivo, cambia el cuerpo de predecir() por tu modelo y corre:
    python comparar_modelo_externo.py --modelo ejemplo_modelo_externo.py --nombre MiModelo

Este ejemplo es B2 (media del grupo) mas un efecto de la media de la celda climatica encogida (tipo B3 simple).
"""
import numpy as np


def predecir(ajuste, validacion):
    """ajuste: parcelas de ajuste con RENDIMIENTO_T_HA. validacion: parcelas a predecir, sin rendimiento.
    Todo lo que se elija o se ajuste debe salir solo de `ajuste`."""
    media_g = ajuste.groupby("grupo")["RENDIMIENTO_T_HA"].mean()
    base = validacion["grupo"].map(media_g)
    res = ajuste["RENDIMIENTO_T_HA"] - ajuste["grupo"].map(media_g)
    n = res.groupby(ajuste["celda_clima"]).size()
    s = res.groupby(ajuste["celda_clima"]).sum()
    k = 4.0
    ajuste_celda = validacion["celda_clima"].map(lambda c: s[c] / (n[c] + k) if c in n.index else 0.0)
    return (base + ajuste_celda).to_numpy(float)
