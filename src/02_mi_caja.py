import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

import config

load_dotenv()
token = os.getenv("SM_TOKEN")
if not token:
    raise SystemExit("No encuentro SM_TOKEN en el archivo .env")
if not token.startswith("Bearer "):
    token = "Bearer " + token

URL = "https://supermanager.acb.com/api/basic/userteam/all"
resp = requests.get(URL, headers={"Authorization": token, "Accept": "application/json"}, timeout=30)
resp.raise_for_status()

mi_equipo = None
for competicion in resp.json():
    for equipo in competicion.get("userTeamList", []):
        if equipo.get("idUserTeam") == config.MI_EQUIPO_ID:
            mi_equipo = equipo
            break
    if mi_equipo:
        break

if mi_equipo is None:
    raise SystemExit(f"No encuentro el equipo {config.MI_EQUIPO_ID} en /userteam/all")

info = {
    "idUserTeam": mi_equipo["idUserTeam"],
    "nameTeam": mi_equipo.get("nameTeam"),
    "amount": float(mi_equipo.get("amount", 0.0)),
    "brokerValor": float(mi_equipo.get("brokerValor", 0.0)),
    "totalPlayerPoints": float(mi_equipo.get("totalPlayerPoints", 0.0)),
    "position": mi_equipo.get("position"),
    "brokerPosition": mi_equipo.get("brokerPosition"),
    "idUserLeague": mi_equipo.get("idUserLeague"),
    "username": mi_equipo.get("username"),
}

Path("data/mi_equipo").mkdir(parents=True, exist_ok=True)
with open("data/mi_equipo/caja.json", "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print(f"  Equipo: {info['nameTeam']} | Caja: {info['amount']:,.0f} EUR | Valor: {info['brokerValor']:,.0f} EUR")