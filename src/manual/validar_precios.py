"""
validar_precios.py — Verifica la regla de precios del Supermanager.

Reproduce el precio actual desde initialPrice, jornada a jornada, y lo
compara con el precio observado en la última captura. Prueba con y sin
contar las jornadas sin jugar.

Salida:
  data/procesado/validacion_precios.csv
"""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

K = 50000

archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
print(f"  Captura: {archivo}")
with open(archivo, encoding="utf-8") as f:
    jugadores = json.load(f)


def simular(j, contar_ceros):
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


# === Recopilar detalle por jugador ===
filas = []
for j in jugadores:
    if not j.get("playerStats"):
        continue
    real = j.get("price", 0)
    if real <= 0:
        continue

    pred_con = simular(j, True)
    pred_sin = simular(j, False)

    # Jornadas jugadas vs jornadas con datos
    jugadas = [e.get("numberJourney") for e in j["playerStats"] if "pointsJourney" in e]
    tiene_cero = any(e.get("pointsJourney") == 0 for e in j["playerStats"])

    filas.append({
        "idPlayer": j["idPlayer"],
        "shortName": j["shortName"],
        "nameTeam": j["nameTeam"],
        "initialPrice": j["initialPrice"],
        "price_real": real,
        "pred_con_ceros": round(pred_con, 0),
        "pred_sin_ceros": round(pred_sin, 0),
        "err_con_pct": round((pred_con - real) / real * 100, 3),
        "err_sin_pct": round((pred_sin - real) / real * 100, 3),
        "jornadas_jugadas": jugadas,
        "n_jornadas": len(jugadas),
        "tiene_cero": tiene_cero,
    })

df = pd.DataFrame(filas)
Path("data/procesado").mkdir(parents=True, exist_ok=True)
df.to_csv("data/procesado/validacion_precios.csv", index=False)

print(f"\n  Detalle guardado: data/procesado/validacion_precios.csv ({len(df)} jugadores)")

# === Resumen agregado ===
for contar in (True, False):
    col = "err_con_pct" if contar else "err_sin_pct"
    errores = df[col].abs().values
    print(f"\n  contar_ceros = {contar}")
    print(f"    Error relativo medio: {errores.mean():.2f}%")
    print(f"    Error relativo mediano: {np.median(errores):.2f}%")
    print(f"    Aciertos con error < 1%: {(errores < 1).sum()} / {len(errores)}")
    print(f"    Aciertos con error < 5%: {(errores < 5).sum()} / {len(errores)}")

# === Los que fallan con contar_ceros=True ===
fallos = df[df["err_con_pct"].abs() > 1].copy()
fallos = fallos.sort_values("err_con_pct", key=lambda s: s.abs(), ascending=False)
print(f"\n  === {len(fallos)} jugadores con error > 1% (contando ceros) ===")
print(fallos[["shortName", "nameTeam", "price_real", "pred_con_ceros", "err_con_pct",
              "n_jornadas", "jornadas_jugadas"]].to_string(index=False))