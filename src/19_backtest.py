"""
19_backtest.py

Backtest del modelo sobre la temporada 2025-26 usando stats_jornada_2526.csv.

Para cada jugador y cada jornada J (desde MIN_PRIOR+1):
  - "prior"   = primeros MIN_PRIOR partidos (simula el histórico)
  - "current" = partidos MIN_PRIOR..J-1
  - v1 = W * media_pts_current + (1-W) * media_pts_prior
  - v2 = W * (media_ppm_current * media_min_current)
       + (1-W) * (media_ppm_prior * media_min_prior)
  - Compara con lo que hizo en J.

Prueba distintos pesos de blend y distintos SUAVIZADO.
Recomienda el blend con menor MAE.

Salidas:
  data/backtest_resumen.csv         (métricas por blend)
  data/backtest_resumen_suav.csv    (métricas por blend y suavizado)
"""
import numpy as np
import pandas as pd


# ─── Parámetros ─────────────────────────────────────────────
MIN_PRIOR = 5                          # partidos iniciales = "histórico"
SUAVIZADOS = [2, 3, 4, 6, 8]           # valores a probar
BLENDS = np.round(np.arange(0, 1.001, 0.05), 2)


def cargar():
    df = pd.read_csv("data/stats_jornada_2526.csv")
    df = df[df["valueTimePlayed"] > 0].copy()
    df["minutos"] = df["valueTimePlayed"] / 60.0
    df["ppm"] = df["pointsJourney"] / df["minutos"]
    df = df.sort_values(["idPlayer", "numberJourney"]).reset_index(drop=True)

    # Solo jugadores con al menos MIN_PRIOR+1 partidos
    counts = df.groupby("idPlayer").size()
    validos = counts[counts >= MIN_PRIOR + 1].index
    df = df[df["idPlayer"].isin(validos)].copy()
    return df


def backtest(df, suavizado):
    """Devuelve un DataFrame con idPlayer, jornada, actual, v1, v2."""
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
    """Devuelve un DataFrame con métricas por peso de blend."""
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
    resumen.to_csv("data/backtest_resumen.csv", index=False)

    # Mejor combinación global
    best = resumen.loc[resumen["mae"].idxmin()]
    print("\n  === MEJOR COMBINACIÓN ===")
    print(f"  peso_v2 = {best['peso_v2']:.2f}")
    print(f"  SUAVIZADO = {int(best['suavizado'])}")
    print(f"  MAE = {best['mae']:.3f}")
    print(f"  RMSE = {best['rmse']:.3f}")
    print(f"  Correlación = {best['corr']:.3f}")
    print(f"  Sesgo = {best['sesgo']:+.3f}")

    # Comparativa resumida con el mejor SUAVIZADO
    mejor_suav = int(best["suavizado"])
    print(f"\n  === Comparativa con SUAVIZADO = {mejor_suav} ===")
    sub = resumen[resumen["suavizado"] == mejor_suav].sort_values("peso_v2")
    print(f"  {'peso_v2':>8} {'MAE':>8} {'RMSE':>8} {'Corr':>8} {'Sesgo':>8}")
    for _, r in sub.iterrows():
        marca = " <-" if abs(r["peso_v2"] - best["peso_v2"]) < 1e-6 else ""
        print(f"  {r['peso_v2']:>8.2f} {r['mae']:>8.3f} {r['rmse']:>8.3f} "
              f"{r['corr']:>8.3f} {r['sesgo']:>+8.3f}{marca}")

    # Comparativa de SUAVIZADO con el mejor blend
    mejor_peso = best["peso_v2"]
    print(f"\n  === Comparativa con peso_v2 = {mejor_peso:.2f} ===")
    sub2 = resumen[np.isclose(resumen["peso_v2"], mejor_peso)].sort_values("suavizado")
    print(f"  {'SUAVIZADO':>10} {'MAE':>8} {'RMSE':>8} {'Corr':>8}")
    for _, r in sub2.iterrows():
        print(f"  {int(r['suavizado']):>10d} {r['mae']:>8.3f} {r['rmse']:>8.3f} {r['corr']:>8.3f}")

    print(f"\n  Guardado: data/backtest_resumen.csv")
    print(f"\n  SUGERENCIA para config.py:")
    print(f"    SUAVIZADO_JORNADAS = {mejor_suav}")
    print(f"    PESO_V2_INICIAL = {mejor_peso:.2f}")


if __name__ == "__main__":
    main()