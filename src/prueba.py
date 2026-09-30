import pandas as pd
pred = pd.read_csv("data/prediccion_global.csv")
print(pred[pred["shortName"].str.contains("Ubal", case=False, na=False)]
      [["shortName", "nameTeam", "position", "price", "puntos_esperados_J2"]])