import glob
import json

import pandas as pd
import pulp

import config

# === Configuración ===
with open("data/mi_equipo/caja.json", encoding="utf-8") as f:
    info_equipo = json.load(f)
CAJA = info_equipo["amount"]

MAX_CAMBIOS = config.MAX_CAMBIOS
FORZAR_VENTA_LESIONADOS = config.FORZAR_VENTA_LESIONADOS
TOP_POR_POSICION = config.TOP_POR_POSICION
POSICIONES = config.POSICIONES
MIN_LOCALES = config.MIN_LOCALES
MAX_EXTRA = config.MAX_EXTRA
PESO_REVAL = config.PESO_REVALORIZACION
UMBRAL = config.UMBRAL_MINIMO_CAMBIO

# === 1. Datos ===
pred = pd.read_csv("data/prediccion_global.csv")
plantilla = pd.read_csv("data/mi_equipo/plantilla_actual.csv")
mercado_snap = pd.read_csv(sorted(glob.glob("data/mercado/mercado_*.csv"))[-1])

plantilla = plantilla.merge(
    mercado_snap[["idPlayer", "price"]].rename(columns={"price": "precio_actual"}),
    on="idPlayer", how="left",
)
plantilla = plantilla.merge(
    pred[["idPlayer", "puntos_esperados_J2", "reval_esperada"]]
        .rename(columns={"puntos_esperados_J2": "pts_esp"}),
    on="idPlayer", how="left",
)
plantilla["pts_esp"] = plantilla["pts_esp"].fillna(0)
plantilla["reval_esperada"] = plantilla["reval_esperada"].fillna(0)
plantilla["score"] = plantilla["pts_esp"] + PESO_REVAL * plantilla["reval_esperada"] * 100
mis_ids = set(plantilla["idPlayer"].astype(int))

cand = pred[~pred["idPlayer"].isin(mis_ids)].copy()
cand = cand.merge(
    mercado_snap[["idPlayer", "price"]].rename(columns={"price": "precio_actual"}),
    on="idPlayer", how="left",
)
cand = cand.dropna(subset=["puntos_esperados_J2", "precio_actual"])
cand = cand[(cand["injuredDays"] == 0) & (cand["fisicStatus"] == "fit")]
cand = cand.rename(columns={"puntos_esperados_J2": "pts_esp"})
cand["score"] = cand["pts_esp"] + PESO_REVAL * cand["reval_esperada"].fillna(0) * 100

cand = pd.concat([
    cand[cand["position"] == p].nlargest(TOP_POR_POSICION, "score")
    for p in POSICIONES
]).reset_index(drop=True)
print(f"Candidatos en el modelo: {len(cand)}")

# === 2. Situación actual ===
print("\n--- Situación actual ---")
print(f"  Equipo: {info_equipo['nameTeam']} ({info_equipo['idUserTeam']})")
for pos, req in POSICIONES.items():
    n = (plantilla["position"] == pos).sum()
    print(f"  Posición {pos}: {n} (obligatorio {req})")
print(f"  Extracomunitarios: {plantilla['isExtraCommunity'].sum()} / {MAX_EXTRA}")
print(f"  Formados localmente: {plantilla['isNational'].sum()} / mínimo {MIN_LOCALES}")
print(f"  Caja: {CAJA:,.0f} €")
print(f"  Umbral mínimo de cambio: {UMBRAL} pts")

# === 3. Modelo ===
prob = pulp.LpProblem("cambios", pulp.LpMaximize)
hacer = pulp.LpVariable("hacer", cat="Binary")
vender = {i: pulp.LpVariable(f"v_{i}", cat="Binary") for i in plantilla.index}
fichar = {i: pulp.LpVariable(f"f_{i}", cat="Binary") for i in cand.index}

prob += (
    pulp.lpSum(cand.loc[i, "score"] * fichar[i] for i in cand.index)
    - pulp.lpSum(plantilla.loc[i, "score"] * vender[i] for i in plantilla.index)
    - UMBRAL * hacer
)

prob += pulp.lpSum(vender.values()) <= MAX_CAMBIOS * hacer
prob += pulp.lpSum(fichar.values()) <= MAX_CAMBIOS * hacer

prob += (
    CAJA
    + pulp.lpSum(plantilla.loc[i, "precio_actual"] * vender[i] for i in plantilla.index)
    - pulp.lpSum(cand.loc[i, "precio_actual"] * fichar[i] for i in cand.index)
    >= 0
)

for pos, req in POSICIONES.items():
    cur = int((plantilla["position"] == pos).sum())
    v = pulp.lpSum(vender[i] for i in plantilla.index if plantilla.loc[i, "position"] == pos)
    f = pulp.lpSum(fichar[i] for i in cand.index if cand.loc[i, "position"] == pos)
    prob += (cur - v + f == req)

cur_e = int(plantilla["isExtraCommunity"].sum())
v_e = pulp.lpSum(vender[i] for i in plantilla.index if plantilla.loc[i, "isExtraCommunity"])
f_e = pulp.lpSum(fichar[i] for i in cand.index if cand.loc[i, "isExtraCommunity"])
prob += (cur_e - v_e + f_e <= MAX_EXTRA)

cur_n = int(plantilla["isNational"].sum())
v_n = pulp.lpSum(vender[i] for i in plantilla.index if plantilla.loc[i, "isNational"])
f_n = pulp.lpSum(fichar[i] for i in cand.index if cand.loc[i, "isNational"])
prob += (cur_n - v_n + f_n >= MIN_LOCALES)

if FORZAR_VENTA_LESIONADOS:
    for i in plantilla.index:
        r = plantilla.loc[i]
        lesionado = (pd.notna(r["injuredDays"]) and r["injuredDays"] > 0) or \
                    (pd.notna(r["fisicStatus"]) and r["fisicStatus"] != "fit")
        if lesionado:
            prob += vender[i] == 1
            print(f"Forzando venta de {r['shortName']} ({r['nameTeam']}) - {r['fisicStatus']}")

# === 4. Resolver ===
prob.solve(pulp.PULP_CBC_CMD(msg=0))
print(f"\nEstado del solver: {pulp.LpStatus[prob.status]}")

hacer_cambios = hacer.varValue and hacer.varValue > 0.5

# === 5. Resultado ===
if not hacer_cambios:
    print("\n>>> NO SE RECOMIENDAN CAMBIOS. La plantilla actual es la mejor opción.")
    pd.DataFrame(columns=["accion"]).to_csv("data/mi_equipo/cambios.csv", index=False)
    print("Guardado data/mi_equipo/cambios.csv (vacío)")
else:
    print("\n=== VENDER ===")
    venta = 0
    for i in plantilla.index:
        if vender[i].varValue and vender[i].varValue > 0.5:
            r = plantilla.loc[i]
            print(f"  {r['shortName']:20s} {r['nameTeam']:25s} "
                  f"{r['precio_actual']:>10,.0f} €  "
                  f"pts={r['pts_esp']:.2f}  reval={r['reval_esperada']:+.1%}")
            venta += r["precio_actual"]

    print("\n=== FICHAR ===")
    compra = 0
    for i in cand.index:
        if fichar[i].varValue and fichar[i].varValue > 0.5:
            r = cand.loc[i]
            print(f"  {r['shortName']:20s} {r['nameTeam']:25s} "
                  f"{r['precio_actual']:>10,.0f} €  "
                  f"pts={r['pts_esp']:.2f}  reval={r['reval_esperada']:+.1%}")
            compra += r["precio_actual"]

    print(f"\nCaja inicial: {CAJA:>12,.0f} €")
    print(f"Total venta:  {venta:>12,.0f} €")
    print(f"Total compra: {compra:>12,.0f} €")
    print(f"Saldo final:  {CAJA + venta - compra:>12,.0f} €")

    # === 6. Verificación ===
    print("\n--- Verificación de la nueva plantilla ---")
    idx_vender = [i for i in plantilla.index
                  if vender[i].varValue and vender[i].varValue > 0.5]
    idx_fichar = [i for i in cand.index
                  if fichar[i].varValue and fichar[i].varValue > 0.5]

    nueva = plantilla.drop(index=idx_vender).copy()
    fichajes = cand.loc[idx_fichar].copy()
    nueva = pd.concat([nueva, fichajes], ignore_index=True)

    for pos, req in POSICIONES.items():
        n = (nueva["position"] == pos).sum()
        check = "OK" if n == req else "MAL"
        print(f"  {check} Posición {pos}: {n} / {req}")
    print(f"  Extracomunitarios: {nueva['isExtraCommunity'].sum()} / {MAX_EXTRA}")
    print(f"  Formados localmente: {nueva['isNational'].sum()} / mínimo {MIN_LOCALES}")

    # === 7. Guardar ===
    cambios = []
    for i in plantilla.index:
        if vender[i].varValue and vender[i].varValue > 0.5:
            cambios.append({"accion": "vender", **plantilla.loc[i].to_dict()})
    for i in cand.index:
        if fichar[i].varValue and fichar[i].varValue > 0.5:
            cambios.append({"accion": "fichar", **cand.loc[i].to_dict()})
    pd.DataFrame(cambios).to_csv("data/mi_equipo/cambios.csv", index=False)
    print("\nGuardado en data/mi_equipo/cambios.csv")