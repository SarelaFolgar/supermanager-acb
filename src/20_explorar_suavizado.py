"""
20_explorar_suavizado.py

Ejecuta 13_prediccion_global.py con varios valores de SUAVIZADO_JORNADAS
y compara cómo cambian los 6 mejores candidatos.

IMPORTANTE: guarda y restaura data/prediccion_global.csv para no dejar
el pipeline con el último SUAVIZADO explorado.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
import config


def ejecutar_13(suavizado):
    r = subprocess.run(
        [sys.executable, "src/13_prediccion_global.py", str(suavizado)],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        print(f"  ERROR con SUAVIZADO={suavizado}")
        print(r.stderr[-500:])
        return None
    if "SUAVIZADO override" not in r.stdout:
        print(f"  AVISO: el override no se aplicó para SUAVIZADO={suavizado}")
    return pd.read_csv("data/prediccion_global.csv")


def main():
    ruta_pred = Path("data/prediccion_global.csv")
    if not ruta_pred.exists():
        print("  ERROR: no existe data/prediccion_global.csv")
        return
    ruta_backup = Path("data/_prediccion_global_backup.csv")
    shutil.copy(ruta_pred, ruta_backup)

    with open("data/mi_equipo/plantilla_actual.csv", encoding="utf-8") as f:
        mis_ids = set(pd.read_csv(f)["idPlayer"].tolist())

    resultados = []
    medias_puntos = {}
    print(f"  Explorando SUAVIZADOS: {config.SUAVIZADOS_EXPLORADOS}")

    try:
        for s in config.SUAVIZADOS_EXPLORADOS:
            print(f"    -> SUAVIZADO = {s}")
            df = ejecutar_13(s)
            if df is None:
                continue

            medias_puntos[s] = float(df["puntos_esperados_J2"].mean())

            cand = df[
                (~df["idPlayer"].isin(mis_ids)) &
                (df["injuredDays"] == 0) &
                (df["fisicStatus"] == "fit")
            ].copy()

            n_part = 2
            w_ref = n_part / (n_part + s)

            top = cand.nlargest(10, "puntos_esperados_J2")[
                ["shortName", "nameTeam", "position", "puntos_esperados_J2"]
            ].reset_index(drop=True)

            resultados.append({
                "suavizado": s,
                "w_j2": round(w_ref, 3),
                "top": top.to_dict("records"),
            })
    finally:
        shutil.copy(ruta_backup, ruta_pred)
        ruta_backup.unlink()

    # Comprobación: ¿los resultados difieren entre SUAVIZADOS?
    valores_unicos = set(round(m, 4) for m in medias_puntos.values())
    if len(valores_unicos) <= 1:
        print(f"\n  ERROR: todos los SUAVIZADOS dan la misma media de puntos "
              f"({list(medias_puntos.values())[0]:.4f}). El override NO funciona.")
    else:
        print(f"\n  Medias de puntos_esperados por SUAVIZADO (deben ser distintas):")
        for s, m in medias_puntos.items():
            print(f"    SUAVIZADO={s}: {m:.4f}")

    filas = []
    for r in resultados:
        fila = {"suavizado": r["suavizado"], "w_j2": r["w_j2"]}
        for i, j in enumerate(r["top"][:6], 1):
            fila[f"top{i}"] = f"{j['shortName']} ({j['puntos_esperados_J2']:.1f})"
        filas.append(fila)

    df_tabla = pd.DataFrame(filas)
    df_tabla.to_csv("data/exploracion_suavizado.csv", index=False)

    with open("data/exploracion_suavizado_full.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n  Guardado: data/exploracion_suavizado.csv")


if __name__ == "__main__":
    main()