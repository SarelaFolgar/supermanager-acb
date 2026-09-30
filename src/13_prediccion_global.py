import glob
import json
from collections import defaultdict

import numpy as np
import pandas as pd

import config

# === 1. Mercado actual ===
archivo_mercado = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
print(f"Mercado: {archivo_mercado}")
with open(archivo_mercado, encoding="utf-8") as f:
    mercado = json.load(f)

# === 2. Detectar resultado por equipo y jornada ===
# Si el equipo ganó, los puntos son valoración × 1.2.
# - Múltiplo de 1.2 que NO es entero → ganó (imposible sin bonus).
# - Entero que NO es múltiplo de 1.2 → perdió (valoración cruda).
# - Todos enteros múltiplos de 1.2 → ambiguo.
def es_multiplo_12(pts):
    if pts is None or pd.isna(pts) or pts <= 0:
        return False
    return abs((pts / 1.2) - round(pts / 1.2)) < 1e-6

def es_entero(pts):
    if pts is None or pd.isna(pts) or pts <= 0:
        return False
    return abs(pts - round(pts)) < 1e-6

def detectar_resultado(pts_list):
    g = sum(1 for p in pts_list if es_multiplo_12(p) and not es_entero(p))
    l = sum(1 for p in pts_list if es_entero(p) and not es_multiplo_12(p))
    if g > l:
        return 1
    if l > g:
        return 0
    return None

pts_por_equipo_jornada = defaultdict(list)
for j in mercado:
    eq = j["nameTeam"]
    for e in j.get("playerStats", []):
        n = e.get("numberJourney")
        pts = e.get("pointsJourney")
        if pts is not None and n is not None:
            pts_por_equipo_jornada[(eq, n)].append(pts)

resultados = {k: detectar_resultado(v) for k, v in pts_por_equipo_jornada.items()}

# === 3. Construir DataFrame del mercado ===
filas = []
for j in mercado:
    eq = j["nameTeam"]
    rival_logo = None
    prox_local = None

    pts_jugadas = []
    pts_sin_bonus = []
    for e in j.get("playerStats", []):
        n = e.get("numberJourney")
        pts = e.get("pointsJourney")
        if pts is not None and n is not None:
            pts_jugadas.append(pts)
            r = resultados.get((eq, n))
            if r == 1 and pts > 0:
                pts_sin_bonus.append(pts / 1.2)
            else:
                pts_sin_bonus.append(pts)
        if "team" in e:
            rival_logo = e["team"]
            prox_local = e.get("isLocal")

    filas.append({
        "idPlayer": j["idPlayer"],
        "shortName": j["shortName"],
        "nick": j.get("nick"),
        "birthdate": j.get("birthdate"),
        "fullName": j.get("fullName"),
        "nameTeam": eq,
        "position": j["position"],
        "price": j["price"],
        "initialPrice": j["initialPrice"],
        "injuredDays": j.get("injuredDays", 0),
        "fisicStatus": j.get("fisicStatus"),
        "isExtraCommunity": j.get("isExtraCommunity"),
        "isNational": j.get("isNational"),
        "license": j.get("license"),
        "partidos_actual": len(pts_jugadas),
        "media_actual_sin_bonus": np.mean(pts_sin_bonus) if pts_sin_bonus else np.nan,
        "rival_logo": rival_logo,
        "prox_local": prox_local,
    })

df = pd.DataFrame(filas)
print(f"Jugadores en el mercado: {len(df)}")

# === 4. Histórico 2025-26 ===
stats_raw = pd.read_csv("data/stats_jornada_2526.csv")
jug_2526 = pd.read_csv("data/jugadores_2526.csv")

stats_2526 = stats_raw[stats_raw["valueTimePlayed"] > 0].copy()
stats_2526["minutos"] = stats_2526["valueTimePlayed"] / 60.0
stats_2526["puntos_con_bonus"] = stats_2526.apply(
    lambda r: r["bonusVictory"] if r["bonusVictory"] > 0 else r["pointsJourney"],
    axis=1,
)

agg = stats_2526.groupby("idPlayer").agg(
    partidos_2526=("pointsJourney", "count"),
    media_2526_sin_bonus=("pointsJourney", "mean"),
    media_2526_con_bonus=("puntos_con_bonus", "mean"),
    minutos_2526=("minutos", "mean"),
).reset_index()
agg = agg.merge(
    jug_2526[["idPlayer", "nick", "birthdate", "fullName"]],
    on="idPlayer", how="left",
)
agg = agg.rename(columns={
    "idPlayer": "idPlayer_2526",
    "nick": "nick_2526",
    "birthdate": "birthdate_2526",
    "fullName": "fullName_2526",
})

def buscar(row):
    m = agg[(agg["nick_2526"] == row["nick"]) & (agg["birthdate_2526"] == row["birthdate"])]
    if len(m):
        return m.iloc[0]["idPlayer_2526"]
    m = agg[agg["nick_2526"] == row["nick"]]
    if len(m):
        return m.iloc[0]["idPlayer_2526"]
    fn = str(row["fullName"]).strip().lower()
    m = agg[agg["fullName_2526"].str.strip().str.lower() == fn]
    if len(m):
        return m.iloc[0]["idPlayer_2526"]
    return None

df["idPlayer_2526"] = df.apply(buscar, axis=1)
df = df.merge(
    agg[["idPlayer_2526", "partidos_2526", "media_2526_sin_bonus",
         "media_2526_con_bonus", "minutos_2526"]],
    on="idPlayer_2526", how="left",
)
print(f"Con histórico 2025-26: {df['media_2526_con_bonus'].notna().sum()} / {len(df)}")

# === 5. Fuerza de equipo (win% 2025-26 + win% actual, ponderado) ===
eq_jornada = stats_raw.groupby(["nameTeam", "numberJourney"])["bonusVictory"].max().reset_index()
eq_jornada["gano"] = eq_jornada["bonusVictory"] > 0
win_pct_2526 = eq_jornada.groupby("nameTeam")["gano"].mean()
df["win_pct_equipo_2526"] = df["nameTeam"].map(win_pct_2526).fillna(0.5)

# Win% actual (jornadas jugadas de esta temporada)
jornadas_jugadas = sorted(set(n for (_, n) in resultados.keys()))
n_jugadas = len(jornadas_jugadas)
PESO_ACTUAL = n_jugadas / (n_jugadas + config.SUAVIZADO_JORNADAS) if n_jugadas > 0 else 0.0
print(f"Jornadas jugadas detectadas: {jornadas_jugadas}")
print(f"Peso del win% actual vs 2025-26: {PESO_ACTUAL:.2f} / {1 - PESO_ACTUAL:.2f}")

win_actual = {}
for eq in df["nameTeam"].unique():
    wins = 0
    total = 0
    for n in jornadas_jugadas:
        r = resultados.get((eq, n))
        if r is None:
            continue
        total += 1
        wins += r
    win_actual[eq] = wins / total if total > 0 else None

def fuerza(equipo):
    w_actual = win_actual.get(equipo)
    w_2526 = win_pct_2526.get(equipo, 0.5)
    if w_actual is None:
        return w_2526
    return PESO_ACTUAL * w_actual + (1 - PESO_ACTUAL) * w_2526

df["fuerza_equipo"] = df["nameTeam"].apply(fuerza)

logos = pd.read_csv("data/equipos_logos.csv").set_index("logo")["equipo"].to_dict()
df["rival"] = df["rival_logo"].map(logos).fillna(df["rival_logo"])
df["fuerza_rival"] = df["rival"].apply(fuerza)

# === 6. P(ganar) ===
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

df["hfa"] = df["prox_local"].apply(lambda x: 0.10 if x else -0.10)
df["p_win_J2"] = sigmoid((df["fuerza_equipo"] - df["fuerza_rival"]) * 4 + df["hfa"] * 5)
df["p_win_J2"] = df["p_win_J2"].clip(0.05, 0.95)

# === 7. W dinámico ===
df["W"] = df["partidos_actual"] / (df["partidos_actual"] + config.SUAVIZADO_JORNADAS)
df["W"] = df["W"].clip(0, 1)

# === 8. Media sin bonus esperada ===
has_hist = df["media_2526_con_bonus"].notna()
jugo = df["partidos_actual"] > 0
df["media_sin_bonus"] = np.nan

# Con histórico + jugó esta temporada
m = has_hist & jugo
df.loc[m, "media_sin_bonus"] = (
    df.loc[m, "W"] * df.loc[m, "media_actual_sin_bonus"]
    + (1 - df.loc[m, "W"]) * df.loc[m, "media_2526_sin_bonus"]
)

# Con histórico pero sin datos actuales (lesionado toda la temporada, etc.)
m = has_hist & ~jugo
df.loc[m, "media_sin_bonus"] = df.loc[m, "media_2526_sin_bonus"]

# Sin histórico: initialPrice / K como proxy de la media esperada por ACB
media_acb_sin_bonus = (
    df["initialPrice"] / config.K_PRECIO / (1 + 0.2 * df["win_pct_equipo_2526"])
)

# Sin histórico + jugó
m = ~has_hist & jugo
df.loc[m, "media_sin_bonus"] = (
    df.loc[m, "W"] * df.loc[m, "media_actual_sin_bonus"]
    + (1 - df.loc[m, "W"]) * media_acb_sin_bonus[m]
)

# Sin histórico + no jugó
m = ~has_hist & ~jugo
df.loc[m, "media_sin_bonus"] = media_acb_sin_bonus[m]

# === 9. Puntos esperados ===
df["puntos_esperados_J2"] = df["media_sin_bonus"] * (1 + 0.2 * df["p_win_J2"])

# === 10. Precio proyectado J3 y reval esperada ===
K = config.K_PRECIO
df["media_acum_proyectada"] = np.where(
    df["partidos_actual"] > 0,
    (df["media_actual_sin_bonus"] + df["puntos_esperados_J2"]) / 2,
    df["puntos_esperados_J2"],
)
df["precio_objetivo"] = K * df["media_acum_proyectada"]
df["precio_proyectado_J3"] = df.apply(
    lambda r: max(min(r["precio_objetivo"], r["price"] * (1 + config.TOPE_PRECIO)),
                  r["price"] * (1 - config.TOPE_PRECIO)),
    axis=1,
)
df["reval_esperada"] = df["precio_proyectado_J3"] / df["price"] - 1

# === 11. Alertas ===
df["alerta_lesion"] = (df["injuredDays"] > 0) | (df["fisicStatus"] != "fit")

# === 12. Mostrar y guardar ===
cols = ["shortName", "nameTeam", "position", "price",
        "partidos_actual", "W", "media_actual_sin_bonus",
        "media_2526_sin_bonus", "media_sin_bonus",
        "p_win_J2", "puntos_esperados_J2", "reval_esperada", "alerta_lesion"]

print("\n=== TOP 15 puntos esperados ===")
print(df.sort_values("puntos_esperados_J2", ascending=False)[cols].head(15).round(2).to_string(index=False))

print("\n=== TOP 15 revalorización esperada ===")
print(df.sort_values("reval_esperada", ascending=False)[cols].head(15).round(2).to_string(index=False))

df.to_csv("data/prediccion_global.csv", index=False)
print(f"\nGuardado en data/prediccion_global.csv ({len(df)} jugadores)")