"""
Pipeline completo del Supermanager ACB.
Uso:
    python src/run.py
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "src/06_snapshot.py",
    "src/15_mi_caja.py",
    "src/10_mi_equipo.py",
    "src/13_prediccion_global.py",
    "src/14_optimizador.py",
    "src/informe.py",
]


def main():
    print("=" * 62)
    print("  PIPELINE SUPERMANAGER ACB")
    print("=" * 62)
    for i, script in enumerate(SCRIPTS, 1):
        print(f"\n[{i}/{len(SCRIPTS)}] ▶ {script}")
        print("-" * 62)
        r = subprocess.run([sys.executable, script])
        if r.returncode != 0:
            sys.exit(f"\n❌ Falló {script}. Se aborta el pipeline.")

    print("\n" + "=" * 62)
    print("  ✅ Pipeline completado")
    print("=" * 62)
    informes = sorted(Path("informes").glob("informe_*.md"))
    if informes:
        print(f"  Informe: {informes[-1]}")


if __name__ == "__main__":
    main()