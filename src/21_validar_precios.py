"""
21_validar_precios.py

Verifica la regla de precios del Supermanager reproduciendo el precio
actual desde initialPrice, jornada a jornada, y comparándolo con el
precio observado en la última captura.

Prueba con y sin contar las jornadas sin jugar (pointsJourney == 0).

Salida: (solo por consola)
"""
import glob
import json

import numpy as np

K = 50000

archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
print(f"  Captura: {archivo}")
with open(archivo, encoding="utf-8") as f:
    jugadores = json.load(f)


def simular(j, contar_ceros):
    """Reproduce el precio desde initialPrice jornada a jornada."""
    p = j["initialPrice"]
    pts = []
    stats_ordenadas = sorted(
        j.get("playerStats", []),
        key=lambda e: e.get("numberJourney", 0),
    )
    for e in stats_ordenadas:
        x = e.get("pointsJourney")
        if x is None:
            continue
        if x == 0 and not contar_ceros:
            continue
        pts.append(x)
        media = np.mean(pts)
        p = float(np.clip(K * media, p * 0.85, p * 1.15))
    return p


for contar in (True, False):
    errores = []
    for j in jugadores:
        if not j.get("playerStats"):
            continue
        real = j.get("price", 0)
        if real <= 0:
            continue
        pred = simular(j, contar)
        errores.append(abs(pred - real) / real)

    if not errores:
        print(f"  contar_ceros={contar}: sin datos")
        continue

    errores = np.array(errores)
    print(f"\n  contar_ceros = {contar}")
    print(f"    Jugadores evaluados: {len(errores)}")
    print(f"    Error relativo medio: {errores.mean():.2%}")
    print(f"    Error relativo mediano: {np.median(errores):.2%}")
    print(f"    Aciertos con error < 1%: {(errores < 0.01).sum()} / {len(errores)}")
    print(f"    Aciertos con error < 5%: {(errores < 0.05).sum()} / {len(errores)}")