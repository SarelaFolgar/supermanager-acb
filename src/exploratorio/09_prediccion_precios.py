import glob
import json

import pandas as pd

import config

K = config.K_PRECIO  # € por punto de media (regla oficial)

archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo, encoding="utf-8") as f:
    jugadores = json.load(f)

filas = []
for j in jugadores:
    pts = [e["pointsJourney"] for e in j["playerStats"] if e.get("pointsJourney") is not None]
    filas.append({
        "shortName": j["shortName"],
        "nameTeam": j["nameTeam"],
        "position": j["position"],
        "precio": j["price"],
        "precio_inicial": j["initialPrice"],
        "partidos": len(pts),
        "media": sum(pts) / len(pts) if pts else None,
    })
df = pd.DataFrame(filas)

df["ratio_vs_inicial"] = df["precio"] / df["precio_inicial"]
print("Precio actual / precio inicial:")
print(df["ratio_vs_inicial"].describe().round(3))

df = df[df["media"].notna() & (df["media"] != 0)].copy()
df["gap"] = K * df["media"] / df["precio"] - 1

cols = ["shortName", "nameTeam", "position", "precio", "media", "gap"]
print("\n--- Más margen de SUBIDA ---")
print(df.sort_values("gap", ascending=False)[cols].head(15).round(2).to_string(index=False))
print("\n--- Más margen de BAJADA ---")
print(df.sort_values("gap")[cols].head(10).round(2).to_string(index=False))