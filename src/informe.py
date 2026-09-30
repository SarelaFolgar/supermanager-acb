"""
Genera un informe en Markdown a partir de los datos del pipeline.

Salida: informes/informe_<jornada>_<fecha>.md (un archivo por día).
"""
import glob
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

import config

# ─── 1. Cargar datos ────────────────────────────────────────
with open("data/mi_equipo/caja.json", encoding="utf-8") as f:
    info_equipo = json.load(f)
CAJA = info_equipo["amount"]
NOMBRE = info_equipo["nameTeam"]
ID_EQUIPO = info_equipo["idUserTeam"]
VALOR = info_equipo["brokerValor"]
POSICION = info_equipo["position"]

cambios = pd.read_csv("data/mi_equipo/cambios.csv")
plantilla = pd.read_csv("data/mi_equipo/plantilla_actual.csv")
pred = pd.read_csv("data/prediccion_global.csv")

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

n_jugadas_actuales = pred["partidos_actual"].max() if "partidos_actual" in pred.columns else 0

# Detectar jornada objetivo
archivo_mercado = sorted(glob.glob("data/raw/mercado_*.json"))[-1]
with open(archivo_mercado, encoding="utf-8") as f:
    mercado = json.load(f)
prox_jornada = None
for j in mercado:
    for e in j.get("playerStats", []):
        if "team" in e:
            prox_jornada = e["numberJourney"]
            break
    if prox_jornada:
        break
JORNADA = f"J{prox_jornada}"

sin_cambios = cambios.empty or "accion" not in cambios.columns

if not sin_cambios:
    vender = cambios[cambios["accion"] == "vender"].copy()
    fichar = cambios[cambios["accion"] == "fichar"].copy()
    ids_vendidos = set(vender["idPlayer"])
else:
    vender = pd.DataFrame()
    fichar = pd.DataFrame()
    ids_vendidos = set()

# ─── 2. Puntos esperados antes y después ────────────────────
pts_antes = plantilla["pts_esp"].sum()
mediana_plantilla = plantilla["pts_esp"].median()

if sin_cambios:
    pts_despues = pts_antes
    nueva_plantilla = plantilla.copy()
else:
    nueva_plantilla = plantilla[~plantilla["idPlayer"].isin(ids_vendidos)].copy()
    nueva_plantilla = pd.concat([nueva_plantilla, fichar], ignore_index=True)
    pts_despues = nueva_plantilla["pts_esp"].fillna(0).sum()

# ─── 3. Motivo de venta ─────────────────────────────────────
def motivo_venta(r):
    lesionado = (pd.notna(r.get("injuredDays", 0)) and r.get("injuredDays", 0) > 0) \
                or (pd.notna(r.get("fisicStatus")) and r.get("fisicStatus") != "fit")
    if lesionado:
        return "Lesionado"
    if r["pts_esp"] < mediana_plantilla:
        return "Bajo rendimiento esperado"
    return "Venta para liberar caja"

# ─── 4. Construir Markdown ──────────────────────────────────
ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
lineas = []

lineas.append(f"# Informe Supermanager ACB — {JORNADA}")
lineas.append(f"**Fecha:** {ahora}  ")
lineas.append(f"**Equipo:** {NOMBRE} (`{ID_EQUIPO}`)  ")
lineas.append(f"**Caja:** {CAJA:,.0f} € · **Valor:** {VALOR:,.0f} € · **Posición general:** {POSICION}")
lineas.append("")
lineas.append("> ⚠️ **Los puntos esperados son un ranking relativo, no una previsión.**")
lineas.append("> Sirven para ordenar opciones y comparar jugadores entre sí,")
lineas.append("> no para predecir el marcador exacto de la jornada.")
lineas.append("")
lineas.append("---")
lineas.append("")

# --- Cambios ---
lineas.append("## Cambios recomendados")
lineas.append("")

if sin_cambios:
    lineas.append("**✅ No hay cambios recomendados para esta jornada.**")
    lineas.append("")
    lineas.append("La plantilla actual es la mejor opción según el modelo, o el mejor")
    lineas.append(f"cambio no supera el umbral mínimo ({config.UMBRAL_MINIMO_CAMBIO} pts).")
    lineas.append("")
else:
    lineas.append("### Vender")
    lineas.append("")
    lineas.append(f"| Jugador | Equipo | Pos | Precio | Pts esp. {JORNADA} | Reval. esp. | Motivo |")
    lineas.append("|---------|--------|-----|--------|--------------------|-------------|--------|")
    for _, r in vender.iterrows():
        reval_str = f"{r['reval_esperada']:+.1%}"
        lineas.append(
            f"| {r['shortName']} | {r['nameTeam']} | {r['position']} | "
            f"{r['precio_actual']:,.0f} € | {r['pts_esp']:.2f} | {reval_str} | {motivo_venta(r)} |"
        )
    lineas.append("")

    lineas.append("### Fichar")
    lineas.append("")
    lineas.append(f"| Jugador | Equipo | Pos | Precio | Pts esp. {JORNADA} | Reval. esp. |")
    lineas.append("|---------|--------|-----|--------|--------------------|-------------|")
    for _, r in fichar.iterrows():
        reval_str = f"{r['reval_esperada']:+.1%}"
        lineas.append(
            f"| {r['shortName']} | {r['nameTeam']} | {r['position']} | "
            f"{r['precio_actual']:,.0f} € | {r['pts_esp']:.2f} | {reval_str} |"
        )
    lineas.append("")

# --- Economía ---
venta = vender["precio_actual"].sum() if not sin_cambios else 0
compra = fichar["precio_actual"].sum() if not sin_cambios else 0
saldo = CAJA + venta - compra
lineas.append("## Resumen económico")
lineas.append("")
lineas.append("| Concepto | Importe |")
lineas.append("|----------|--------:|")
lineas.append(f"| Caja inicial | {CAJA:,.0f} € |")
lineas.append(f"| Total ventas | {venta:,.0f} € |")
lineas.append(f"| Total compras | {compra:,.0f} € |")
lineas.append(f"| **Saldo final** | **{saldo:,.0f} €** |")
lineas.append("")

# --- Puntos ---
lineas.append("## Impacto en puntos")
lineas.append("")
lineas.append(f"- Puntos esperados **antes**: {pts_antes:.2f}")
lineas.append(f"- Puntos esperados **después**: {pts_despues:.2f}")
lineas.append(f"- **Diferencia: {pts_despues - pts_antes:+.2f} puntos** (ranking)")
lineas.append("")

# --- Plantilla actual con puntos esperados ---
lineas.append(f"## Plantilla actual — puntos esperados {JORNADA}")
lineas.append("")
lineas.append("| Pos | Jugador | Equipo | Precio | Pts esp. | Reval. esp. | Decisión |")
lineas.append("|-----|---------|--------|--------|---------:|-------------|----------|")
for _, r in plantilla.sort_values("pts_esp", ascending=False).iterrows():
    decision = "Vender" if r["idPlayer"] in ids_vendidos else "Mantener"
    lineas.append(
        f"| {r['position']} | {r['shortName']} | {r['nameTeam']} | "
        f"{r['precio_actual']:,.0f} € | {r['pts_esp']:.2f} | "
        f"{r['reval_esperada']:+.1%} | {decision} |"
    )
lineas.append("")

# --- Plantilla resultante ---
lineas.append("## Plantilla resultante")
lineas.append("")
lineas.append("| Pos | Jugador | Equipo | Precio | Pts esp. | Cupo |")
lineas.append("|-----|---------|--------|--------|---------:|------|")
for _, r in nueva_plantilla.sort_values(["position", "shortName"]).iterrows():
    if r.get("isExtraCommunity"):
        cupo = "EXT"
    elif r.get("isNational"):
        cupo = "JFL"
    else:
        cupo = "—"
    precio = r.get("precio_actual")
    precio_str = f"{precio:,.0f} €" if pd.notna(precio) else "—"
    pts = r["pts_esp"] if pd.notna(r["pts_esp"]) else 0
    lineas.append(
        f"| {r['position']} | {r['shortName']} | {r['nameTeam']} | "
        f"{precio_str} | {pts:.2f} | {cupo} |"
    )
lineas.append("")

# --- Verificación ---
lineas.append("## Verificación de reglas")
lineas.append("")
n_bases = (nueva_plantilla["position"] == 1).sum()
n_aleros = (nueva_plantilla["position"] == 3).sum()
n_pivots = (nueva_plantilla["position"] == 5).sum()
n_extra = int(nueva_plantilla["isExtraCommunity"].fillna(False).sum())
n_locales = int(nueva_plantilla["isNational"].fillna(False).sum())

def tick(ok):
    return "✅" if ok else "❌"

lineas.append(f"- {tick(n_bases == config.POSICIONES[1])} Bases: {n_bases} / {config.POSICIONES[1]}")
lineas.append(f"- {tick(n_aleros == config.POSICIONES[3])} Aleros: {n_aleros} / {config.POSICIONES[3]}")
lineas.append(f"- {tick(n_pivots == config.POSICIONES[5])} Pívots: {n_pivots} / {config.POSICIONES[5]}")
lineas.append(f"- {tick(n_extra <= config.MAX_EXTRA)} Extracomunitarios: {n_extra} / {config.MAX_EXTRA}")
lineas.append(f"- {tick(n_locales >= config.MIN_LOCALES)} Locales: {n_locales} / mínimo {config.MIN_LOCALES}")
lineas.append(f"- {tick(saldo >= 0)} Saldo no negativo: {saldo:,.0f} €")
lineas.append("")

# --- Alertas ---
if not sin_cambios:
    alertas = fichar[
        (fichar.get("injuredDays", 0) > 0) |
        (fichar.get("fisicStatus") != "fit")
    ] if "injuredDays" in fichar.columns else pd.DataFrame()

    if not alertas.empty:
        lineas.append("## ⚠️ Alertas")
        lineas.append("")
        for _, r in alertas.iterrows():
            lineas.append(
                f"- **{r['shortName']}** ({r['nameTeam']}): "
                f"{r.get('fisicStatus', '?')}, {r.get('injuredDays', 0)} días de baja"
            )
        lineas.append("")

# --- Notas del modelo ---
lineas.append("---")
lineas.append("")
lineas.append("## Notas sobre el modelo")
lineas.append("")
lineas.append(f"- Suavizado de jornadas: {config.SUAVIZADO_JORNADAS} (W sube con las jornadas)")
lineas.append(f"- Precio por punto (K): {config.K_PRECIO:,} €")
lineas.append(f"- Tope de variación de precio: ±{int(config.TOPE_PRECIO * 100)}%")
lineas.append("- Fuerza de equipo: win% 2025-26 + win% actual, ponderado por SUAVIZADO_JORNADAS")
lineas.append(f"- Jornadas jugadas: {n_jugadas_actuales}")
lineas.append(f"- Peso de la revalorización en el optimizador: {config.PESO_REVALORIZACION}")
lineas.append(f"- Umbral mínimo de cambio: {config.UMBRAL_MINIMO_CAMBIO} pts")
lineas.append("- Los jugadores sin histórico se estiman con `initialPrice / K`.")
lineas.append("- El bonus de cada jornada se descuenta dividiendo entre 1,2 si el equipo ganó y la valoración fue > 0.")
lineas.append("- Los puntos esperados son un ranking relativo, no una previsión puntual.")
lineas.append("")
lineas.append("### Criterios del motivo de venta")
lineas.append("")
lineas.append("- **Lesionado**: `injuredDays > 0` o `fisicStatus != \"fit\"`.")
lineas.append(f"- **Bajo rendimiento esperado**: puntos esperados por debajo de la mediana de la plantilla ({mediana_plantilla:.2f}).")
lineas.append("- **Venta para liberar caja**: puntúa por encima de la mediana pero se vende para financiar fichajes.")

# ─── 5. Guardar (un archivo por día, se sobreescribe) ───────
Path("informes").mkdir(exist_ok=True)
fecha = datetime.now().strftime("%Y-%m-%d")
ruta = Path("informes") / f"informe_{JORNADA}_{fecha}.md"
ruta.write_text("\n".join(lineas), encoding="utf-8")

print(f"\n✅ Informe guardado en {ruta}")

# ─── 6. Resumen por consola ─────────────────────────────────
print("\n" + "=" * 60)
print(f"  INFORME {JORNADA} — {ahora}")
print("=" * 60)
if sin_cambios:
    print("\nSin cambios recomendados. Plantilla óptima.")
else:
    print(f"\nVender:  {', '.join(vender['shortName'])}")
    print(f"Fichar:  {', '.join(fichar['shortName'])}")
    print(f"Saldo:   {saldo:,.0f} €")
    print(f"Puntos:  {pts_antes:.2f} → {pts_despues:.2f}  ({pts_despues - pts_antes:+.2f})")