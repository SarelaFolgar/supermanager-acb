import glob
import json

import pandas as pd
import pulp

import config

# === Carga ===
with open("data/mi_equipo/caja.json", encoding="utf-8") as f:
    info_equipo = json.load(f)
CAJA = info_equipo["amount"]

pred = pd.read_csv("data/procesado/prediccion_global.csv")
pred_v2 = pd.read_csv("data/procesado/prediccion_v2.csv")
plantilla = pd.read_csv("data/mi_equipo/plantilla_actual.csv")
mercado_snap = pd.read_csv(sorted(glob.glob("data/mercado/mercado_*.csv"))[-1])

MAX_CAMBIOS = config.MAX_CAMBIOS
FORZAR_VENTA_LESIONADOS = config.FORZAR_VENTA_LESIONADOS
TOP_POR_POSICION = config.TOP_POR_POSICION
POSICIONES = config.POSICIONES
MIN_LOCALES = config.MIN_LOCALES
MAX_EXTRA = config.MAX_EXTRA
UMBRAL = config.UMBRAL_MINIMO_CAMBIO

# === Jornada y pesos dinámicos ===
jornada = int(pred["partidos_actual"].max()) + 1 if "partidos_actual" in pred.columns else 1

if jornada >= config.JORNADAS_DECAIMIENTO:
    PESO_REVAL = config.PESO_REVAL_FINAL
else:
    factor = (config.JORNADAS_DECAIMIENTO - jornada) / (config.JORNADAS_DECAIMIENTO - 1)
    PESO_REVAL = config.PESO_REVAL_FINAL + (
        config.PESO_REVAL_INICIAL - config.PESO_REVAL_FINAL
    ) * factor

if jornada < config.JORNADA_BLEND_INICIO:
    peso_v2 = 0.0
elif jornada >= config.JORNADA_V2_TECHO:
    peso_v2 = config.PESO_V2_FINAL
else:
    paso = config.PESO_V2_FINAL / (config.JORNADA_V2_TECHO - config.JORNADA_BLEND_INICIO)
    peso_v2 = (jornada - config.JORNADA_BLEND_INICIO) * paso

print(f"  Jornada objetivo: J{jornada}")
print(f"  Peso broker: {PESO_REVAL:.2f}")
print(f"  Peso modelo v2: {peso_v2:.3f}")

# === Blend v1/v2 ===
pred = pred.merge(
    pred_v2[["idPlayer", "puntos_esperados_v2"]],
    on="idPlayer", how="left",
)
pred["pts_blend"] = (
    (1 - peso_v2) * pred["puntos_esperados_J2"]
    + peso_v2 * pred["puntos_esperados_v2"].fillna(pred["puntos_esperados_J2"])
)

COLS_PRED = [
    "idPlayer", "pts_blend", "puntos_esperados_J2", "puntos_esperados_v2",
    "reval_esperada", "reval_euros", "reval_euros_norm",
    "umbral_sube_15", "umbral_mantiene", "umbral_baja_15", "pronostico",
    "p_sube_15", "p_baja_15",
]

# === Plantilla ===
plantilla = plantilla.merge(
    mercado_snap[["idPlayer", "price"]].rename(columns={"price": "precio_actual"}),
    on="idPlayer", how="left",
)
plantilla = plantilla.merge(
    pred[COLS_PRED].rename(columns={"pts_blend": "pts_esp"}),
    on="idPlayer", how="left",
)
plantilla["pts_esp"] = plantilla["pts_esp"].fillna(0)
plantilla["reval_euros_norm"] = plantilla["reval_euros_norm"].fillna(0)
plantilla["reval_euros"] = plantilla["reval_euros"].fillna(0)
plantilla["reval_esperada"] = plantilla["reval_esperada"].fillna(0)
plantilla["umbral_sube_15"] = plantilla["umbral_sube_15"].fillna(0)
plantilla["umbral_mantiene"] = plantilla["umbral_mantiene"].fillna(0)
plantilla["umbral_baja_15"] = plantilla["umbral_baja_15"].fillna(0)
plantilla["pronostico"] = plantilla["pronostico"].fillna("—")
plantilla["p_sube_15"] = plantilla["p_sube_15"].fillna(0)
plantilla["p_baja_15"] = plantilla["p_baja_15"].fillna(0)
mis_ids = set(plantilla["idPlayer"].astype(int))

# === Candidatos ===
cand = pred[~pred["idPlayer"].isin(mis_ids)].copy()
cand = cand.merge(
    mercado_snap[["idPlayer", "price"]].rename(columns={"price": "precio_actual"}),
    on="idPlayer", how="left",
)
cand = cand.dropna(subset=["pts_blend", "precio_actual"])
cand = cand[(cand["injuredDays"] == 0) & (cand["fisicStatus"] == "fit")]
cand = cand.rename(columns={"pts_blend": "pts_esp"})
cand["reval_euros_norm"] = cand["reval_euros_norm"].fillna(0)
cand["reval_euros"] = cand["reval_euros"].fillna(0)
cand["reval_esperada"] = cand["reval_esperada"].fillna(0)

cand = pd.concat([
    cand[cand["position"] == p].nlargest(TOP_POR_POSICION, "pts_esp")
    for p in POSICIONES
]).reset_index(drop=True)


# === Función: resolver con un peso de broker dado ===
def resolver(peso):
    prob = pulp.LpProblem(f"cambios_w{peso}", pulp.LpMaximize)
    hacer = pulp.LpVariable("hacer", cat="Binary")
    vender = {i: pulp.LpVariable(f"v_{i}", cat="Binary") for i in plantilla.index}
    fichar = {i: pulp.LpVariable(f"f_{i}", cat="Binary") for i in cand.index}

    plantilla["score"] = plantilla["pts_esp"] + peso * plantilla["reval_euros_norm"]
    cand["score"] = cand["pts_esp"] + peso * cand["reval_euros_norm"]

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

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    hace = hacer.varValue and hacer.varValue > 0.5
    if not hace:
        return {
            "peso": peso, "pts_netos": 0.0, "reval_euros_neta": 0.0,
            "vender": [], "fichar": [], "n_cambios": 0,
        }

    idx_v = [i for i in plantilla.index if vender[i].varValue and vender[i].varValue > 0.5]
    idx_f = [i for i in cand.index if fichar[i].varValue and fichar[i].varValue > 0.5]

    pts_netos = cand.loc[idx_f, "pts_esp"].sum() - plantilla.loc[idx_v, "pts_esp"].sum()
    reval_euros_neta = cand.loc[idx_f, "reval_euros"].sum() - plantilla.loc[idx_v, "reval_euros"].sum()

    return {
        "peso": peso,
        "pts_netos": float(pts_netos),
        "reval_euros_neta": float(reval_euros_neta),
        "vender": plantilla.loc[idx_v, "shortName"].tolist(),
        "fichar": cand.loc[idx_f, "shortName"].tolist(),
        "n_cambios": len(idx_v),
    }


# === Frontera de Pareto (incluye el PESO_REVAL actual) ===
pesos_a_explorar = sorted(set(config.PESOS_EXPLORADOS + [round(PESO_REVAL, 2)]))
print(f"  Explorando {len(pesos_a_explorar)} pesos (incluye actual {PESO_REVAL:.2f})...")

resultados = [resolver(w) for w in pesos_a_explorar]
pareto = pd.DataFrame(resultados)
pareto.to_csv("data/mi_equipo/pareto.csv", index=False)


# === Detección de zona estable ===
def set_cambios(r):
    return frozenset(r["vender"] + r["fichar"])


def score_pareto(r, peso):
    return r["pts_netos"] + peso * r["reval_euros_neta"] / 100_000


sets = [set_cambios(r) for r in resultados]
pesos_ord = [r["peso"] for r in resultados]

grupos = []
actual = [0]
for i in range(1, len(sets)):
    if sets[i] == sets[i - 1]:
        actual.append(i)
    else:
        grupos.append(actual)
        actual = [i]
grupos.append(actual)

idx_actual = min(range(len(pesos_ord)), key=lambda i: abs(pesos_ord[i] - PESO_REVAL))
grupo_actual = next(g for g in grupos if idx_actual in g)

peso_min = pesos_ord[grupo_actual[0]]
peso_max = pesos_ord[grupo_actual[-1]]
n_valores = len(grupo_actual)

if n_valores >= 3:
    robustez = "ALTA"
elif n_valores == 2:
    robustez = "MEDIA"
else:
    robustez = "BAJA"

ref_score = score_pareto(resultados[idx_actual], PESO_REVAL)
casi = []
for i, r in enumerate(resultados):
    if sets[i] == sets[idx_actual]:
        continue
    s = score_pareto(r, PESO_REVAL)
    diff = abs(s - ref_score) / max(abs(ref_score), 1e-9)
    if diff < 0.01:
        casi.append({
            "peso": r["peso"],
            "pts_netos": r["pts_netos"],
            "reval_euros_neta": r["reval_euros_neta"],
            "diff_pct": round(diff * 100, 2),
            "vender": r["vender"],
            "fichar": r["fichar"],
        })

zona = {
    "peso_actual": PESO_REVAL,
    "peso_min": peso_min,
    "peso_max": peso_max,
    "n_valores": n_valores,
    "robustez": robustez,
    "soluciones_casi_equivalentes": casi,
}
with open("data/mi_equipo/zona_estable.json", "w", encoding="utf-8") as f:
    json.dump(zona, f, ensure_ascii=False, indent=2)

print(f"  Robustez: {robustez} (pesos {peso_min}–{peso_max}, {n_valores} valores)")
if casi:
    print(f"  {len(casi)} soluciones casi equivalentes (dentro del 1%)")


# === Resolver con el PESO_REVAL actual y guardar ===
principal = resolver(PESO_REVAL)
print(f"  Peso elegido: {PESO_REVAL:.2f} -> "
      f"{principal['n_cambios']} cambios, "
      f"{principal['pts_netos']:+.2f} pts, "
      f"{principal['reval_euros_neta']:+,.0f} EUR")

if principal["n_cambios"] == 0:
    pd.DataFrame(columns=["accion"]).to_csv("data/mi_equipo/cambios.csv", index=False)
else:
    prob = pulp.LpProblem("final", pulp.LpMaximize)
    hacer = pulp.LpVariable("hacer", cat="Binary")
    vender = {i: pulp.LpVariable(f"v_{i}", cat="Binary") for i in plantilla.index}
    fichar = {i: pulp.LpVariable(f"f_{i}", cat="Binary") for i in cand.index}

    plantilla["score"] = plantilla["pts_esp"] + PESO_REVAL * plantilla["reval_euros_norm"]
    cand["score"] = cand["pts_esp"] + PESO_REVAL * cand["reval_euros_norm"]

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
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    cambios = []
    for i in plantilla.index:
        if vender[i].varValue and vender[i].varValue > 0.5:
            cambios.append({"accion": "vender", **plantilla.loc[i].to_dict()})
    for i in cand.index:
        if fichar[i].varValue and fichar[i].varValue > 0.5:
            cambios.append({"accion": "fichar", **cand.loc[i].to_dict()})
    pd.DataFrame(cambios).to_csv("data/mi_equipo/cambios.csv", index=False)
    print(f"  {principal['n_cambios']} ventas + {principal['n_cambios']} fichajes guardados")