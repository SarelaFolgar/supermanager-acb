import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("SM_TOKEN")
if not token:
    raise SystemExit("No encuentro SM_TOKEN en el archivo .env")
if not token.startswith("Bearer "):
    token = "Bearer " + token

URL = "https://supermanager.acb.com/api/basic/player"
filtros = [
    {"field": "competition.idCompetition", "value": 1, "operator": "=", "condition": "AND"},
    {"field": "edition.isActive", "value": True, "operator": "=", "condition": "AND"},
]
orden = [{"field": "price", "type": "DESC"}]
params = {
    "_filters": json.dumps(filtros, separators=(",", ":")),
    "_page": 1,
    "_perPage": 30,
    "_sort": json.dumps(orden, separators=(",", ":")),
}
headers = {"Authorization": token, "Accept": "application/json"}

resp = requests.get(URL, params=params, headers=headers, timeout=30)
resp.raise_for_status()
jugadores = resp.json()

# Un snapshot por día: sobrescribe el de hoy si ya existe
hoy = datetime.now().strftime("%Y-%m-%d")
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/mercado").mkdir(parents=True, exist_ok=True)

ruta_json = f"data/raw/mercado_{hoy}.json"
ruta_csv = f"data/mercado/mercado_{hoy}.csv"

with open(ruta_json, "w", encoding="utf-8") as f:
    json.dump(jugadores, f, ensure_ascii=False)

df = pd.json_normalize(jugadores)
df = df[[c for c in df.columns if not c.startswith("playerStats")]]
df.insert(0, "captura", hoy)
df.to_csv(ruta_csv, index=False)

print(f"Guardados {len(df)} jugadores en {ruta_csv}")
cols = ["shortName", "nameTeam", "position", "price", "injuredDays", "fisicStatus", "competitionAverage"]
print(df[cols].head(10).to_string(index=False))