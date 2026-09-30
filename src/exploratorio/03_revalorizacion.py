import pandas as pd

stats = pd.read_csv("data/stats_jornada_2526.csv")
jugadas = stats[stats["valueTimePlayed"] > 0]

r = jugadas.groupby(["idPlayer", "shortName", "nameTeam"]).agg(
    partidos=("pointsJourney", "count"),
    media=("pointsJourney", "mean"),
    precio_inicial=("initialPrice", "first"),
    precio_final=("price", "first"),
).reset_index()

r = r[r["partidos"] >= 10]
r["puntos_por_millon_inicial"] = r["media"] / (r["precio_inicial"] / 1_000_000)
r["revalorizacion_%"] = (r["precio_final"] / r["precio_inicial"] - 1) * 100

print("--- Mayores chollos al inicio ---")
print(r.sort_values("puntos_por_millon_inicial", ascending=False).head(12).round(1).to_string(index=False))
print("\n--- Mayor revalorización ---")
print(r.sort_values("revalorizacion_%", ascending=False).head(12).round(1).to_string(index=False))