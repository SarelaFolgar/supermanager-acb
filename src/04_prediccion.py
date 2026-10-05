import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import config

# Override por línea de comandos (usado por 08_explorar_suavizado.py)
if len(sys.argv) > 1:
    try:
        config.SUAVIZADO_JORNADAS = int(sys.argv[1])
        print(f"  SUAVIZADO override: {config.SUAVIZADO_JORNADAS}")
    except ValueError:
        pass

# === 1. Mercado actual ===
archivo_mercado = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo_mercado, encoding="utf-8") as f:
    mercado = json.load(f)

# === 2. Detectar resultado por equipo y jornada ===
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

# === 3. DataFrame del mercado ===
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
        "sum_points_actual": sum(pts_jugadas) if pts_jugadas else 0.0,
        "media_actual_sin_bonus": np.mean(pts_sin_bonus) if pts_sin_bonus else np.nan,
        "rival_logo": rival_logo,
        "prox_local": prox_local,
    })

df = pd.DataFrame(filas)

# === 4. Histórico 2025-26 ===
stats_raw = pd.read_csv("data/historico/2025-26/stats_jornada.csv")
jug_2526 = pd.read_csv("data/historico/2025-26/jugadores.csv")

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
    jug_2526[["idPlayer", "nick", "birthdate", "fullName", "nameTeam", "shortName"]],
    on="idPlayer", how="left",
)
agg = agg.rename(columns={
    "idPlayer": "idPlayer_2526",
    "nick": "nick_2526",
    "birthdate": "birthdate_2526",
    "fullName": "fullName_2526",
    "nameTeam": "nameTeam_2526",
    "shortName": "shortName_2526",
})

def buscar(row):
    # 1) shortName + birthdate (estricto)
    if pd.notna(row.get("shortName")) and pd.notna(row.get("birthdate")):
        m = agg[(agg["shortName_2526"] == row["shortName"]) &
                (agg["birthdate_2526"] == row["birthdate"])]
        if len(m):
            return m.iloc[0]["idPlayer_2526"]

    # 2) fullName normalizado
    fn = str(row["fullName"]).strip().lower()
    m = agg[agg["fullName_2526"].str.strip().str.lower() == fn]
    if len(m):
        return m.iloc[0]["idPlayer_2526"]

    # 3) nick + birthdate (por si acaso)
    if pd.notna(row.get("nick")) and pd.notna(row.get("birthdate")):
        m = agg[(agg["nick_2526"] == row["nick"]) &
                (agg["birthdate_2526"] == row["birthdate"])]
        if len(m):
            return m.iloc[0]["idPlayer_2526"]

    # 4) Sin match
    return None

df["idPlayer_2526"] = df.apply(buscar, axis=1)
df = df.merge(
    agg[["idPlayer_2526", "partidos_2526", "media_2526_sin_bonus",
         "media_2526_con_bonus", "minutos_2526", "nameTeam_2526"]],
    on="idPlayer_2526", how="left",
)

def normaliza(eq):
    if pd.isna(eq):
        return None
    return str(eq).strip().lower()

df["cambio_equipo"] = (
    df["nameTeam_2526"].notna()
    & (df["nameTeam"].apply(normaliza) != df["nameTeam_2526"].apply(normaliza))
)

# === 5. Fuerza de equipo (win% + localía) ===
eq_jornada = stats_raw.groupby(["nameTeam", "numberJourney"])["bonusVictory"].max().reset_index()
eq_jornada["gano"] = eq_jornada["bonusVictory"] > 0
win_pct_2526 = eq_jornada.groupby("nameTeam")["gano"].mean()
df["win_pct_equipo_2526"] = df["nameTeam"].map(win_pct_2526).fillna(0.5)

jornadas_jugadas = sorted(set(n for (_, n) in resultados.keys()))
n_jugadas = len(jornadas_jugadas)
PESO_ACTUAL = n_jugadas / (n_jugadas + config.SUAVIZADO_JORNADAS) if n_jugadas > 0 else 0.0

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
    """Fuerza del equipo como win% combinado (histórico + actual)."""
    w_actual = win_actual.get(equipo)
    w_2526 = win_pct_2526.get(equipo, 0.5)
    if w_actual is None:
        return w_2526
    return PESO_ACTUAL * w_actual + (1 - PESO_ACTUAL) * w_2526


df["fuerza_equipo"] = df["nameTeam"].apply(fuerza)

logos = pd.read_csv("data/procesado/equipos_logos.csv").set_index("logo")["equipo"].to_dict()
df["rival"] = df["rival_logo"].map(logos).fillna(df["rival_logo"])
df["fuerza_rival"] = df["rival"].apply(fuerza)

# === 6. P(win) ===
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

df["hfa"] = df["prox_local"].apply(lambda x: 0.10 if x else -0.10)
df["p_win"] = sigmoid((df["fuerza_equipo"] - df["fuerza_rival"]) * 4 + df["hfa"] * 5)
df["p_win"] = df["p_win"].clip(0.05, 0.95)

# === 7. W dinámico y factor histórico ===
df["W"] = df["partidos_actual"] / (df["partidos_actual"] + config.SUAVIZADO_JORNADAS)
df["W"] = df["W"].clip(0, 1)

df["factor_hist"] = np.where(
    df["cambio_equipo"] & (df["partidos_actual"] >= config.MIN_PARTIDOS_FACTOR_HIST),
    config.FACTOR_HIST_CAMBIO_EQUIPO,
    config.FACTOR_HIST_MISMO_EQUIPO,
)
df["peso_hist"] = (1 - df["W"]) * df["factor_hist"]
df["peso_actual"] = 1 - df["peso_hist"]

# === 8. Media sin bonus esperada ===
has_hist = df["media_2526_con_bonus"].notna()
jugo = df["partidos_actual"] > 0
df["media_sin_bonus"] = np.nan

m = has_hist & jugo
df.loc[m, "media_sin_bonus"] = (
    df.loc[m, "peso_actual"] * df.loc[m, "media_actual_sin_bonus"]
    + df.loc[m, "peso_hist"] * df.loc[m, "media_2526_sin_bonus"]
)

m = has_hist & ~jugo
df.loc[m, "media_sin_bonus"] = df.loc[m, "media_2526_sin_bonus"]

media_acb_sin_bonus = (
    df["initialPrice"] / config.K_PRECIO / (1 + 0.2 * df["win_pct_equipo_2526"])
)

m = ~has_hist & jugo
df.loc[m, "media_sin_bonus"] = (
    df.loc[m, "W"] * df.loc[m, "media_actual_sin_bonus"]
    + (1 - df.loc[m, "W"]) * media_acb_sin_bonus[m]
)

m = ~has_hist & ~jugo
df.loc[m, "media_sin_bonus"] = media_acb_sin_bonus[m]

# === 9. Puntos esperados ===
df["puntos_esperados"] = df["media_sin_bonus"] * (1 + 0.2 * df["p_win"])

# === 10. Modelo probabilístico de revalorización ===
K = config.K_PRECIO

def calcular_distribucion(precio, S, N, mu, seed):
    rng = np.random.default_rng(seed)
    sd = max(config.SD_BASE + config.SD_ESCALA_MU * mu, 1.0)
    x = rng.normal(mu, sd, config.N_SIMULACIONES)
    objetivo = K * (S + x) / (N + 1)
    nuevo = np.clip(objetivo, precio * (1 - config.TOPE_PRECIO),
                    precio * (1 + config.TOPE_PRECIO))
    reval_esperado = float(nuevo.mean() - precio)
    p_sube = float((objetivo >= precio * (1 + config.TOPE_PRECIO)).mean())
    p_baja = float((objetivo <= precio * (1 - config.TOPE_PRECIO)).mean())
    return reval_esperado, p_sube, p_baja

revals, ps_sube, ps_baja = [], [], []
for _, r in df.iterrows():
    if pd.isna(r["puntos_esperados"]) or r["partidos_actual"] == 0:
        revals.append(0.0)
        ps_sube.append(0.0)
        ps_baja.append(0.0)
        continue
    rev, ps, pb = calcular_distribucion(
        precio=r["price"],
        S=r["sum_points_actual"],
        N=int(r["partidos_actual"]),
        mu=r["puntos_esperados"],
        seed=int(r["idPlayer"]),
    )
    revals.append(rev)
    ps_sube.append(ps)
    ps_baja.append(pb)

df["reval_euros"] = revals
df["p_sube_15"] = ps_sube
df["p_baja_15"] = ps_baja
df["reval_esperada"] = df["reval_euros"] / df["price"].replace(0, np.nan)
df["reval_euros_norm"] = df["reval_euros"] / 100_000

df["N_actual"] = df["partidos_actual"]
df["media_implicita"] = df["price"] / K
df["umbral_mantiene"] = (
    df["media_implicita"] * (df["N_actual"] + 1) - df["sum_points_actual"]
)
df["umbral_sube_15"] = (
    df["media_implicita"] * (1 + config.TOPE_PRECIO) * (df["N_actual"] + 1)
    - df["sum_points_actual"]
)
df["umbral_baja_15"] = (
    df["media_implicita"] * (1 - config.TOPE_PRECIO) * (df["N_actual"] + 1)
    - df["sum_points_actual"]
)

def pronostico(p_sube, p_baja):
    if p_sube >= 0.5:
        return "upup"
    if p_sube >= 0.25:
        return "up"
    if p_baja >= 0.5:
        return "downdown"
    if p_baja >= 0.25:
        return "down"
    return "flat"

df["pronostico"] = [
    pronostico(ps, pb) for ps, pb in zip(df["p_sube_15"], df["p_baja_15"])
]

df["alerta_lesion"] = (df["injuredDays"] > 0) | (df["fisicStatus"] != "fit")

# === 11. Guardar ===
df.to_csv("data/procesado/prediccion_global.csv", index=False)
print(f"  Predicciones: {len(df)} jugadores | "
      f"{df['media_2526_con_bonus'].notna().sum()} con historico | "
      f"{df['cambio_equipo'].sum()} cambiaron de equipo | "
      f"J{int(df['partidos_actual'].max())} jugada(s)")