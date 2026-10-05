from pathlib import Path

import numpy as np
import pandas as pd

import config

PPM_MIN = 0.0
PPM_MAX = 1.2
K_SHRINK = 4


def main():
    pred = pd.read_csv("data/procesado/prediccion_con_minutos.csv")
    stats = pd.read_csv("data/historico/2025-26/stats_jornada.csv")

    stats = stats[stats["valueTimePlayed"] > 0].copy()
    stats["minutos"] = stats["valueTimePlayed"] / 60.0

    hist = stats.groupby("idPlayer").agg(
        minutos_hist_tot=("minutos", "sum"),
        puntos_hist_tot=("pointsJourney", "sum"),
    ).reset_index()
    hist["ppm_hist_sin_bonus"] = hist["puntos_hist_tot"] / hist["minutos_hist_tot"]
    hist = hist.rename(columns={"idPlayer": "idPlayer_2526"})

    pred = pred.merge(
        hist[["idPlayer_2526", "ppm_hist_sin_bonus"]],
        on="idPlayer_2526", how="left",
    )

    pred["ppm_actual_sin_bonus"] = np.where(
        pred["minutos_medios"] > 0,
        pred["val_medios"] / pred["minutos_medios"],
        np.nan,
    )

    pred["ppm_actual_sin_bonus"] = pred["ppm_actual_sin_bonus"].clip(PPM_MIN, PPM_MAX)
    pred["ppm_hist_sin_bonus"] = pred["ppm_hist_sin_bonus"].clip(PPM_MIN, PPM_MAX)

    pred["ppm_combined"] = pred["ppm_hist_sin_bonus"].fillna(pred["ppm_actual_sin_bonus"])
    anchor_pos = pred.groupby("position")["ppm_combined"].median().to_dict()

    n_part = pred["partidos_rincon"].fillna(0)
    ancla = pred["position"].map(anchor_pos).fillna(0.5)
    pred["ppm_actual_ajustado"] = (
        pred["ppm_actual_sin_bonus"].fillna(0) * n_part + ancla * K_SHRINK
    ) / (n_part + K_SHRINK)

    W = pred["W"]
    tiene_hist = pred["minutos_2526"].notna() & (pred["minutos_2526"] > 0)
    tiene_actual = pred["minutos_medios"].notna() & (pred["minutos_medios"] > 0)
    tiene_ppm_hist = pred["ppm_hist_sin_bonus"].notna()

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

    pred["puntos_esperados_v2"] = (
        pred["ppm_esperado"] * pred["minutos_esperados"]
        * (1 + 0.2 * pred["p_win_J2"])
    )

    sin_datos = pred["puntos_esperados_v2"].isna()
    pred.loc[sin_datos, "puntos_esperados_v2"] = pred.loc[sin_datos, "puntos_esperados_J2"]
    pred["metodo_v2"] = np.where(sin_datos, "v1_fallback", "v2_minutos")

    Path("data/procesado").mkdir(parents=True, exist_ok=True)
    pred.to_csv("data/procesado/prediccion_v2.csv", index=False)

    n_v2 = (pred["metodo_v2"] == "v2_minutos").sum()
    n_v1 = (pred["metodo_v2"] == "v1_fallback").sum()
    print(f"  Modelo v2 (minutos): {n_v2} jugadores")
    print(f"  Fallback v1 (sin minutos): {n_v1} jugadores")
    print(f"  Guardado: data/procesado/prediccion_v2.csv")


if __name__ == "__main__":
    main()