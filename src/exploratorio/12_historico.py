import glob
import json
from pathlib import Path

import pandas as pd

import config

plantilla = pd.read_csv("data/mi_equipo/plantilla_actual.csv")
j1 = pd.read_csv("data/mi_equipo/jornada_1_puntos.csv")

archivo_mercado = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo_mercado, encoding="utf-8") as f:
    mercado = json.load(f)
meta_actual = pd.DataFrame([{
    "idPlayer_actual": j["idPlayer"],
    "nick": j.get("nick"),
    "birthdate": j.get("birthdate"),
    "fullName_actual": j.get("fullName"),
} for j in mercado])

plantilla = plantilla.merge(meta_actual, left_on="idPlayer", right_on="idPlayer_actual", how="left")

jug_2526 = pd.read_csv("data/jugadores_2526.csv")
stats_2526 = pd.read_csv("data/stats_jornada_2526.csv")

stats_2526 = stats_2526[stats_2526["valueTimePlayed"] > 0].copy()
stats_2526["minutos"] = stats_2526["valueTimePlayed"] / 60.0

stats_2526["puntos_con_bonus"] = stats_2526.apply(
    lambda r: r["bonusVictory"] if r["bonusVictory"] > 0 else r["pointsJourney"],
    axis=1,
)
agg = stats_2526.groupby("idPlayer").agg(
    partidos_2526=("puntos_con_bonus", "count"),
    media_2526=("puntos_con_bonus", "mean"),
    minutos_2526=("minutos", "mean"),
).reset_index()

precio_final = stats_2526.groupby("idPlayer")["price"].first().rename("precio_final_2526")
agg = agg.merge(precio_final, on="idPlayer")

def buscar(row):
    m = jug_2526[(jug_2526["nick"] == row["nick"]) & (jug_2526["birthdate"] == row["birthdate"])]
    if len(m):
        return m.iloc[0]["idPlayer"]
    m = jug_2526[jug_2526["nick"] == row["nick"]]
    if len(m):
        return m.iloc[0]["idPlayer"]
    fn = str(row["fullName"]).strip().lower()
    m = jug_2526[jug_2526["fullName"].str.strip().str.lower() == fn]
    if len(m):
        return m.iloc[0]["idPlayer"]
    return None

plantilla["idPlayer_2526"] = plantilla.apply(buscar, axis=1)

agg = agg.rename(columns={"idPlayer": "idPlayer_2526_ref"})
df = plantilla.merge(agg, left_on="idPlayer_2526", right_on="idPlayer_2526_ref", how="left")
df = df.drop(columns=["idPlayer_2526_ref"])

df = df.merge(
    j1[["idPlayer", "journeyPoints"]].rename(
        columns={"idPlayer": "idPlayer_actual", "journeyPoints": "puntos_j1"}
    ),
    on="idPlayer_actual",
    how="left",
)

W = config.PESO_JORNADA_ACTUAL
df["media_ponderada"] = W * df["puntos_j1"].fillna(0) + (1 - W) * df["media_2526"]

cols = ["shortName", "nameTeam", "position", "initialPrice",
        "partidos_2526", "media_2526", "minutos_2526",
        "puntos_j1", "media_ponderada", "idPlayer_2526"]
print(df[cols].round(2).to_string(index=False))

Path("data/mi_equipo").mkdir(parents=True, exist_ok=True)
df.to_csv("data/mi_equipo/historico_cruzado.csv", index=False)
print("\nGuardado en data/mi_equipo/historico_cruzado.csv")