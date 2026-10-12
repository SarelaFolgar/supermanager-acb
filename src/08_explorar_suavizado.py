"""
08_explorar_suavizado.py

Ejecuta 04_prediccion.py + 07_optimizador.py con varios valores de
SUAVIZADO_JORNADAS. Guarda quién vender y quién fichar en cada caso.

Al terminar, restaura:
  data/procesado/prediccion_global.csv   (con SUAVIZADO del config)
  data/procesado/prediccion_v2.csv       (dependiente)
  data/mi_equipo/cambios.csv             (con SUAVIZADO del config)
  data/mi_equipo/pareto.csv              (con SUAVIZADO del config)
  data/mi_equipo/zona_estable.json       (con SUAVIZADO del config)

Salidas:
  data/procesado/exploracion_suavizado.csv
  data/procesado/exploracion_suavizado_full.json
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
import config


def ejecutar(script, *args, silencioso=True):
    r = subprocess.run(
        [sys.executable, script, *args],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        print(f"  ERROR en {script} {args}")
        print(r.stderr[-500:])
        return False
    return True


def backup(ruta):
    if ruta.exists():
        bak = ruta.with_name("_" + ruta.name + ".bak")
        shutil.copy(ruta, bak)
        return bak
    return None


def restore(ruta, bak):
    if bak and bak.exists():
        shutil.copy(bak, ruta)
        bak.unlink()


def main():
    ruta_pred = Path("data/procesado/prediccion_global.csv")
    ruta_v2 = Path("data/procesado/prediccion_v2.csv")
    ruta_cambios = Path("data/mi_equipo/cambios.csv")
    ruta_pareto = Path("data/mi_equipo/pareto.csv")
    ruta_zona = Path("data/mi_equipo/zona_estable.json")

    if not ruta_pred.exists():
        print("  ERROR: no existe data/procesado/prediccion_global.csv")
        return

    # Backups de todo lo que el pipeline va a sobrescribir
    b_pred = backup(ruta_pred)
    b_v2 = backup(ruta_v2)
    b_cambios = backup(ruta_cambios)
    b_pareto = backup(ruta_pareto)
    b_zona = backup(ruta_zona)

    pred_orig = pd.read_csv(ruta_pred)
    n_part = int(pred_orig["partidos_actual"].max()) if "partidos_actual" in pred_orig.columns else 2

    resultados = []
    medias_puntos = {}
    print(f"  Explorando SUAVIZADOS: {config.SUAVIZADOS_EXPLORADOS}")
    print(f"  Partidos jugados detectados: {n_part}")

    try:
        for s in config.SUAVIZADOS_EXPLORADOS:
            print(f"\n    -> SUAVIZADO = {s}")
            if not ejecutar("src/04_prediccion.py", str(s)):
                continue

            df_pred = pd.read_csv(ruta_pred)
            medias_puntos[s] = float(df_pred["puntos_esperados"].mean())

            # Regenerar v2 (depende de la predicción)
            if not ejecutar("src/05_minutos_features.py"):
                continue
            if not ejecutar("src/06_modelo_minutos.py"):
                continue

            # Optimizador (completo, con Pareto)
            if not ejecutar("src/07_optimizador.py"):
                continue

            cambios = pd.read_csv(ruta_cambios)
            if cambios.empty or "accion" not in cambios.columns:
                vender = []
                fichar = []
            else:
                vender = cambios[cambios["accion"] == "vender"]["shortName"].tolist()
                fichar = cambios[cambios["accion"] == "fichar"]["shortName"].tolist()

            w_ref = n_part / (n_part + s)
            resultados.append({
                "suavizado": s,
                "n_partidos": n_part,
                "w": round(w_ref, 3),
                "vender": vender,
                "fichar": fichar,
            })
            print(f"       Vender: {', '.join(vender) if vender else '—'}")
            print(f"       Fichar: {', '.join(fichar) if fichar else '—'}")
    finally:
        # Restaurar el estado original (con el SUAVIZADO del config)
        restore(ruta_pred, b_pred)
        restore(ruta_v2, b_v2)
        restore(ruta_cambios, b_cambios)
        restore(ruta_pareto, b_pareto)
        restore(ruta_zona, b_zona)

    filas = []
    for r in resultados:
        filas.append({
            "suavizado": r["suavizado"],
            "n_partidos": r["n_partidos"],
            "w": r["w"],
            "vender": ", ".join(r["vender"]) if r["vender"] else "—",
            "fichar": ", ".join(r["fichar"]) if r["fichar"] else "—",
        })
    df_tabla = pd.DataFrame(filas)
    df_tabla.to_csv("data/procesado/exploracion_suavizado.csv", index=False)

    with open("data/procesado/exploracion_suavizado_full.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    valores_unicos = set(round(m, 4) for m in medias_puntos.values())
    if len(valores_unicos) <= 1:
        print(f"\n  ERROR: todos los SUAVIZADOS dan la misma media de puntos.")
    else:
        print(f"\n  Medias de puntos_esperados por SUAVIZADO (deben ser distintas):")
        for s, m in medias_puntos.items():
            print(f"    SUAVIZADO={s}: {m:.4f}")

    print(f"\n  Guardado: data/procesado/exploracion_suavizado.csv")
    print(f"  Estado del pipeline restaurado a SUAVIZADO={config.SUAVIZADO_JORNADAS}")


if __name__ == "__main__":
    main()