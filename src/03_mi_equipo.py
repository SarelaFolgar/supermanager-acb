import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

import config

load_dotenv()
token = os.getenv("SM_TOKEN")
if not token:
    raise SystemExit("No encuentro SM_TOKEN en el archivo .env")
if not token.startswith("Bearer "):
    token = "Bearer " + token

URL = f"https://supermanager.acb.com/api/basic/userteamplayer/journeys/{config.MI_EQUIPO_ID}"
resp = requests.get(URL, headers={"Authorization": token, "Accept": "application/json"}, timeout=30)
resp.raise_for_status()
data = resp.json()

j1 = next(j for j in data if j["number"] == 1)
j2 = next(j for j in data if j["number"] == 2)

filas = []
for p in j2["playerList"]:
    filas.append({
        "idPlayer": p["idPlayer"],
        "shortName": p["shortName"],
        "fullName": p["fullName"],
        "nameTeam": p["nameTeam"],
        "position": p["position"],
        "initialPrice": p["initialPrice"],
        "fisicStatus": p["fisicStatus"],
        "injuredDays": p["injuredDays"],
        "isExtraCommunity": p["isExtraCommunity"],
        "license": p["license"],
        "isNational": p["isNational"],
        "prox_rival_logo": p.get("team"),
        "prox_local": p.get("isLocal"),
    })
df_plantilla = pd.DataFrame(filas)

logos = pd.read_csv("data/procesado/equipos_logos.csv").set_index("logo")["equipo"].to_dict()
df_plantilla["rival"] = (
    df_plantilla["prox_rival_logo"].map(logos).fillna(df_plantilla["prox_rival_logo"])
)

Path("data/mi_equipo").mkdir(parents=True, exist_ok=True)
df_plantilla.to_csv("data/mi_equipo/plantilla_actual.csv", index=False)

print(f"  Plantilla: {len(df_plantilla)} jugadores | "
      f"{df_plantilla['isExtraCommunity'].sum()} EXT | "
      f"{df_plantilla['isNational'].sum()} locales")