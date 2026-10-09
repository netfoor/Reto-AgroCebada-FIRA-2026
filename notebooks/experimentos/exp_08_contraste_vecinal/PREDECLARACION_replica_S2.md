# Predeclaración — réplica con Sentinel-2 (escrita antes de calcularla)
Fecha/hora: 2026-10-08T12:09:01-06:00
Hallazgo a replicar (exploratorio, Planet): integral de verdor relativa a vecinos <1 km (f_integ_nb1000) correlaciona NEGATIVAMENTE con el residuo OOF de MIX (Spearman -0.286, n=108).
Receta S2 fijada ahora, sin mirar resultados:
- Sentinel-2 NDVI (ndvi_promedio) 2025, porcentaje_nubosidad <= 20.
- Serie diaria = mediana por día; mediana móvil centrada 21 días, min_periods=2; interpolación lineal solo interior.
- Mismas definiciones que Planet: base = mediana DOY 91-150; pico = max DOY 150-330; umbral = base + 0.5*amplitud; integral = suma(curva - base, recortada en 0) entre greenup y senescencia.
- Vecindario: parcelas (de las 197) a < 1000 m, >= 2 vecinos; anomalía = valor - mediana de vecinos.
Predicción a priori: Spearman(S2 integ_nb1000, residuo MIX) < 0 en las 138 y en Chignahuapan.
Criterio: se considera corroboración si el signo es negativo y |rho| >= 0.15 en las 138. Si no, se reporta como no corroborado.
