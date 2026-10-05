"""
10b_guardar_stats.py

Descarga el desglose completo de estadísticas por jornada de todos los
jugadores del mercado actual y lo acumula en un CSV histórico con el
mismo formato que stats_jornada.csv de Ivo.

Entradas:
  data/procesado/prediccion_global.csv    (lista de jugadores del mercado)
  data/raw/mercado_*.json                 (para jugadores.csv)

Salidas:
  data/historico/<TEMPORADA>/stats_jornada.csv   (acumulativo)
  data/historico/<TEMPORADA>/jugadores.csv       (se sobrescribe)

Uso:
  python src/10b_guardar_stats.py
"""
import glob
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# ─── Configuración ──────────────────────────────────────────
TEMPORADA = "2026-27"
ARCHIVO = Path(f"data/historico/{TEMPORADA}/stats_jornada.csv")
PAUSA = 0.4
MAX_JUGADORES = config.MAX_JUGADORES_STATS

COLS = [
    "idPlayer", "shortName", "nick", "license", "idTeam", "nameTeam",
    "playerPrice", "initialPrice", "price",
    "idJourney", "pointsJourney", "numberJourney", "bonusVictory",
    "valueTimePlayed", "pointsTimePlayed",
    "valuePoints", "pointsPoints",
    "valueT2", "pointsT2",
    "valueT3", "pointsT3",
    "valueTL", "pointsTL",
    "valueRebounds", "pointsRebounds",
    "valueAssists", "pointsAssists",
    "valueSteals", "pointsSteals",
    "valueTurnover", "pointsTurnover",
    "valueBlocks", "pointsBlocks",
    "valueBlocksAgainst", "pointsBlocksAgainst",
    "valueFoul", "pointsFoul",
    "valueFoulReceived", "pointsFoulReceived",
    "photo", "number",
]


def extraer_filas(idPlayer, data):
    """Extrae las filas de jornadas jugadas de un jugador."""
    filas = []
    for e in data.get("playerStats", []):
        if "idJourney" not in e or "pointsJourney" not in e:
            continue
        filas.append({
            "idPlayer": idPlayer,
            "shortName": data.get("shortName"),
            "nick": data.get("nick"),
            "license": data.get("license"),
            "idTeam": data.get("idTeam"),
            "nameTeam": data.get("nameTeam"),
            "playerPrice": e.get("playerPrice"),
            "initialPrice": data.get("initialPrice"),
            "price": data.get("price"),
            "idJourney": e.get("idJourney"),
            "pointsJourney": e.get("pointsJourney"),
            "numberJourney": e.get("numberJourney"),
            "bonusVictory": e.get("bonusVictory"),
            "valueTimePlayed": e.get("valueTimePlayed"),
            "pointsTimePlayed": e.get("pointsTimePlayed"),
            "valuePoints": e.get("valuePoints"),
            "pointsPoints": e.get("pointsPoints"),
            "valueT2": e.get("valueT2"),
            "pointsT2": e.get("pointsT2"),
            "valueT3": e.get("valueT3"),
            "pointsT3": e.get("pointsT3"),
            "valueTL": e.get("valueTL"),
            "pointsTL": e.get("pointsTL"),
            "valueRebounds": e.get("valueRebounds"),
            "pointsRebounds": e.get("pointsRebounds"),
            "valueAssists": e.get("valueAssists"),
            "pointsAssists": e.get("pointsAssists"),
            "valueSteals": e.get("valueSteals"),
            "pointsSteals": e.get("pointsSteals"),
            "valueTurnover": e.get("valueTurnover"),
            "pointsTurnover": e.get("pointsTurnover"),
            "valueBlocks": e.get("valueBlocks"),
            "pointsBlocks": e.get("pointsBlocks"),
            "valueBlocksAgainst": e.get("valueBlocksAgainst"),
            "pointsBlocksAgainst": e.get("pointsBlocksAgainst"),
            "valueFoul": e.get("valueFoul"),
            "pointsFoul": e.get("pointsFoul"),
            "valueFoulReceived": e.get("valueFoulReceived"),
            "pointsFoulReceived": e.get("pointsFoulReceived"),
            "photo": data.get("photo"),
            "number": data.get("number"),
        })
    return filas


def guardar_jugadores():
    """Guarda data/historico/<TEMPORADA>/jugadores.csv desde el mercado actual.
    Se sobrescribe cada ejecución → al final de temporada refleja el estado final."""
    archivo_mercado = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
    with open(archivo_mercado, encoding="utf-8") as f:
        mercado = json.load(f)

    filas = []
    for j in mercado:
        ultima = None
        for e in j.get("playerStats", []):
            if e.get("pointsJourney") is not None:
                ultima = e
        filas.append({
            "idPlayer": j.get("idPlayer"),
            "acbIdPlayer": j.get("acbIdPlayer"),
            "fullName": j.get("fullName"),
            "shortName": j.get("shortName"),
            "nick": j.get("nick"),
            "birthdate": j.get("birthdate"),
            "age": j.get("age"),
            "height": j.get("height"),
            "nationality": j.get("nationality"),
            "birthplace": j.get("birthplace"),
            "idTeam": j.get("idTeam"),
            "nameTeam": j.get("nameTeam"),
            "imageTeam": j.get("imageTeam"),
            "position": j.get("position"),
            "license": j.get("license"),
            "isExtraCommunity": j.get("isExtraCommunity"),
            "isNational": j.get("isNational"),
            "isActive": j.get("isActive"),
            "isExitLeague": j.get("isExitLeague"),
            "injuredDays": j.get("injuredDays"),
            "fisicStatus": j.get("fisicStatus"),
            "price": j.get("price"),
            "initialPrice": j.get("initialPrice"),
            "competitionAverage": j.get("competitionAverage"),
            "numberJourney": ultima["numberJourney"] if ultima else None,
            "pointsJourney": ultima["pointsJourney"] if ultima else None,
            "photo": j.get("photo"),
            "number": j.get("number"),
        })

    ruta = ARCHIVO.parent / "jugadores.csv"
    pd.DataFrame(filas).to_csv(ruta, index=False)
    print(f"  Guardado: {ruta} ({len(filas)} jugadores)")


def main():
    load_dotenv()
    token = os.getenv("SM_TOKEN")
    if not token:
        raise SystemExit("No encuentro SM_TOKEN en el archivo .env")
    if not token.startswith("Bearer "):
        token = "Bearer " + token

    headers = {"Authorization": token, "Accept": "application/json"}

    pred = pd.read_csv("data/procesado/prediccion_global.csv")
    jugadores = pred[["idPlayer", "shortName"]].drop_duplicates()
    if MAX_JUGADORES > 0:
        jugadores = jugadores.head(MAX_JUGADORES)
    print(f"  Jugadores a procesar: {len(jugadores)}")

    if ARCHIVO.exists():
        df_hist = pd.read_csv(ARCHIVO)
        print(f"  Histórico existente: {len(df_hist)} filas")
    else:
        df_hist = pd.DataFrame(columns=COLS)
        ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
        print("  Histórico nuevo")

    filas_nuevas = []
    errores = []

    for i, (_, r) in enumerate(jugadores.iterrows(), 1):
        id_p = int(r["idPlayer"])
        url = f"https://supermanager.acb.com/api/basic/playerstats/1/{id_p}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                errores.append((r["shortName"], f"HTTP {resp.status_code}"))
                continue
            data = resp.json()
            filas_nuevas.extend(extraer_filas(id_p, data))
            if i % 25 == 0:
                print(f"    {i}/{len(jugadores)} ({len(filas_nuevas)} filas)")
            time.sleep(PAUSA)
        except Exception as e:
            errores.append((r["shortName"], str(e)[:80]))
            continue

    if filas_nuevas:
        df_nuevas = pd.DataFrame(filas_nuevas)
        df_final = pd.concat([df_hist, df_nuevas], ignore_index=True)
        df_final = df_final.drop_duplicates(
            subset=["idPlayer", "numberJourney"], keep="last"
        )
        df_final = df_final.sort_values(["idPlayer", "numberJourney"]).reset_index(drop=True)
        df_final.to_csv(ARCHIVO, index=False)

        print(f"\n  Guardado: {ARCHIVO}")
        print(f"  Filas totales: {len(df_final)}")
        print(f"  Jugadores: {df_final['idPlayer'].nunique()}")
        print(f"  Jornadas: {sorted(df_final['numberJourney'].unique())}")
    else:
        print("  No se extrajo ninguna fila nueva.")

    # Guardar también la ficha de jugadores
    guardar_jugadores()

    if errores:
        print(f"\n  Errores ({len(errores)}):")
        for nombre, err in errores[:15]:
            print(f"    {nombre}: {err}")


if __name__ == "__main__":
    main()