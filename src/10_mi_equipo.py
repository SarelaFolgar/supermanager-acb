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
headers = {"Authorization": token, "Accept": "application/json"}

resp = requests.get(URL, headers=headers, timeout=30)
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

# Mapear logo del rival → nombre de equipo
logos = pd.read_csv("data/equipos_logos.csv").set_index("logo")["equipo"].to_dict()
df_plantilla["rival"] = (
    df_plantilla["prox_rival_logo"]
    .map(logos)
    .fillna(df_plantilla["prox_rival_logo"])
)

filas_j1 = []
for p in j1["playerList"]:
    filas_j1.append({
        "idPlayer": p["idPlayer"],
        "shortName": p["shortName"],
        "nameTeam": p["nameTeam"],
        "position": p["position"],
        "journeyPoints": p.get("journeyPoints"),
    })
df_j1 = pd.DataFrame(filas_j1)

Path("data/mi_equipo").mkdir(parents=True, exist_ok=True)
df_plantilla.to_csv("data/mi_equipo/plantilla_actual.csv", index=False)
df_j1.to_csv("data/mi_equipo/jornada_1_puntos.csv", index=False)

print("=== PLANTILLA ACTUAL ===")
print(df_plantilla[["shortName", "nameTeam", "position", "initialPrice",
                    "fisicStatus", "injuredDays", "isExtraCommunity"]].to_string(index=False))

print("\n=== PUNTOS J1 ===")
print(df_j1[["shortName", "nameTeam", "position", "journeyPoints"]].to_string(index=False))

print("\n=== CUPOS ===")
extra = df_plantilla["isExtraCommunity"].sum()
nacionales = df_plantilla["isNational"].sum()
print(f"Extracomunitarios: {extra} / {config.MAX_EXTRA}")
print(f"Formados localmente: {nacionales} / mínimo {config.MIN_LOCALES}")

print("\n=== PRÓXIMO RIVAL ===")
for _, r in df_plantilla.iterrows():
    local = "Local" if r["prox_local"] else "Visitante"
    print(f"{r['shortName']:20s} vs {r['rival']:35s} ({local})")