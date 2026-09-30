import glob
import json

import pandas as pd

archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo, encoding="utf-8") as f:
    jugadores = json.load(f)

filas = []
for j in jugadores:
    fila = {
        "idPlayer": j["idPlayer"],
        "shortName": j["shortName"],
        "nameTeam": j["nameTeam"],
        "position": j["position"],
        "price": j["price"],
        "injuredDays": j["injuredDays"],
        "fisicStatus": j["fisicStatus"],
    }
    for e in j["playerStats"]:
        n = e.get("numberJourney")
        if "pointsJourney" in e:
            fila[f"pts_j{n}"] = e["pointsJourney"]
        if "team" in e:
            fila["prox_jornada"] = n
            fila["prox_rival_logo"] = e["team"]
            fila["prox_local"] = e["isLocal"]
    filas.append(fila)

df = pd.DataFrame(filas)

print("--- Próximo partido por equipo ---")
equipos = df.groupby("nameTeam")[["prox_jornada", "prox_rival_logo", "prox_local"]].first()
print(equipos.to_string())

print("\n--- Top 10 puntos en la J1 ---")
cols = ["shortName", "nameTeam", "position", "price", "pts_j1"]
print(df.sort_values("pts_j1", ascending=False)[cols].head(10).to_string(index=False))