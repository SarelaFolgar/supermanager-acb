import pandas as pd

stats = pd.read_csv("data/stats_jornada_2526.csv")
jug = pd.read_csv("data/jugadores_2526.csv")

print("Filas y columnas (stats):", stats.shape)
print("Filas y columnas (jugadores):", jug.shape)
print("Jugadores distintos:", stats["idPlayer"].nunique())
print("Jornadas:", stats["numberJourney"].min(), "a", stats["numberJourney"].max())
print("Jornadas sin puntos (vacías):", stats["pointsJourney"].isna().sum())
print(stats[["shortName", "nameTeam", "numberJourney", "playerPrice", "pointsJourney"]].head(10))