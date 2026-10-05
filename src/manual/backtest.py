"""
backtest.py — Backtest del modelo sobre la temporada 2025-26.

Salidas:
  data/backtest_resumen.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

MIN_PRIOR = 5
SUAVIZADOS = [2, 3, 4, 6, 8]
BLENDS = np.round(np.arange(0, 1.001, 0.05), 2)


def cargar():
    df = pd.read_csv("data/historico/2025-26/stats_jornada.csv")
    df = df[df["valueTimePlayed"] > 0].copy()
    df["minutos"] = df["valueTimePlayed"] / 60.0
    df["ppm"] = df["pointsJourney"] / df["minutos"]
    df = df.sort_values(["idPlayer", "numberJourney"]).reset_index(drop=True)

    counts = df.groupby("idPlayer").size()
    validos = counts[counts >= MIN_PRIOR + 1].index
    df = df[df["idPlayer"].isin(validos)].copy()
    return df


def backtest(df, suavizado):
    filas = []
    for id_p, grupo in df.groupby("idPlayer"):
        grupo = grupo.sort_values("numberJourney").reset_index(drop=True)
        n = len(grupo)

        prior = grupo.iloc[:MIN_PRIOR]
        p_pts = prior["pointsJourney"].mean()
        p_ppm = prior["ppm"].mean()
        p_min = prior["minutos"].mean()
        v2_prior = p_ppm * p_min

        cur_pts = []
        cur_ppm = []
        cur_min = []

        for i in range(MIN_PRIOR, n):
            actual = grupo.loc[i, "pointsJourney"]
            jornada = grupo.loc[i, "numberJourney"]

            if len(cur_pts) == 0:
                v1 = p_pts
                v2 = v2_prior
            else:
                w = len(cur_pts) / (len(cur_pts) + suavizado)
                v1 = w * np.mean(cur_pts) + (1 - w) * p_pts
                v2 = (
                    w * (np.mean(cur_ppm) * np.mean(cur_min))
                    + (1 - w) * v2_prior
                )

            filas.append({
                "idPlayer": id_p,
                "jornada": jornada,
                "actual": actual,
                "v1": v1,
                "v2": v2,
            })

            cur_pts.append(grupo.loc[i, "pointsJourney"])
            cur_ppm.append(grupo.loc[i, "ppm"])
            cur_min.append(grupo.loc[i, "minutos"])

    return pd.DataFrame(filas)


def evaluar(df_pred, blends):
    filas = []
    for w in blends:
        pred = (1 - w) * df_pred["v1"] + w * df_pred["v2"]
        err = pred - df_pred["actual"]
        filas.append({
            "peso_v2": w,
            "mae": err.abs().mean(),
            "rmse": np.sqrt((err ** 2).mean()),
            "corr": df_pred["actual"].corr(pred),
            "sesgo": err.mean(),
        })
    return pd.DataFrame(filas)


def main():
    print("  Cargando datos de 2025-26...")
    df = cargar()
    print(f"  Jugadores: {df['idPlayer'].nunique()}")
    print(f"  Partidos: {len(df)}")

    todos = []
    for s in SUAVIZADOS:
        print(f"\n  Backtest con SUAVIZADO = {s}...")
        pred = backtest(df, s)
        res = evaluar(pred, BLENDS)
        res["suavizado"] = s
        todos.append(res)

    resumen = pd.concat(todos, ignore_index=True)
    resumen.to_csv("data/procesado/backtest_resumen.csv", index=False)

    best = resumen.loc[resumen["mae"].idxmin()]
    print("\n  === MEJOR COMBINACIÓN ===")
    print(f"  peso_v2 = {best['peso_v2']:.2f}")
    print(f"  SUAVIZADO = {int(best['suavizado'])}")
    print(f"  MAE = {best['mae']:.3f}")
    print(f"  RMSE = {best['rmse']:.3f}")
    print(f"  Correlación = {best['corr']:.3f}")
    print(f"  Sesgo = {best['sesgo']:+.3f}")

    print(f"\n  Guardado: data/backtest_resumen.csv")


if __name__ == "__main__":
    main()