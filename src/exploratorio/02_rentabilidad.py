import pandas as pd

stats = pd.read_csv("data/stats_jornada_2526.csv")

# Partido jugado = minutos > 0
jugadas = stats[stats["valueTimePlayed"] > 0]

resumen = jugadas.groupby(["idPlayer", "shortName"]).agg(
    partidos=("pointsJourney", "count"),
    media=("pointsJourney", "mean"),
    regularidad=("pointsJourney", "std"),
).reset_index()

# La columna 'price' es el precio final del jugador (una sola cifra por jugador)
precio = stats.groupby("idPlayer")["price"].first().rename("precio_final")

resumen = resumen.merge(precio, on="idPlayer")
resumen["puntos_por_millon"] = resumen["media"] / (resumen["precio_final"] / 1_000_000)

# Descartamos a quien jugó pocos partidos (poca muestra)
resumen = resumen[resumen["partidos"] >= 10]

top = resumen.sort_values("puntos_por_millon", ascending=False)
print(top.head(15).round(2).to_string(index=False))