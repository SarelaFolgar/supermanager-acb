"""
17_minutos_features.py — Cruza los minutos reales (El Rincón) con las
predicciones del modelo.

Entrada:
  data/rincon/minutos_actual.csv      (generado por 16_rincon_scraper.py)
  data/prediccion_global.csv          (generado por 13_prediccion_global.py)

Salida:
  data/prediccion_con_minutos.csv
"""
from pathlib import Path

import pandas as pd


def main():
    rincon = pd.read_csv("data/rincon/minutos_actual.csv")
    pred = pd.read_csv("data/prediccion_global.csv")

    # Agrupar por jugador
    rincon = rincon.dropna(subset=["minutos"]).copy()

    agg = rincon.groupby("idPlayer").agg(
        partidos_rincon=("jornada", "count"),
        minutos_medios=("minutos", "mean"),
        minutos_max=("minutos", "max"),
        minutos_min=("minutos", "min"),
        sm_medios=("sm", "mean"),
        val_medios=("valoracion", "mean"),
        puntos_medios=("puntos", "mean"),
    ).reset_index()

    # Último partido (jornada más alta)
    ultimo = (
        rincon.sort_values("jornada")
        .groupby("idPlayer")
        .tail(1)[["idPlayer", "jornada", "minutos"]]
        .rename(columns={"jornada": "ultima_jornada", "minutos": "minutos_ultimo"})
    )
    agg = agg.merge(ultimo, on="idPlayer", how="left")

    # Tendencias y ratios
    agg["minutos_tendencia"] = agg["minutos_ultimo"] - agg["minutos_medios"]
    agg["ppm_sm"] = agg["sm_medios"] / agg["minutos_medios"]
    agg["ppm_val"] = agg["val_medios"] / agg["minutos_medios"]

    # Cruce con predicciones
    df = pred.merge(agg, on="idPlayer", how="left")

    # Para los jugadores sin datos de El Rincón, dejamos NaN
    sin_minutos = df["minutos_medios"].isna().sum()
    print(f"  Jugadores con minutos: {df['minutos_medios'].notna().sum()} / {len(df)}")
    print(f"  Sin datos de El Rincón: {sin_minutos} (recién llegados o sin jugar)")

    # Guardar
    Path("data").mkdir(exist_ok=True)
    df.to_csv("data/prediccion_con_minutos.csv", index=False)
    print(f"  Guardado: data/prediccion_con_minutos.csv ({len(df)} jugadores)")


if __name__ == "__main__":
    main()