"""
descargar_acb.py

Descarga los CSVs del repo pbp_acb_historico de Ivo Villanueva.
"""
import time
from pathlib import Path

import requests

# ─── CONFIGURACIÓN ──────────────────────────────────────────
AÑOS_BOXSCORE = [2022, 2023, 2024, 2025]
AÑOS_STATS_EQUIPOS = [2022, 2023, 2024, 2025]

DESCARGAR_CALENDARIO = True
DESCARGAR_HORARIOS = True

REPO = "IvoVillanueva/pbp_acb_historico"
BRANCH = "main"
BASE_RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
SALIDA = Path("data/acb")
PAUSA = 0.5


def descargar(ruta_repo, destino, opcional=False):
    url = BASE_RAW + ruta_repo
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"  ERROR de red en {ruta_repo}: {e}")
        return False

    if r.status_code == 404:
        if not opcional:
            print(f"  NO EXISTE: {ruta_repo}")
        return False
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}: {ruta_repo}")
        return False

    with open(destino, "wb") as f:
        f.write(r.content)
    kb = len(r.content) / 1024
    print(f"  OK  {ruta_repo}")
    print(f"      -> {destino} ({kb:.1f} KB)")
    return True


def main():
    print(f"  Descargando de {REPO} (rama {BRANCH})")
    print(f"  Destino: {SALIDA}")
    print()

    # === Sueltos ===
    if DESCARGAR_CALENDARIO:
        print("  [Calendario histórico]")
        descargar("data/calendario_historico.csv",
                  SALIDA / "calendario_historico.csv")
        time.sleep(PAUSA)

    print("  [Mapeo de jornadas]")
    descargar("data/ids_partidos_historico.csv",
              SALIDA / "ids_partidos_historico.csv")
    time.sleep(PAUSA)

    if DESCARGAR_HORARIOS:
        print("  [Horarios temporada en curso]")
        descargar("data/horarios.csv",
                  SALIDA / "horarios.csv")
        time.sleep(PAUSA)

    # === Boxscores ===
    print(f"\n  [Boxscores: {len(AÑOS_BOXSCORE)} temporadas]")
    n_ok = 0
    for a in AÑOS_BOXSCORE:
        ruta = f"data_boxscores/boxscore_acb_{a}.csv"
        destino = SALIDA / "boxscores" / f"boxscore_acb_{a}.csv"
        if descargar(ruta, destino, opcional=True):
            n_ok += 1
        time.sleep(PAUSA)
    print(f"  {n_ok} / {len(AÑOS_BOXSCORE)} boxscores descargados")

    # === Stats equipos ===
    print(f"\n  [Stats equipos: {len(AÑOS_STATS_EQUIPOS)} temporadas]")
    n_ok = 0
    for a in AÑOS_STATS_EQUIPOS:
        ruta = f"data_stats_equipos/stats_equipos_acb_{a}.csv"
        destino = SALIDA / "stats_equipos" / f"stats_equipos_acb_{a}.csv"
        if descargar(ruta, destino, opcional=True):
            n_ok += 1
        time.sleep(PAUSA)
    print(f"  {n_ok} / {len(AÑOS_STATS_EQUIPOS)} stats equipos descargados")

    print()
    print(f"  Descarga completada en {SALIDA}")


if __name__ == "__main__":
    main()