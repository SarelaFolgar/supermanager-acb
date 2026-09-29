import pandas as pd

stats = pd.read_csv("data/stats_jornada_2526.csv").sort_values(["idPlayer", "numberJourney"])

jugo = stats["valueTimePlayed"] > 0
stats["pts"] = stats["pointsJourney"].where(jugo)
stats["minutos"] = stats["valueTimePlayed"].where(jugo)
stats["precio"] = stats["playerPrice"].where(stats["playerPrice"] > 0)

g = stats.groupby("idPlayer")
stats["precio"] = g["precio"].ffill()

# Datos conocidos ANTES de cada jornada (shift(1) evita mirar al futuro)
stats["media_ult3"] = g["pts"].transform(lambda s: s.shift(1).rolling(3, min_periods=2).mean())
stats["minutos_ult3"] = g["minutos"].transform(lambda s: s.shift(1).rolling(3, min_periods=2).mean())
stats["precio_previo"] = g["precio"].shift(1)

feat = stats[["idPlayer", "shortName", "nameTeam", "numberJourney", "media_ult3",
              "minutos_ult3", "precio_previo", "pts"]].rename(columns={"pts": "puntos_objetivo"})
feat = feat.dropna(subset=["media_ult3", "precio_previo", "puntos_objetivo"])

feat.to_csv("data/features_2526.csv", index=False)
print(feat.shape)
print(feat.head(5).to_string(index=False))
print(feat[["media_ult3", "minutos_ult3", "precio_previo", "puntos_objetivo"]].corr().round(2))