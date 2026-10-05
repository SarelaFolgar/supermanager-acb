"""
scrape_rincon.py — Descarga minutos y estadísticas por partido desde
El Rincón del Supermanager.

Fuente: https://www.rincondelmanager.com/smgr/jugador/<slug>
Salida: data/rincon/minutos_actual.csv
"""
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Permitir import de config desde src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}
BASE_URL = "https://www.rincondelmanager.com/smgr/jugador/"
PAUSA = 1.0
LIMITE = 0


def slug(nombre):
    if not nombre or pd.isna(nombre):
        return None
    s = str(nombre).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(c))
    s = re.sub(r"[\s\.]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or None


def numero_decimal(s):
    if s is None:
        return None
    s = str(s).replace(" ", "").strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def numero_entero(s):
    if s is None:
        return None
    s = str(s).replace(" ", "").replace(".", "").replace(",", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parsear_partidos(html):
    soup = BeautifulSoup(html, "lxml")
    partidos = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 11:
            continue
        primera = tds[0].get_text(strip=True)
        if not primera.isdigit():
            continue
        try:
            jornada = int(primera)
            rival = tds[1].get_text(strip=True)
            local_visitante = tds[2].get_text(strip=True)
            victoria = tds[3].get_text(strip=True)
            min_texto = tds[4].get_text(strip=True)
            pts = tds[5].get_text(strip=True)
            reb = tds[6].get_text(strip=True)
            asis = tds[7].get_text(strip=True)
            t3 = tds[8].get_text(strip=True)
            val = tds[9].get_text(strip=True)
            sm = tds[10].get_text(strip=True)
            broker = tds[11].get_text(strip=True) if len(tds) > 11 else ""
        except (IndexError, ValueError):
            continue

        minutos = None
        m = re.match(r"(\d+):(\d+)", min_texto)
        if m:
            minutos = int(m.group(1)) + int(m.group(2)) / 60.0

        partidos.append({
            "jornada": jornada,
            "rival": rival,
            "local_visitante": local_visitante,
            "victoria": victoria,
            "minutos_texto": min_texto,
            "minutos": round(minutos, 2) if minutos else None,
            "puntos": numero_decimal(pts),
            "rebotes": numero_decimal(reb),
            "asistencias": numero_decimal(asis),
            "triples": t3,
            "valoracion": numero_decimal(val),
            "sm": numero_decimal(sm),
            "broker": numero_entero(broker),
        })
    return partidos


def main():
    Path("data/rincon").mkdir(parents=True, exist_ok=True)

    pred = pd.read_csv("data/procesado/prediccion_global.csv")
    pred = pred[pred["fullName"].notna()].copy()
    pred["slug"] = pred["fullName"].apply(slug)
    pred = pred[pred["slug"].notna()].drop_duplicates(subset="slug")

    if LIMITE > 0:
        pred = pred.head(LIMITE)

    print(f"Jugadores a scrapear: {len(pred)}")

    filas = []
    errores = []
    for i, (_, r) in enumerate(pred.iterrows(), 1):
        url = BASE_URL + r["slug"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                errores.append((r["fullName"], f"HTTP {resp.status_code}"))
                continue
            partidos = parsear_partidos(resp.text)
            for p in partidos:
                p["idPlayer"] = r["idPlayer"]
                p["shortName"] = r["shortName"]
                p["fullName"] = r["fullName"]
                p["nameTeam"] = r["nameTeam"]
                filas.append(p)
            if i % 20 == 0:
                print(f"  {i}/{len(pred)} jugadores ({len(filas)} partidos)")
            time.sleep(PAUSA)
        except Exception as e:
            errores.append((r["fullName"], str(e)[:80]))
            continue

    if filas:
        df = pd.DataFrame(filas)
        df.to_csv("data/rincon/minutos_actual.csv", index=False)
        print(f"\nGuardado: {len(df)} filas -> data/rincon/minutos_actual.csv")
    else:
        print("\nNo se extrajo ningún partido.")

    if errores:
        print(f"\nErrores ({len(errores)}):")
        for nombre, err in errores[:20]:
            print(f"  {nombre}: {err}")


if __name__ == "__main__":
    main()