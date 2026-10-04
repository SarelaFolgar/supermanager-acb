"""
18_modelo_minutos.py — Modelo v2 basado en minutos y puntos por minuto.

Puntos esperados = PPM_esperado × minutos_esperados × (1 + 0.2 × p_win)

Correcciones para reducir ruido con pocas jornadas:
  A) Shrink del PPM actual hacia la mediana de su posición.
  B) Clip del PPM a [0, 1.2] para evitar valores absurdos.

Entrada:
  data/prediccion_con_minutos.csv
  data/stats_jornada_2526.csv

Salida:
  data/prediccion_v2.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd


# ─── Parámetros de suavizado ────────────────────────────────
PPM_MIN = 0.0      # Opción B
PPM_MAX = 1.2      # Opción B
K_SHRINK = 4       # Opción A: cuánto pesa la mediana de la posición


def main():
    pred = pd.read_csv("data/prediccion_con_minutos.csv")
    stats = pd.read_csv("data/stats_jornada_2526.csv")

    # ─── PPM histórico sin bonus ────────────────────────────
    stats = stats[stats["valueTimePlayed"] > 0].copy()
    stats["minutos"] = stats["valueTimePlayed"] / 60.0

    hist = stats.groupby("idPlayer").agg(
        minutos_hist_tot=("minutos", "sum"),
        puntos_hist_tot=("pointsJourney", "sum"),   # sin bonus
    ).reset_index()
    hist["ppm_hist_sin_bonus"] = hist["puntos_hist_tot"] / hist["minutos_hist_tot"]
    hist = hist.rename(columns={"idPlayer": "idPlayer_2526"})

    pred = pred.merge(
        hist[["idPlayer_2526", "ppm_hist_sin_bonus"]],
        on="idPlayer_2526", how="left",
    )

    # ─── PPM actual sin bonus ───────────────────────────────
    pred["ppm_actual_sin_bonus"] = np.where(
        pred["minutos_medios"] > 0,
        pred["val_medios"] / pred["minutos_medios"],
        np.nan,
    )

    # ─── Opción B: clip PPM a [PPM_MIN, PPM_MAX] ────────────
    n_clip_act = int(
        ((pred["ppm_actual_sin_bonus"] < PPM_MIN) |
         (pred["ppm_actual_sin_bonus"] > PPM_MAX)).sum()
    )
    n_clip_hist = int(
        ((pred["ppm_hist_sin_bonus"] < PPM_MIN) |
         (pred["ppm_hist_sin_bonus"] > PPM_MAX)).sum()
    )
    pred["ppm_actual_sin_bonus"] = pred["ppm_actual_sin_bonus"].clip(PPM_MIN, PPM_MAX)
    pred["ppm_hist_sin_bonus"] = pred["ppm_hist_sin_bonus"].clip(PPM_MIN, PPM_MAX)

    # ─── Opción A: shrink del PPM actual hacia la mediana de su posición ─
    # Ancla: mediana del PPM combinado por posición (usa histórico si está, si no actual).
    pred["ppm_combined"] = pred["ppm_hist_sin_bonus"].fillna(pred["ppm_actual_sin_bonus"])
    anchor_pos = pred.groupby("position")["ppm_combined"].median().to_dict()

    n_part = pred["partidos_rincon"].fillna(0)
    ancla = pred["position"].map(anchor_pos).fillna(0.5)
    pred["ppm_actual_ajustado"] = (
        pred["ppm_actual_sin_bonus"].fillna(0) * n_part + ancla * K_SHRINK
    ) / (n_part + K_SHRINK)

    # ─── Flags de disponibilidad ────────────────────────────
    W = pred["W"]
    tiene_hist = pred["minutos_2526"].notna() & (pred["minutos_2526"] > 0)
    tiene_actual = pred["minutos_medios"].notna() & (pred["minutos_medios"] > 0)
    tiene_ppm_hist = pred["ppm_hist_sin_bonus"].notna()

    # ─── Minutos esperados ──────────────────────────────────
    pred["minutos_esperados"] = np.nan

    m = tiene_hist & tiene_actual
    pred.loc[m, "minutos_esperados"] = (
        W[m] * pred.loc[m, "minutos_medios"]
        + (1 - W[m]) * pred.loc[m, "minutos_2526"]
    )

    m = ~tiene_hist & tiene_actual
    pred.loc[m, "minutos_esperados"] = pred.loc[m, "minutos_medios"]

    m = tiene_hist & ~tiene_actual
    pred.loc[m, "minutos_esperados"] = pred.loc[m, "minutos_2526"]

    # ─── PPM esperado ───────────────────────────────────────
    pred["ppm_esperado"] = np.nan

    m = tiene_actual & tiene_ppm_hist
    pred.loc[m, "ppm_esperado"] = (
        W[m] * pred.loc[m, "ppm_actual_ajustado"]
        + (1 - W[m]) * pred.loc[m, "ppm_hist_sin_bonus"]
    )

    m = tiene_actual & ~tiene_ppm_hist
    pred.loc[m, "ppm_esperado"] = pred.loc[m, "ppm_actual_ajustado"]

    m = ~tiene_actual & tiene_ppm_hist
    pred.loc[m, "ppm_esperado"] = pred.loc[m, "ppm_hist_sin_bonus"]

    # ─── Puntos esperados v2 ────────────────────────────────
    pred["puntos_esperados_v2"] = (
        pred["ppm_esperado"] * pred["minutos_esperados"]
        * (1 + 0.2 * pred["p_win_J2"])
    )

    # ─── Fallback v1 si no hay datos ────────────────────────
    sin_datos = pred["puntos_esperados_v2"].isna()
    pred.loc[sin_datos, "puntos_esperados_v2"] = pred.loc[sin_datos, "puntos_esperados_J2"]
    pred["metodo_v2"] = np.where(sin_datos, "v1_fallback", "v2_minutos")

    # ─── Guardar ────────────────────────────────────────────
    Path("data").mkdir(exist_ok=True)
    pred.to_csv("data/prediccion_v2.csv", index=False)

    n_v2 = int((pred["metodo_v2"] == "v2_minutos").sum())
    n_v1 = int((pred["metodo_v2"] == "v1_fallback").sum())
    print(f"  PPM clipados (actual): {n_clip_act}")
    print(f"  PPM clipados (histórico): {n_clip_hist}")
    print(f"  Anclas por posición: {anchor_pos}")
    print(f"  Modelo v2: {n_v2} jugadores")
    print(f"  Fallback v1: {n_v1} jugadores")
    print(f"  Guardado: data/prediccion_v2.csv")

    # ─── Comparativa v1 vs v2 ───────────────────────────────
    pred["dif_v2_v1"] = pred["puntos_esperados_v2"] - pred["puntos_esperados_J2"]
    cols = ["shortName", "nameTeam", "position", "price",
            "puntos_esperados_J2", "minutos_esperados", "ppm_esperado",
            "puntos_esperados_v2", "dif_v2_v1"]

    print("\n  Top 10 que MÁS suben con v2:")
    print(pred.nlargest(10, "dif_v2_v1")[cols].round(2).to_string(index=False))

    print("\n  Top 10 que MÁS bajan con v2:")
    print(pred.nsmallest(10, "dif_v2_v1")[cols].round(2).to_string(index=False))

    print("\n  Distribución de diferencias v2 - v1:")
    print(pred["dif_v2_v1"].describe().round(2).to_string())


if __name__ == "__main__":
    main()