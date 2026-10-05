"""
08_explorar_suavizado.py

Ejecuta 04_prediccion.py con varios valores de SUAVIZADO_JORNADAS
y compara cómo cambian los 6 mejores candidatos.

Guarda y restaura data/procesado/prediccion_global.csv para no dejar el
pipeline con el último SUAVIZADO explorado.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
import config


def ejecutar_prediccion(suavizado):
    r = subprocess.run(
        [sys.executable, "src/04_prediccion.py", str(suavizado)],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        print(f"  ERROR con SUAVIZADO={suavizado}")
        print(r.stderr[-500:])
        return None
    if "SUAVIZADO override" not in r.stdout:
        print(f"  AVISO: el override no se aplicó para SUAVIZADO={suavizado}")
    return pd.read_csv("data/procesado/prediccion_global.csv")


def main():
    ruta_pred = Path("data/procesado/prediccion_global.csv")
    if not ruta_pred.exists():
        print("  ERROR: no existe data/procesado/prediccion_global.csv")
        return
    ruta_backup = Path("data/procesado/_prediccion_global_backup.csv")
    shutil.copy(ruta_pred, ruta_backup)

    with open("data/mi_equipo/plantilla_actual.csv", encoding="utf-8") as f:
        mis_ids = set(pd.read_csv(f)["idPlayer"].tolist())

    resultados = []
    medias_puntos = {}
    print(f"  Explorando SUAVIZADOS: {config.SUAVIZADOS_EXPLORADOS}")

    try:
        for s in config.SUAVIZADOS_EXPLORADOS:
            print(f"    -> SUAVIZADO = {s}")
            df = ejecutar_prediccion(s)
            if df is None:
                continue

            medias_puntos[s] = float(df["puntos_esperados"].mean())

            cand = df[
                (~df["idPlayer"].isin(mis_ids)) &
                (df["injuredDays"] == 0) &
                (df["fisicStatus"] == "fit")
            ].copy()

            n_part = 2
            w_ref = n_part / (n_part + s)

            top = cand.nlargest(10, "puntos_esperados")[
                ["shortName", "nameTeam", "position", "puntos_esperados"]
            ].reset_index(drop=True)

            resultados.append({
                "suavizado": s,
                "w": round(w_ref, 3),
                "top": top.to_dict("records"),
            })
    finally:
        shutil.copy(ruta_backup, ruta_pred)
        ruta_backup.unlink()

    valores_unicos = set(round(m, 4) for m in medias_puntos.values())
    if len(valores_unicos) <= 1:
        print(f"\n  ERROR: todos los SUAVIZADOS dan la misma media de puntos. El override NO funciona.")
    else:
        print(f"\n  Medias de puntos_esperados por SUAVIZADO (deben ser distintas):")
        for s, m in medias_puntos.items():
            print(f"    SUAVIZADO={s}: {m:.4f}")

    filas = []
    for r in resultados:
        fila = {"suavizado": r["suavizado"], "w": r["w"]}
        for i, j in enumerate(r["top"][:6], 1):
            fila[f"top{i}"] = f"{j['shortName']} ({j['puntos_esperados']:.1f})"
        filas.append(fila)

    df_tabla = pd.DataFrame(filas)
    df_tabla.to_csv("data/procesado/exploracion_suavizado.csv", index=False)

    with open("data/procesado/exploracion_suavizado_full.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n  Guardado: data/procesado/exploracion_suavizado.csv")


if __name__ == "__main__":
    main()