"""
Pipeline completo del Supermanager ACB.

Uso:
    python src/run.py

Flags en config.py:
  - SCRAPEAR_RINCON: si True, ejecuta el scraper de El Rincón antes.
  - EXPLORAR_SUAVIZADO_EN_RUN: si True, ejecuta la exploración de suavizado.
"""
import os
import subprocess
import sys
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, "src")
import config

SCRIPTS_BASE = [
    "src/01_snapshot.py",
    "src/02_mi_caja.py",
    "src/03_mi_equipo.py",
    "src/04_prediccion.py",
    "src/05_minutos_features.py",
    "src/06_modelo_minutos.py",
    "src/07_optimizador.py",
]

if config.EXPLORAR_SUAVIZADO_EN_RUN:
    SCRIPTS_BASE.append("src/08_explorar_suavizado.py")

SCRIPTS_BASE.append("src/09_informe.py")

if config.SCRAPEAR_RINCON:
    SCRIPTS = ["src/manual/scrape_rincon.py"] + SCRIPTS_BASE
else:
    SCRIPTS = SCRIPTS_BASE


def main():
    print("=" * 62)
    print("  PIPELINE SUPERMANAGER ACB")
    extras = []
    if config.SCRAPEAR_RINCON:
        extras.append("scraper Rincón")
    if config.EXPLORAR_SUAVIZADO_EN_RUN:
        extras.append("exploración suavizado")
    if extras:
        print(f"  extras: {', '.join(extras)}")
    print("=" * 62)

    for i, script in enumerate(SCRIPTS, 1):
        print(f"\n[{i}/{len(SCRIPTS)}] {script}")
        r = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        for linea in r.stdout.splitlines():
            print(f"  {linea}")
        if r.returncode != 0:
            print(f"\n  ERROR en {script}")
            print(r.stderr)
            sys.exit(1)

    print("\n" + "=" * 62)
    print("  Pipeline completado")
    print("=" * 62)
    informes = sorted(Path("informes").glob("informe_*.md"))
    if informes:
        print(f"  Informe: {informes[-1]}")


if __name__ == "__main__":
    main()