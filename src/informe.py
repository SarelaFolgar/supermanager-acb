"""
Genera un informe en Markdown y HTML con todo el detalle.
"""
import glob
import json
from datetime import datetime
from pathlib import Path

import markdown as md_lib
import pandas as pd

import config

# ─── Carga ──────────────────────────────────────────────────
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
pred_v2 = pd.read_csv("data/prediccion_v2.csv")
pareto = pd.read_csv("data/mi_equipo/pareto.csv")

# === Jornada y pesos dinámicos ===
n_jugadas_actuales = pred["partidos_actual"].max() if "partidos_actual" in pred.columns else 0
jornada_num = int(n_jugadas_actuales) + 1

if jornada_num >= config.JORNADAS_DECAIMIENTO:
    PESO_REVAL = config.PESO_REVAL_FINAL
else:
    factor = (config.JORNADAS_DECAIMIENTO - jornada_num) / (config.JORNADAS_DECAIMIENTO - 1)
    PESO_REVAL = config.PESO_REVAL_FINAL + (
        config.PESO_REVAL_INICIAL - config.PESO_REVAL_FINAL
    ) * factor


def peso_v2_para(j):
    if j < config.JORNADA_BLEND_INICIO:
        return 0.0
    if j >= config.JORNADA_V2_TECHO:
        return config.PESO_V2_FINAL
    paso = config.PESO_V2_FINAL / (config.JORNADA_V2_TECHO - config.JORNADA_BLEND_INICIO)
    return (j - config.JORNADA_BLEND_INICIO) * paso


peso_v2 = peso_v2_para(jornada_num)

pred = pred.merge(pred_v2[["idPlayer", "puntos_esperados_v2"]], on="idPlayer", how="left")
pred["pts_final"] = (
    (1 - peso_v2) * pred["puntos_esperados_J2"]
    + peso_v2 * pred["puntos_esperados_v2"].fillna(pred["puntos_esperados_J2"])
)

mercado_snap = pd.read_csv(sorted(glob.glob("data/mercado/mercado_*.csv"))[-1])
plantilla = plantilla.merge(
    mercado_snap[["idPlayer", "price"]].rename(columns={"price": "precio_actual"}),
    on="idPlayer", how="left",
)
cols_pred = ["idPlayer", "pts_final", "reval_esperada", "reval_euros",
             "umbral_sube_15", "umbral_mantiene", "umbral_baja_15", "pronostico",
             "cambio_equipo", "nameTeam_2526", "p_sube_15", "p_baja_15"]
plantilla = plantilla.merge(
    pred[cols_pred].rename(columns={"pts_final": "pts_esp"}),
    on="idPlayer", how="left",
)
for c in ["pts_esp", "reval_esperada", "reval_euros", "umbral_sube_15",
          "umbral_mantiene", "umbral_baja_15", "p_sube_15", "p_baja_15"]:
    plantilla[c] = plantilla[c].fillna(0)
plantilla["pronostico"] = plantilla["pronostico"].fillna("—")
plantilla["cambio_equipo"] = plantilla["cambio_equipo"].fillna(False)

PRONO_FLECHA = {
    "upup": "↑↑ Sube 15%",
    "up": "↑ Sube",
    "flat": "≈ Se mantiene",
    "down": "↓ Baja",
    "downdown": "↓↓ Baja 15%",
    "—": "—",
}

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
    for c in ["umbral_sube_15", "umbral_mantiene", "umbral_baja_15",
              "reval_euros", "reval_esperada", "cambio_equipo", "pts_final",
              "p_sube_15", "p_baja_15"]:
        if c not in vender.columns:
            vender = vender.merge(pred[["idPlayer", c]], on="idPlayer", how="left")
        if c not in fichar.columns:
            fichar = fichar.merge(pred[["idPlayer", c]], on="idPlayer", how="left")
    for c in ["umbral_sube_15", "umbral_mantiene", "umbral_baja_15",
              "p_sube_15", "p_baja_15"]:
        vender[c] = vender[c].fillna(0)
        fichar[c] = fichar[c].fillna(0)
    vender["cambio_equipo"] = vender["cambio_equipo"].fillna(False)
    fichar["cambio_equipo"] = fichar["cambio_equipo"].fillna(False)
else:
    vender = pd.DataFrame()
    fichar = pd.DataFrame()
    ids_vendidos = set()

pts_antes = plantilla["pts_esp"].sum()
mediana_plantilla = plantilla["pts_esp"].median()

if sin_cambios:
    pts_despues = pts_antes
    nueva_plantilla = plantilla.copy()
else:
    nueva_plantilla = plantilla[~plantilla["idPlayer"].isin(ids_vendidos)].copy()
    nueva_plantilla = pd.concat([nueva_plantilla, fichar], ignore_index=True)
    pts_despues = nueva_plantilla["pts_esp"].fillna(0).sum()

if not sin_cambios:
    venta_eur = vender["precio_actual"].sum()
    compra_eur = fichar["precio_actual"].sum()
else:
    venta_eur = 0
    compra_eur = 0
saldo = CAJA + venta_eur - compra_eur
reval_nueva_plantilla = nueva_plantilla["reval_euros"].fillna(0).sum()
caja_final = saldo + reval_nueva_plantilla
valor_actual_nueva = nueva_plantilla["precio_actual"].fillna(0).sum() + saldo
valor_proyectado_nueva = nueva_plantilla["precio_actual"].fillna(0).sum() + reval_nueva_plantilla + saldo

def motivo_venta(r):
    lesionado = (pd.notna(r.get("injuredDays", 0)) and r.get("injuredDays", 0) > 0) \
                or (pd.notna(r.get("fisicStatus")) and r.get("fisicStatus") != "fit")
    if lesionado:
        return "Lesionado"
    if r["pts_esp"] < mediana_plantilla:
        return "Bajo rendimiento"
    return "Liberar caja"

# ═══════════════════════════════════════════════════════════
# MARKDOWN
# ═══════════════════════════════════════════════════════════
ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
L = []

L.append(f"# Informe Supermanager ACB — {JORNADA}")
L.append("")
L.append(f"**Fecha:** {ahora}  ")
L.append(f"**Equipo:** {NOMBRE} (`{ID_EQUIPO}`)  ")
L.append(f"**Caja:** {CAJA:,.0f} € · **Valor:** {VALOR:,.0f} € · **Posición general:** {POSICION}")
L.append("")
L.append(f"**Configuración activa:** peso broker = {PESO_REVAL:.2f} · peso modelo v2 (minutos) = {peso_v2:.3f}")
L.append("")
L.append("> Los puntos esperados son un ranking relativo, no una previsión exacta. "
         "Sirven para ordenar opciones y comparar jugadores entre sí.")
L.append("")
L.append("> **Modelo probabilístico**: las columnas de revalorización usan simulación. "
         "No comparan un punto con un umbral: calculan la probabilidad de subir/bajar "
         "el 15% y el reval esperado sobre la distribución de la valoración del próximo partido.")
L.append("")
L.append("---")
L.append("")

# ═══════════════════════════════════════════════════════════
# CAMBIOS RECOMENDADOS
# ═══════════════════════════════════════════════════════════
L.append("## Cambios recomendados")
L.append("")
L.append("Esta sección es la más importante del informe. Propone los 4 cambios que maximizan "
         "el score del optimizador respetando todas las reglas del juego.")
L.append("")

if sin_cambios:
    L.append(f"**No hay cambios recomendados.** El mejor cambio no supera el umbral mínimo "
             f"de {config.UMBRAL_MINIMO_CAMBIO} puntos.")
    L.append("")
else:
    L.append("### Vender")
    L.append("")
    L.append(f"| Jugador | Equipo | Pos | Precio | Pts esp. {JORNADA} | P(↑15%) | P(↓15%) | Reval. € | Pronóstico | Motivo |")
    L.append("|---------|--------|-----|--------|--------------------|--------:|--------:|---------:|:----------:|--------|")
    for _, r in vender.iterrows():
        L.append(
            f"| {r['shortName']} | {r['nameTeam']} | {r['position']} | "
            f"{r['precio_actual']:,.0f} € | {r['pts_esp']:.2f} | "
            f"{r['p_sube_15']:.0%} | {r['p_baja_15']:.0%} | "
            f"{r['reval_euros']:+,.0f} € | "
            f"{PRONO_FLECHA.get(r.get('pronostico', '—'), '—')} | {motivo_venta(r)} |"
        )
    L.append("")
    L.append("**Cómo se lee esta tabla:**")
    L.append("")
    L.append("- **Precio**: lo que obtienes al venderlo ahora.")
    L.append("- **Pts esp.**: valoración que se espera que haga (media de la distribución).")
    L.append("- **P(↑15%)**: probabilidad estimada de que su precio suba el 15% (tope máximo).")
    L.append("- **P(↓15%)**: probabilidad estimada de que baje el 15% (tope mínimo).")
    L.append("- **Reval. €**: media de la variación esperada del precio en euros. Es el número "
             "que usa el optimizador para valorar el broker.")
    L.append("- **Pronóstico**: resumen visual del cruce entre P(↑15%) y P(↓15%). No es un punto, "
             "es una distribución.")
    L.append("- **Motivo**: por qué el optimizador quiere venderlo:")
    L.append("  - **Lesionado**: `injuredDays > 0` o `fisicStatus != \"fit\"`.")
    L.append(f"  - **Bajo rendimiento**: pts esp. por debajo de la mediana ({mediana_plantilla:.2f}).")
    L.append("  - **Liberar caja**: puntúa bien pero se vende para financiar fichajes.")
    L.append("")

    L.append("### Fichar")
    L.append("")
    L.append(f"| Jugador | Equipo | Pos | Precio | Pts esp. {JORNADA} | P(↑15%) | P(↓15%) | Reval. € | Pronóstico |")
    L.append("|---------|--------|-----|--------|--------------------|--------:|--------:|---------:|:----------:|")
    for _, r in fichar.iterrows():
        L.append(
            f"| {r['shortName']} | {r['nameTeam']} | {r['position']} | "
            f"{r['precio_actual']:,.0f} € | {r['pts_esp']:.2f} | "
            f"{r['p_sube_15']:.0%} | {r['p_baja_15']:.0%} | "
            f"{r['reval_euros']:+,.0f} € | "
            f"{PRONO_FLECHA.get(r.get('pronostico', '—'), '—')} |"
        )
    L.append("")
    L.append("**Cómo se lee:** igual que la de vender. Lo ideal es combinar **pts esp. altos** "
             "con **reval. € positivos**. Si un jugador tiene solo una de las dos cosas, el "
             "optimizador ha decidido que compensa por el otro lado.")
    L.append("")

# Economía
L.append("## Resumen económico")
L.append("")
L.append("Caja después de aplicar los cambios. El saldo final nunca puede ser negativo.")
L.append("")
L.append("| Concepto | Importe |")
L.append("|----------|--------:|")
L.append(f"| Caja inicial | {CAJA:,.0f} € |")
L.append(f"| Total ventas | {venta_eur:,.0f} € |")
L.append(f"| Total compras | {compra_eur:,.0f} € |")
L.append(f"| **Caja tras los cambios** | **{saldo:,.0f} €** |")
L.append("")

if not sin_cambios:
    L.append("## Proyección económica")
    L.append("")
    L.append("¿Cómo quedaría tu equipo después de la jornada, si se cumplen las "
             "revalorizaciones esperadas (media de la distribución)?")
    L.append("")
    L.append("| Concepto | Importe |")
    L.append("|----------|--------:|")
    L.append(f"| Caja tras los cambios | {saldo:,.0f} € |")
    L.append(f"| + Reval. esperada de la nueva plantilla | {reval_nueva_plantilla:+,.0f} € |")
    L.append(f"| **= Caja final proyectada** | **{caja_final:,.0f} €** |")
    L.append("")
    L.append(f"**Valor del equipo ahora:** {valor_actual_nueva:,.0f} € → "
             f"**proyectado:** {valor_proyectado_nueva:,.0f} €")
    L.append("")
    L.append("> **Aviso:** estas cifras son medias de una distribución, no promesas. "
             "El intervalo real incluye jornadas buenas y malas.")
    L.append("")

L.append("## Impacto en puntos")
L.append("")
L.append(f"- Puntos esperados **antes**: {pts_antes:.2f}")
L.append(f"- Puntos esperados **después**: {pts_despues:.2f}")
L.append(f"- **Diferencia: {pts_despues - pts_antes:+.2f} puntos**")
L.append("")

# Ranking
L.append("## Ranking — mayor subida esperada (euros)")
L.append("")
L.append("Top 15 jugadores del mercado (excluyendo tu plantilla y lesionados) por "
         "**ganancia esperada de precio en euros** (media de la distribución).")
L.append("")
mercado_fit = pred[(pred["injuredDays"] == 0) & (pred["fisicStatus"] == "fit")].copy()
top_subida = mercado_fit.nlargest(15, "reval_euros")[
    ["shortName", "nameTeam", "position", "price",
     "pts_final", "reval_euros", "p_sube_15", "p_baja_15", "pronostico"]
]
L.append("| Jugador | Equipo | Pos | Precio | Pts esp. | P(↑15%) | P(↓15%) | Reval. € | Pronóstico |")
L.append("|---------|--------|-----|--------|---------:|--------:|--------:|---------:|:----------:|")
for _, r in top_subida.iterrows():
    L.append(
        f"| {r['shortName']} | {r['nameTeam']} | {r['position']} | "
        f"{r['price']:,.0f} € | {r['pts_final']:.1f} | "
        f"{r['p_sube_15']:.0%} | {r['p_baja_15']:.0%} | "
        f"{r['reval_euros']:+,.0f} € | {PRONO_FLECHA.get(r['pronostico'], '—')} |"
    )
L.append("")
L.append("**Cómo se lee:** los jugadores están ordenados por Reval. € (no por %). "
         "Un jugador barato con P(↑15%) alta puede generar poco dinero; uno caro con "
         "P(↑15%) media puede generar más.")
L.append("")

# Frontera Pareto
L.append("## Frontera puntos vs. broker")
L.append("")
L.append("El optimizador tiene un dilema: **no puede maximizar puntos y broker a la vez**. "
         "Para verlo, se ejecuta varias veces con distintos pesos del broker y se muestran "
         "los cambios que haría en cada caso.")
L.append("")
L.append("| Peso | Cambios | Pts netos | Reval neta (€) | Vender | Fichar |")
L.append("|-----:|--------:|----------:|---------------:|--------|--------|")
for _, r in pareto.iterrows():
    marca = " *" if abs(r["peso"] - PESO_REVAL) < 0.01 else ""
    vender_str = ", ".join(eval(r["vender"])) if isinstance(r["vender"], str) else ", ".join(r["vender"])
    fichar_str = ", ".join(eval(r["fichar"])) if isinstance(r["fichar"], str) else ", ".join(r["fichar"])
    L.append(
        f"| {r['peso']:.2f}{marca} | {int(r['n_cambios'])} | "
        f"{r['pts_netos']:+.2f} | {r['reval_euros_neta']:+,.0f} € | "
        f"{vender_str or '—'} | {fichar_str or '—'} |"
    )
L.append("")
L.append(f"\\* = configuración actual para J{jornada_num}: `PESO_REVAL = {PESO_REVAL:.2f}`.")
L.append("")
L.append("**Cómo se lee esta tabla:**")
L.append("")
L.append("Cada fila es una **ejecución distinta del optimizador** con un peso del broker distinto:")
L.append("")
L.append("- **Peso 0.00** = solo le importan los puntos. Ignora la revalorización.")
L.append("- **Peso 15.00** = el broker pesa muchísimo. Sacrifica puntos por ganar dinero.")
L.append(f"- **Peso {PESO_REVAL:.2f} \\*** = es el que tienes configurado para la J{jornada_num}. "
         f"Con él se ha generado la sección 'Cambios recomendados'.")
L.append("")
L.append("**Qué mirar:**")
L.append("")
L.append("1. **¿Las ventas son estables?** Si los mismos jugadores aparecen en casi todas las "
             "filas, la decisión es robusta.")
L.append("2. **¿Los fichajes son estables?** Igual con la columna Fichar. Un núcleo fijo indica "
             "que son claramente buenos.")
L.append("3. **¿Dónde está el codo?** Busca la fila donde más reval se gana sin sacrificar "
             "demasiados puntos. Normalmente es tu `PESO_REVAL` actual.")
L.append("")
L.append("**¿De dónde sale el peso?**")
L.append("")
L.append("No es un valor óptimo calculado. Es una fórmula lineal que decae entre J1 (peso 15) "
         "y J10 (peso 1). La justificación:")
L.append("")
L.append("- **En J1-J3 tu caja es escasa.** Sin caja no puedes fichar. La única forma de "
         "conseguir caja es que tus jugadores suban de precio.")
L.append("- **En J10+ la plantilla ya está consolidada.** Importan más los puntos que el dinero.")
L.append("- **Equivalencia práctica:** 100.000 € de reval valen ~2 puntos de media por jornada "
         "en el mercado. Aceptar una pérdida de 2 puntos ahora a cambio de +84.000 € es un "
         "intercambio razonable a 5-10 jornadas vista.")
L.append("")

# Sensibilidad al histórico
ruta_suav = Path("data/exploracion_suavizado.csv")
if ruta_suav.exists():
    suav = pd.read_csv(ruta_suav)
    L.append("## Sensibilidad al peso del histórico")
    L.append("")
    L.append("Igual que con el broker, aquí exploramos cuánto tarda la temporada actual en "
             "pesar más que el histórico. El modelo se ejecuta con distintos valores de "
             "`SUAVIZADO_JORNADAS` y se ve qué candidatos salen en cada caso.")
    L.append("")
    L.append("| SUAVIZADO | W (2 partidos) | Top 6 candidatos |")
    L.append("|----------:|---------------:|------------------|")
    for _, r in suav.iterrows():
        top_str = " · ".join(
            str(r[f"top{i}"]) for i in range(1, 7)
            if f"top{i}" in r and pd.notna(r[f"top{i}"])
        )
        L.append(f"| {int(r['suavizado'])} | {r['w_j2']:.2f} | {top_str} |")
    L.append("")
    L.append("**Cómo se lee:**")
    L.append("")
    L.append("- **SUAVIZADO bajo (2)**: W sube rápido. Con 2 partidos ya está 50/50.")
    L.append("- **SUAVIZADO alto (8)**: W sube despacio. Con 8 partidos aún no llega a 50/50.")
    L.append("- **SUAVIZADO = 4** (valor actual): el óptimo según el backtest.")
    L.append("")
    L.append("**Qué mirar:** si los candidatos del top son parecidos en todos los valores, "
             "el modelo es robusto al peso del histórico. Si cambian mucho, el parámetro "
             "es sensible y conviene fiarse del valor óptimo (4).")
    L.append("")
    L.append("**Tabla de pesos por jornada:**")
    L.append("")
    L.append("| SUAVIZADO | J1 | J2 | J4 | J8 | J10 | Comportamiento |")
    L.append("|----------:|---:|---:|---:|---:|----:|----------------|")
    L.append("| 2 | 0,33 | 0,50 | 0,67 | 0,80 | 0,83 | Reacciona rápido al presente |")
    L.append("| 3 | 0,25 | 0,40 | 0,57 | 0,73 | 0,77 | Un poco más lento |")
    L.append("| **4** | **0,20** | **0,33** | **0,50** | **0,67** | **0,71** | Óptimo según backtest |")
    L.append("| 6 | 0,14 | 0,25 | 0,40 | 0,57 | 0,63 | Fía más del histórico |")
    L.append("| 8 | 0,11 | 0,20 | 0,33 | 0,50 | 0,56 | Se fía mucho del histórico |")
    L.append("")
    L.append("En cualquier caso, **el histórico nunca se ignora del todo**: `1 − W` siempre es "
             "positivo. Para ignorarlo haría falta `SUAVIZADO = 0`, y eso no tiene sentido.")
    L.append("")

# Plantilla actual
L.append(f"## Plantilla actual — puntos esperados {JORNADA}")
L.append("")
L.append("Tus 10 jugadores actuales, ordenados por puntos esperados (de mayor a menor). "
         "La columna **Decisión** indica si el optimizador los vendería o los mantendría.")
L.append("")
L.append("| Pos | Jugador | Equipo | Precio | Pts esp. | P(↑15%) | P(↓15%) | Reval. € | Pronóstico | Decisión |")
L.append("|-----|---------|--------|--------|---------:|--------:|--------:|---------:|:----------:|----------|")
for _, r in plantilla.sort_values("pts_esp", ascending=False).iterrows():
    decision = "Vender" if r["idPlayer"] in ids_vendidos else "Mantener"
    L.append(
        f"| {r['position']} | {r['shortName']} | {r['nameTeam']} | "
        f"{r['precio_actual']:,.0f} € | {r['pts_esp']:.2f} | "
        f"{r['p_sube_15']:.0%} | {r['p_baja_15']:.0%} | "
        f"{r['reval_euros']:+,.0f} € | "
        f"{PRONO_FLECHA.get(r['pronostico'], '—')} | {decision} |"
    )
L.append("")
L.append("**Cómo se lee:**")
L.append("")
L.append("- Los de arriba son tus mejores jugadores según el modelo. Si están en 'Mantener', "
             "los conservas.")
L.append("- Los de abajo probablemente se venden (bajo rendimiento o liberar caja).")
L.append("- Fíjate en **Pts esp. vs P(↑15%)**: si un jugador tiene 15 pts esperados y P(↑15%) = 30%, "
             "no es lo mismo que si tiene 15 pts y P(↑15%) = 80%.")
L.append("")

# Plantilla resultante
L.append("## Plantilla resultante")
L.append("")
L.append("Tu equipo después de aplicar los cambios recomendados. Es el equipo con el que "
         "jugarías la próxima jornada.")
L.append("")
L.append("| Pos | Jugador | Equipo | Precio | Pts esp. | Cupo |")
L.append("|-----|---------|--------|--------|---------:|------|")
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
    L.append(
        f"| {r['position']} | {r['shortName']} | {r['nameTeam']} | "
        f"{precio_str} | {pts:.2f} | {cupo} |"
    )
L.append("")
L.append("**Cómo se lee:**")
L.append("")
L.append("- **Pos**: 1=base, 3=alero, 5=pívot. Deben ser 2/4/4.")
L.append("- **Cupo**: EXT (extracomunitario, máx. 2), JFL (formado local, mín. 4), "
             "— (ni uno ni otro).")
L.append("")

# Verificación
L.append("## Verificación de reglas")
L.append("")
L.append("El solver comprueba que la plantilla resultante cumple todas las reglas del juego.")
L.append("")
n_bases = (nueva_plantilla["position"] == 1).sum()
n_aleros = (nueva_plantilla["position"] == 3).sum()
n_pivots = (nueva_plantilla["position"] == 5).sum()
n_extra = int(nueva_plantilla["isExtraCommunity"].fillna(False).sum())
n_locales = int(nueva_plantilla["isNational"].fillna(False).sum())

def tick(ok):
    return "OK" if ok else "FALLO"

L.append(f"- [{tick(n_bases == config.POSICIONES[1])}] Bases: {n_bases} / {config.POSICIONES[1]}")
L.append(f"- [{tick(n_aleros == config.POSICIONES[3])}] Aleros: {n_aleros} / {config.POSICIONES[3]}")
L.append(f"- [{tick(n_pivots == config.POSICIONES[5])}] Pivots: {n_pivots} / {config.POSICIONES[5]}")
L.append(f"- [{tick(n_extra <= config.MAX_EXTRA)}] Extracomunitarios: {n_extra} / {config.MAX_EXTRA}")
L.append(f"- [{tick(n_locales >= config.MIN_LOCALES)}] Locales: {n_locales} / minimo {config.MIN_LOCALES}")
L.append(f"- [{tick(saldo >= 0)}] Saldo no negativo: {saldo:,.0f} EUR")
L.append("")
L.append("**Si alguna regla sale como FALLO**, hay un bug en el optimizador. No apliques "
         "los cambios y avisa.")
L.append("")

if not sin_cambios:
    alertas = fichar[
        (fichar.get("injuredDays", 0) > 0) |
        (fichar.get("fisicStatus") != "fit")
    ] if "injuredDays" in fichar.columns else pd.DataFrame()
    if not alertas.empty:
        L.append("## Alertas")
        L.append("")
        L.append("Alguno de los fichajes recomendados tiene problemas físicos. Comprueba "
                 "en la web del Supermanager antes de hacer los cambios.")
        L.append("")
        for _, r in alertas.iterrows():
            L.append(f"- **{r['shortName']}** ({r['nameTeam']}): {r.get('fisicStatus', '?')}")
        L.append("")

# ═══════════════════════════════════════════════════════════
# CÓMO FUNCIONA EL MODELO
# ═══════════════════════════════════════════════════════════
L.append("---")
L.append("")
L.append("## Cómo funciona el modelo")
L.append("")
L.append("Esta sección explica con detalle de dónde sale cada número del informe. Está pensada "
         "para que alguien que lo vea por primera vez entienda todo sin ayuda.")
L.append("")

# --- 1. Valoración ---
L.append("### 1. ¿Qué es la 'valoración'?")
L.append("")
L.append("En el Supermanager, cuando hablamos de 'puntos' nos referimos a la **valoración ACB**, "
         "no a las canastas. La fórmula es:")
L.append("")
L.append("```")
L.append("valoración = PTS + asistencias + rebotes + tapones a favor + robos")
L.append("           + faltas recibidas + T1C + T2C + T3C")
L.append("           − pérdidas − tapones en contra − faltas personales")
L.append("           − T1I − T2I − T3I")
L.append("```")
L.append("")
L.append("Donde `TxC` son tiros anotados y `TxI` son tiros fallados.")
L.append("")
L.append("Un jugador que anota 10 puntos reales (5 canastas de 2), coge 8 rebotes, pone 2 tapones, "
         "recibe 3 faltas y falla 4 tiros tendría `10 + 8 + 2 + 3 − 4 = 19` de valoración.")
L.append("")
L.append("**Bonus por victoria:** si el equipo gana y la valoración es positiva, "
         "el Supermanager multiplica los puntos por 1,2. Si pierde, o si la valoración es ≤ 0, "
         "no hay bonus.")
L.append("")

# --- 2. Puntos esperados ---
L.append("### 2. Puntos esperados (Pts esp.)")
L.append("")
L.append("Es la valoración ACB que **esperamos** que haga el jugador en la próxima jornada. "
         "Se calcula en 6 pasos:")
L.append("")
L.append("#### Paso 1 — ¿Cuánto pesa cada temporada?")
L.append("")
L.append("```")
L.append("W = partidos_jugados / (partidos_jugados + SUAVIZADO)")
L.append("```")
L.append("")
L.append(f"Con `SUAVIZADO = {config.SUAVIZADO_JORNADAS}`:")
L.append("")
L.append("| Partidos jugados | W (temporada actual) | 1−W (histórico) |")
L.append("|-----------------:|--------------------:|----------------:|")
L.append("| 1 | 0,20 | 0,80 |")
L.append("| 2 | 0,33 | 0,67 |")
L.append("| 3 | 0,43 | 0,57 |")
L.append("| 4 | 0,50 | 0,50 |")
L.append("| 5 | 0,56 | 0,44 |")
L.append("| 8 | 0,67 | 0,33 |")
L.append("| 20 | 0,83 | 0,17 |")
L.append("")
L.append("**No hay que tocar nada.** Se ajusta solo. En J1 se fía casi todo del histórico. "
         "En J5 lo actual ya pesa más. En J20 lo actual pesa 83%.")
L.append("")
L.append("#### Paso 2 — Peso del histórico según cambio de equipo")
L.append("")
L.append("```")
L.append("factor_hist = 0,3  si cambió de equipo y lleva ≥ 3 partidos en el nuevo")
L.append("factor_hist = 1,0  en cualquier otro caso")
L.append("peso_hist = (1 − W) × factor_hist")
L.append("peso_actual = 1 − peso_hist")
L.append("```")
L.append("")
L.append("Si un jugador cambió de equipo, su histórico se pondera al 30% porque su rol "
         "puede ser distinto. Pero solo si ya lleva 3+ partidos en el nuevo (evita el caso "
         "T. Allen: una sola jornada espectacular inflaba la predicción).")
L.append("")
L.append("#### Paso 3 — Media esperada sin bonus")
L.append("")
L.append("```")
L.append("media_sin_bonus = peso_actual × media_actual + peso_hist × media_2526")
L.append("```")
L.append("")
L.append("Las medias son de **valoración sin bonus**. El bonus se añade en el paso 5.")
L.append("")
L.append("#### Paso 4 — Probabilidad de victoria")
L.append("")
L.append("```")
L.append("p_win = sigmoide((fuerza_equipo − fuerza_rival) × 4 + localía × 5)")
L.append("```")
L.append("")
L.append("La fuerza del equipo combina win% de 2025-26 con win% de esta temporada "
         "(ponderadas por W). Localía: +0,10 en casa, −0,10 fuera.")
L.append("")
L.append("#### Paso 5 — Bonus esperado por victoria")
L.append("")
L.append("```")
L.append("puntos_v1 = media_sin_bonus × (1 + 0,2 × p_win)")
L.append("```")
L.append("")
L.append("Si el equipo ganara seguro (p_win=1), +20%. Si perdiera seguro (p_win=0), 0%. "
         "En el medio, proporcional.")
L.append("")
L.append("#### Paso 6 — Blend con el modelo de minutos (v2)")
L.append("")
L.append("```")
L.append("puntos_final = (1 − peso_v2) × puntos_v1 + peso_v2 × puntos_v2")
L.append("puntos_v2 = minutos_esperados × PPM_esperado × (1 + 0,2 × p_win)")
L.append("```")
L.append("")
L.append(f"En J{jornada_num}, `peso_v2 = {peso_v2:.3f}`. v2 se pondera poco porque el "
         f"backtest sobre 2025-26 (6.261 predicciones) demostró que predice similar a v1 "
         f"(MAE 5,58 vs 5,61).")
L.append("")
L.append("#### Jugadores sin histórico 2025-26")
L.append("")
L.append("Si un jugador no jugó en ACB la temporada pasada, no tiene `media_2526`. "
         "En su lugar usamos:")
L.append("")
L.append("```")
L.append("media_referencia = initialPrice / 50.000")
L.append("```")
L.append("")
L.append("El `initialPrice` es lo que la propia ACB esperaba de él al fijarle precio. "
         "Se mezcla con la media actual usando la misma W:")
L.append("")
L.append("```")
L.append("media_sin_bonus = W × media_actual + (1 − W) × media_referencia")
L.append("```")
L.append("")
L.append("Con J1 (W=0,20): 20% su partido real, 80% la referencia inicial. "
         "Con J10 (W=0,71): 71% sus partidos, 29% la referencia.")
L.append("")
L.append("#### Ejemplo real (Tavares, J3)")
L.append("")
L.append("| Paso | Valor |")
L.append("|------|------:|")
L.append("| Media 2025-26 sin bonus | 16,43 |")
L.append("| Media actual (2 partidos) sin bonus | ~12,15 |")
L.append("| W (2 partidos) | 0,33 |")
L.append("| factor_hist | 1,0 (sigue en Real Madrid) |")
L.append("| peso_hist / peso_actual | 0,67 / 0,33 |")
L.append("| media_sin_bonus | 0,33×12,15 + 0,67×16,43 = **15,02** |")
L.append("| p_win (contra Obradoiro, en casa) | ~0,72 |")
L.append("| **Pts esp. v1** | 15,02 × (1 + 0,2×0,72) = **17,17** |")
L.append("| Pts esp. v2 | 16,90 |")
L.append("| **Pts esp. final** | 0,97 × 17,17 + 0,03 × 16,90 = **17,16** |")
L.append("")

# --- 3. Cuándo pesa más la temporada actual ---
L.append("### 3. ¿Cuándo empieza a pesar más la temporada actual?")
L.append("")
L.append(f"Con `SUAVIZADO = {config.SUAVIZADO_JORNADAS}` (óptimo según el backtest):")
L.append("")
L.append("| Partidos jugados | Peso actual (W) | Peso histórico (1−W) | ¿Cuál manda? |")
L.append("|-----------------:|----------------:|---------------------:|--------------|")
L.append("| J1 | 0,20 | 0,80 | Histórico |")
L.append("| J2 | 0,33 | 0,67 | Histórico |")
L.append("| J3 | 0,43 | 0,57 | Histórico |")
L.append("| J4 | 0,50 | 0,50 | Empate |")
L.append("| **J5** | **0,56** | **0,44** | **Temporada actual** |")
L.append("| J10 | 0,71 | 0,29 | Temporada actual |")
L.append("| J20 | 0,83 | 0,17 | Temporada actual |")
L.append("")
L.append("Esto significa que **a partir de la J5 el modelo se fía más de lo que el jugador "
         "está haciendo esta temporada que de lo que hizo el año pasado.** Se ajusta solo.")
L.append("")

# --- 4. Backtest SUAVIZADO ---
L.append("### 4. Cómo se eligió SUAVIZADO = 4 (backtest)")
L.append("")
L.append("El valor óptimo de `SUAVIZADO_JORNADAS` se obtuvo con un **backtest sobre la "
         "temporada 2025-26** (34 jornadas, ~250 jugadores, 6.261 predicciones).")
L.append("")
L.append("El método fue:")
L.append("")
L.append("1. **Dividir la temporada de cada jugador** en dos partes: los **primeros 5 partidos** "
         "(simulan el 'histórico') y los **partidos 6 a 34** (simulan la temporada en curso).")
L.append("2. **Para cada jornada J ≥ 6**, predecir J usando solo datos hasta J−1, probando varios "
         "valores de SUAVIZADO.")
L.append("3. **Comparar la predicción con lo que realmente hizo** el jugador en J.")
L.append("4. **Calcular el MAE** (error medio absoluto) para cada valor.")
L.append("")
L.append("Resultados:")
L.append("")
L.append("| SUAVIZADO | MAE | RMSE | Correlación |")
L.append("|----------:|----:|-----:|------------:|")
L.append("| 2 | 5,592 | 7,162 | 0,453 |")
L.append("| 3 | 5,578 | 7,146 | 0,455 |")
L.append("| **4** | **5,575** | **7,143** | **0,456** |")
L.append("| 6 | 5,584 | 7,155 | 0,454 |")
L.append("| 8 | 5,600 | 7,174 | 0,451 |")
L.append("")
L.append("El valor 4 minimiza el MAE. **Las diferencias son ruido** (5,575 a 5,600), así que "
         "cualquier valor entre 3 y 6 funcionaría igual de bien. Elegimos 4 por ser el más "
         "redondo, no porque sea demostrablemente superior.")
L.append("")
L.append("**¿Por qué funciona el backtest sin datos de otra temporada?** Porque no necesita "
         "'histórico de años anteriores'. Mide: *¿cuánto peso dar a los primeros partidos vs a "
         "los más recientes?* Eso es exactamente el mismo problema matemático que resolverá W.")
L.append("")

# --- 5. Modelo probabilístico (NUEVO) ---
L.append("### 5. Modelo probabilístico de revalorización")
L.append("")
L.append("Para predecir la revalorización de precio **no basta con un solo punto**. Si un "
         "jugador tiene 15,7 pts esperados y su umbral de subida es 15,4, no es un 'sube 15%' "
         "seguro: es prácticamente una moneda al aire. La varianza jornada a jornada es de "
         "±5-7 puntos.")
L.append("")
L.append("Para capturarlo, usamos **simulación Monte Carlo**:")
L.append("")
L.append("```")
L.append("valoración_simulada ~ Normal(mu = pts_esperados, sd = 4.5 + 0.25 × mu)")
L.append("objetivo = 50.000 × (S + valoración_simulada) / (N + 1)")
L.append("precio_nuevo = clip(objetivo, precio × 0.85, precio × 1.15)")
L.append("```")
L.append("")
L.append(f"Con `{config.N_SIMULACIONES:,}` simulaciones por jugador. De la distribución de "
         f"`precio_nuevo − precio` obtenemos:")
L.append("")
L.append("- **Reval. €**: media de la variación (lo que usa el optimizador).")
L.append("- **P(↑15%)**: fracción de simulaciones donde toca el techo del +15%.")
L.append("- **P(↓15%)**: fracción de simulaciones donde toca el suelo del −15%.")
L.append("")
L.append("**Ejemplo:** un jugador con 15,7 pts esperados y umbral de subida 15,4 puede tener "
         "P(↑15%) = 52%, es decir, una moneda al aire. En cambio, uno con 20 pts esperados y "
         "umbral 15,4 tendría P(↑15%) = 90%.")
L.append("")
L.append("La desviación típica `4.5 + 0.25 × mu` está ajustada empíricamente sobre 2025-26: "
         "los jugadores que puntúan más tienen también más varianza.")
L.append("")

# --- 6. Umbrales de precio ---
L.append("### 6. Umbrales de precio")
L.append("")
L.append("Regla oficial del Supermanager:")
L.append("")
L.append("```")
L.append("precio_nuevo = 50.000 × media_acumulada")
L.append("media_acumulada = (suma de valoraciones de la temporada) / (partidos jugados)")
L.append("```")
L.append("")
L.append("Con tope del **±15%** por jornada. Despejando la valoración `X` necesaria para cada umbral:")
L.append("")
L.append("```")
L.append("X_mantiene = P × (N+1) / 50.000 − S")
L.append("X_sube_15 = P × 1,15 × (N+1) / 50.000 − S")
L.append("X_baja_15 = P × 0,85 × (N+1) / 50.000 − S")
L.append("```")
L.append("")
L.append("Donde `P` es el precio actual, `N` los partidos jugados esta temporada, "
         "y `S` la suma de valoraciones esta temporada.")
L.append("")
L.append("**Verificación empírica:** hemos validado esta fórmula contra las capturas reales "
         "del mercado. Resultados:")
L.append("")
L.append("| Contar jornadas sin jugar (0 pts) | Error medio | Aciertos < 1% |")
L.append("|:---------------------------------:|------------:|--------------:|")
L.append("| Sí | 1,05% | 236 / 250 |")
L.append("| No | 1,62% | 231 / 250 |")
L.append("")
L.append("**Conclusión:** la fórmula funciona, y una jornada sin jugar cuenta como 0 en la "
         "media (no se salta). El error del 1% es ruido de redondeo.")
L.append("")
L.append("**Ejemplo con Tavares (J1):**")
L.append("- Precio: 637.500 € · Partidos: 1 · Suma de valoraciones: 10,8.")
L.append("- `X_mantiene = 637.500 × 2 / 50.000 − 10,8 = 14,7`.")
L.append("- `X_sube_15 = 637.500 × 1,15 × 2 / 50.000 − 10,8 = 18,5`.")
L.append("- `X_baja_15 = 637.500 × 0,85 × 2 / 50.000 − 10,8 = 10,9`.")
L.append("")

# --- 7. Pronóstico ---
L.append("### 7. Pronóstico por probabilidades")
L.append("")
L.append("El pronóstico ya no compara un punto con un umbral: se basa en las probabilidades.")
L.append("")
L.append("| Pronóstico | Condición |")
L.append("|:----------:|-----------|")
L.append("| ↑↑ Sube 15% | P(↑15%) ≥ 50% |")
L.append("| ↑ Sube | 25% ≤ P(↑15%) < 50% |")
L.append("| ≈ Se mantiene | P(↑15%) < 25% y P(↓15%) < 25% |")
L.append("| ↓ Baja | 25% ≤ P(↓15%) < 50% |")
L.append("| ↓↓ Baja 15% | P(↓15%) ≥ 50% |")
L.append("")

# --- 8. Score ---
L.append("### 8. Score del optimizador")
L.append("")
L.append("El optimizador maximiza:")
L.append("")
L.append("```")
L.append(f"score = pts_final + {PESO_REVAL:.2f} × reval_euros / 100.000")
L.append("```")
L.append("")
L.append(f"En J{jornada_num}, cada 100.000 € de reval valen **{PESO_REVAL:.2f} puntos** en el score. "
         f"El peso broker decae con las jornadas: en J1 vale {config.PESO_REVAL_INICIAL}, "
         f"en J{config.JORNADAS_DECAIMIENTO}+ vale {config.PESO_REVAL_FINAL}.")
L.append("")

# --- 9. Restricciones ---
L.append("### 9. Restricciones")
L.append("")
L.append("El solver `pulp` busca la combinación de 4 cambios (ventas + fichajes) que maximiza "
         "el score total, sujeto a:")
L.append("")
L.append("- 2 bases, 4 aleros, 4 pívots.")
L.append("- Máximo 2 extracomunitarios.")
L.append("- Mínimo 4 formados localmente.")
L.append("- Caja + ventas − compras ≥ 0 (nunca negativa).")
L.append("- Máximo 4 cambios en total.")
L.append("- Si `FORZAR_VENTA_LESIONADOS`, todo jugador con `injuredDays > 0` o `fisicStatus != 'fit'` "
         "se vende obligatoriamente.")
L.append("")

# --- 10. Frontera Pareto ---
L.append("### 10. Frontera puntos vs. broker")
L.append("")
L.append("El optimizador tiene un dilema: no puede maximizar puntos y broker a la vez. "
         "Para verlo, se ejecuta con varios pesos del broker. Cada fila de la tabla muestra "
         "qué cambios haría con ese peso. Sirve para ver si la recomendación es **robusta** "
         "(mismos jugadores en varias filas) o sensible al peso.")
L.append("")

# --- 11. Sensibilidad ---
L.append("### 11. Sensibilidad al histórico")
L.append("")
L.append("El modelo se ejecuta también con distintos valores de `SUAVIZADO_JORNADAS`. "
         "Si el top de candidatos es parecido en todos los valores, el modelo es robusto. "
         "Si cambia mucho, la decisión de cuánto histórico usar importa.")
L.append("")

# --- 12. Pesos dinámicos ---
L.append("### 12. Pesos dinámicos por jornada")
L.append("")
L.append("| Jornada | Peso broker | Peso v2 |")
L.append("|---------|------------:|--------:|")
L.append(f"| J1 | {config.PESO_REVAL_INICIAL:.2f} | {peso_v2_para(1):.3f} |")
L.append(f"| J3 | {PESO_REVAL:.2f} | {peso_v2_para(3):.3f} |")
L.append(f"| J5 | {config.PESO_REVAL_FINAL + (config.PESO_REVAL_INICIAL - config.PESO_REVAL_FINAL) * (1 - 4 / (config.JORNADAS_DECAIMIENTO - 1)):.2f} | {peso_v2_para(5):.3f} |")
L.append(f"| J10 | {config.PESO_REVAL_FINAL:.2f} | {peso_v2_para(10):.3f} |")
L.append("")

# --- 13. Glosario ---
L.append("### 13. Glosario")
L.append("")
L.append("| Término | Significado |")
L.append("|---------|-------------|")
L.append("| **Valoración** | Puntos Supermanager (fórmula arriba). |")
L.append("| **Pts esp.** | Media esperada de la valoración en la próxima jornada. |")
L.append("| **P(↑15%)** | Probabilidad estimada de subir el 15% (tope máximo). |")
L.append("| **P(↓15%)** | Probabilidad estimada de bajar el 15% (tope mínimo). |")
L.append("| **Reval. €** | Variación esperada del precio, en euros (media de la distribución). |")
L.append("| **Score** | Valor que el optimizador maximiza. |")
L.append("| **W** | Peso de la temporada actual vs el histórico. |")
L.append("| **PPM** | Puntos por minuto (valoración / minutos). |")
L.append("| **P(ganar)** | Probabilidad de que gane el equipo. |")
L.append("| **K** | Euros por punto de media (50.000). |")
L.append("| **EXT** | Extracomunitario (máx. 2). |")
L.append("| **JFL** | Formado localmente (mín. 4). |")
L.append("| **v1** | Modelo basado en puntos históricos. |")
L.append("| **v2** | Modelo basado en minutos. |")
L.append("| **Blend** | Mezcla ponderada de v1 y v2. |")
L.append("| **Pareto** | Exploración del óptimo con distintos pesos de broker. |")
L.append("| **Sensibilidad** | Exploración del óptimo con distintos pesos de histórico. |")
L.append("| **MAE** | Error medio absoluto (métrica del backtest). |")
L.append("| **Monte Carlo** | Simulación de la distribución de valoración del próximo partido. |")
L.append("")

# --- 14. Limitaciones ---
L.append("### 14. Limitaciones conocidas")
L.append("")
L.append("- El modelo **no usa racha ni estado de forma a corto plazo** (solo media).")
L.append("- La **probabilidad de victoria** se estima con win% + localía, sin tener en cuenta "
         "bajas, enfrentamientos previos, ni el rival concreto.")
L.append("- Los **jugadores sin histórico** usan `initialPrice / 50.000` como estimación.")
L.append("- **El factor de cambio de equipo** es una aproximación: no detecta jugadores que "
         "cambian de rol sin cambiar de equipo.")
L.append("- La **desviación típica** de la valoración (4.5 + 0.25 × mu) está ajustada "
         "empíricamente sobre 2025-26; no es una ley universal.")
L.append("- El **backtest sobre 2025-26** es la mejor validación disponible, pero no garantiza "
         "los mismos resultados en 2026-27.")
L.append("- El **reval. € es una media de una distribución**, no una promesa. La varianza "
         "real puede ser grande.")

# ═══════════════════════════════════════════════════════════
# GUARDAR
# ═══════════════════════════════════════════════════════════
Path("informes").mkdir(exist_ok=True)
fecha = datetime.now().strftime("%Y-%m-%d")
ruta_md = Path("informes") / f"informe_{JORNADA}_{fecha}.md"
contenido_md = "\n".join(L)
ruta_md.write_text(contenido_md, encoding="utf-8")

html_body = md_lib.markdown(
    contenido_md,
    extensions=["tables", "fenced_code", "toc", "nl2br"],
)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Informe Supermanager ACB — {jornada}</title>
<style>
  :root {{
    --bg: #0f1115; --fg: #e6e6e6; --muted: #a0a0a0;
    --accent: #ff6b35; --card: #1a1d24; --border: #2a2d36;
    --good: #4ade80; --bad: #f87171; --warn: #fbbf24;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--fg);
    max-width: 1100px; margin: 0 auto; padding: 32px 24px;
    line-height: 1.6;
  }}
  h1 {{ color: var(--accent); border-bottom: 2px solid var(--accent); padding-bottom: 12px; }}
  h2 {{ color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-top: 40px; }}
  h3 {{ color: var(--fg); margin-top: 28px; }}
  a {{ color: var(--accent); }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 32px 0; }}
  table {{
    width: 100%; border-collapse: collapse; margin: 16px 0;
    background: var(--card); border-radius: 6px; overflow: hidden;
    font-size: 14px;
  }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #22252d; color: var(--accent); font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover {{ background: #1f2229; }}
  code {{
    background: var(--card); padding: 2px 6px; border-radius: 4px;
    font-family: "SF Mono", Consolas, monospace; font-size: 0.9em;
    color: var(--warn);
  }}
  pre {{
    background: var(--card); padding: 16px; border-radius: 6px;
    overflow-x: auto; border-left: 3px solid var(--accent);
  }}
  pre code {{ background: none; padding: 0; color: var(--fg); }}
  blockquote {{
    border-left: 4px solid var(--warn); margin: 16px 0;
    padding: 8px 16px; background: rgba(251,191,36,0.08);
    border-radius: 4px; color: var(--muted);
  }}
  ul, ol {{ padding-left: 24px; }}
  strong {{ color: #fff; }}
  em {{ color: var(--muted); }}
  @media print {{
    body {{ background: #fff; color: #000; max-width: 100%; }}
    h1, h2, h3 {{ color: #000; }}
    table {{ background: #fff; }}
    th {{ background: #f0f0f0; color: #000; }}
    tr:hover {{ background: transparent; }}
    pre, code, blockquote {{ background: #f5f5f5; }}
    a {{ color: #000; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

ruta_html = Path("informes") / f"informe_{JORNADA}_{fecha}.html"
ruta_html.write_text(
    HTML_TEMPLATE.format(jornada=JORNADA, body=html_body),
    encoding="utf-8",
)

print(f"  Informe MD:   {ruta_md}")
print(f"  Informe HTML: {ruta_html}")