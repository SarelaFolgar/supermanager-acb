"""
mapeo_equipos.py — Genera data/equipos_logos.csv desde la última
captura del mercado. Se ejecuta a mano cuando cambien los equipos.
"""
import glob
import json
from pathlib import Path

import pandas as pd

archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo, encoding="utf-8") as f:
    jugadores = json.load(f)

pares = {}
for j in jugadores:
    logo = j.get("imageTeam")
    equipo = j.get("nameTeam")
    if logo and equipo:
        pares[logo] = equipo

df = pd.DataFrame(sorted(pares.items()), columns=["logo", "equipo"])
Path("data").mkdir(exist_ok=True)
df.to_csv("data/equipos_logos.csv", index=False)

print(f"Guardados {len(df)} equipos en data/equipos_logos.csv")
print(df.to_string(index=False))