from pathlib import Path

import pandas as pd


def main():
    rincon = pd.read_csv("data/rincon/minutos_actual.csv")
    pred = pd.read_csv("data/procesado/prediccion_global.csv")

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

    ultimo = (
        rincon.sort_values("jornada")
        .groupby("idPlayer")
        .tail(1)[["idPlayer", "jornada", "minutos"]]
        .rename(columns={"jornada": "ultima_jornada", "minutos": "minutos_ultimo"})
    )
    agg = agg.merge(ultimo, on="idPlayer", how="left")

    agg["minutos_tendencia"] = agg["minutos_ultimo"] - agg["minutos_medios"]
    agg["ppm_sm"] = agg["sm_medios"] / agg["minutos_medios"]
    agg["ppm_val"] = agg["val_medios"] / agg["minutos_medios"]

    df = pred.merge(agg, on="idPlayer", how="left")

    sin_minutos = df["minutos_medios"].isna().sum()
    print(f"  Jugadores con minutos: {df['minutos_medios'].notna().sum()} / {len(df)}")
    print(f"  Sin datos de El Rincón: {sin_minutos} (recién llegados o sin jugar)")

    Path("data/procesado").mkdir(parents=True, exist_ok=True)
    df.to_csv("data/procesado/prediccion_con_minutos.csv", index=False)
    print(f"  Guardado: data/procesado/prediccion_con_minutos.csv ({len(df)} jugadores)")


if __name__ == "__main__":
    main()