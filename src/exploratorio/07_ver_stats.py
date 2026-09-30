import glob
import json

# Abre la captura más reciente
archivo = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo, encoding="utf-8") as f:
    jugadores = json.load(f)

con_stats = [j for j in jugadores if j.get("playerStats")]
print("Captura:", archivo)
print("Jugadores con estadísticas:", len(con_stats), "de", len(jugadores))

j = con_stats[0]
print("\nEjemplo:", j["shortName"], "-", j["nameTeam"])
print(json.dumps(j["playerStats"], indent=2, ensure_ascii=False)[:2500])