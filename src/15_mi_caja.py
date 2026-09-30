"""
Lee el dinero en caja, el nombre del equipo, el valor y la posición
desde /api/basic/userteam/all.

Salida: data/mi_equipo/caja.json
"""
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
headers = {"Authorization": token, "Accept": "application/json"}

resp = requests.get(URL, headers=headers, timeout=30)
resp.raise_for_status()
data = resp.json()

# data es una lista (una entrada por competición). Buscamos nuestro equipo.
mi_equipo = None
for competicion in data:
    for equipo in competicion.get("userTeamList", []):
        if equipo.get("idUserTeam") == config.MI_EQUIPO_ID:
            mi_equipo = equipo
            break
    if mi_equipo:
        break

if mi_equipo is None:
    raise SystemExit(
        f"No encuentro el equipo {config.MI_EQUIPO_ID} en la respuesta. "
        "¿Está bien el ID en config.py?"
    )

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

print(f"Equipo: {info['nameTeam']} ({info['idUserTeam']})")
print(f"Caja:   {info['amount']:,.0f} €")
print(f"Valor:  {info['brokerValor']:,.0f} €")
print(f"Puntos: {info['totalPlayerPoints']}")
print(f"Posición general: {info['position']}")
print(f"Posición broker:  {info['brokerPosition']}")
print(f"\nGuardado en data/mi_equipo/caja.json")