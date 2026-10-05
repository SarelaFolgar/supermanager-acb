"""
10_guardar_predicciones.py

Guarda cada ejecución en un histórico persistente para poder hacer
análisis de calibración y backtests de decisión en el futuro.

Lógica:
  1. Guarda las predicciones actuales (dedupe por jornada+jugador).
  2. Rellena "actual_*" para la jornada más reciente ya jugada.

Salida: data/historico/<TEMPORADA>/predicciones.csv
"""
import glob
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

TEMPORADA = "2026-27"
ARCHIVO = Path(f"data/historico/{TEMPORADA}/predicciones.csv")


def cargar_mercado():
    archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
    with open(archivo, encoding="utf-8") as f:
        return json.load(f)


def indexar_actuales(mercado):
    idx = {}
    for j in mercado:
        id_p = j["idPlayer"]
        idx[id_p] = {"price": j["price"], "pts": {}}
        for e in j.get("playerStats", []):
            n = e.get("numberJourney")
            p = e.get("pointsJourney")
            if n is not None and p is not None:
                idx[id_p]["pts"][n] = p
    return idx


def main():
    pred = pd.read_csv("data/procesado/prediccion_global.csv")
    mercado = cargar_mercado()
    actuales = indexar_actuales(mercado)

    j_actual = int(pred["partidos_actual"].max())
    jornada_objetivo = j_actual + 1
    ahora = datetime.now().isoformat(timespec="seconds")

    nuevas = []
    for _, r in pred.iterrows():
        nuevas.append({
            "season": TEMPORADA,
            "jornada": jornada_objetivo,
            "idPlayer": r["idPlayer"],
            "shortName": r["shortName"],
            "nameTeam": r["nameTeam"],
            "position": r["position"],
            "price_before": r["price"],
            "pts_esp": r.get("puntos_esperados_J2"),
            "p_up15": r.get("p_sube_15"),
            "p_down15": r.get("p_baja_15"),
            "reval_euros": r.get("reval_euros"),
            "umbral_sube_15": r.get("umbral_sube_15"),
            "umbral_baja_15": r.get("umbral_baja_15"),
            "actual_rating": None,
            "actual_price": None,
            "actual_up15": None,
            "actual_down15": None,
            "predicted_at": ahora,
            "actual_filled_at": None,
        })
    df_nuevas = pd.DataFrame(nuevas)

    if ARCHIVO.exists():
        df = pd.read_csv(ARCHIVO)
    else:
        ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame()

    # Dedupe: eliminar filas antiguas de esta jornada y añadir las nuevas
    if not df.empty:
        df = df[~((df["season"] == TEMPORADA) & (df["jornada"] == jornada_objetivo))]
    df = pd.concat([df, df_nuevas], ignore_index=True)

    # Rellenar actuals de la jornada más reciente ya jugada
    pendientes = df[(df["actual_rating"].isna()) & (df["jornada"] == j_actual)]
    n_rellenos = 0
    for idx, fila in pendientes.iterrows():
        id_p = fila["idPlayer"]
        info = actuales.get(id_p)
        if not info or j_actual not in info["pts"]:
            continue
        df.at[idx, "actual_rating"] = info["pts"][j_actual]
        df.at[idx, "actual_price"] = info["price"]
        pb = fila["price_before"]
        if pb and pb > 0:
            ratio = info["price"] / pb
            df.at[idx, "actual_up15"] = int(ratio >= 1.15)
            df.at[idx, "actual_down15"] = int(ratio <= 0.85)
        df.at[idx, "actual_filled_at"] = ahora
        n_rellenos += 1

    df.to_csv(ARCHIVO, index=False)

    con_actual = int(df["actual_rating"].notna().sum())
    print(f"  Historico: {len(df)} filas | "
          f"{con_actual} con actual | "
          f"{n_rellenos} rellenos ahora")
    print(f"  Guardado: {ARCHIVO}")


if __name__ == "__main__":
    main()