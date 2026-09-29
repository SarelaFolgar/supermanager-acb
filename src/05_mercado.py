import json
import os

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
print("Status:", resp.status_code)
if resp.status_code != 200:
    raise SystemExit("Fallo. Si es 401 o 403, el token ha caducado: repite el paso de copiarlo.")

data = resp.json()
print("Tipo:", type(data).__name__)
if isinstance(data, dict):
    print("Claves:", list(data.keys()))
    for k, v in data.items():
        if isinstance(v, list) and v:
            print(f"Lista '{k}':", len(v), "elementos")
            print("Claves del primer elemento:", list(v[0].keys()))
else:
    print("Elementos:", len(data))
    print("Claves del primer elemento:", list(data[0].keys()))