"""Configuración del proyecto. Edita SOLO este archivo."""

# ─── MI EQUIPO ──────────────────────────────────────────────
MI_EQUIPO_ID = 246638
# 249063 SERGIO
# 246638 SARELA

# ─── SCRAPER DE EL RINCÓN ───────────────────────────────────
SCRAPEAR_RINCON = False
EXPLORAR_SUAVIZADO_EN_RUN = True

# Si True, run.py ejecuta 10b_guardar_stats.py para refrescar el histórico
# de stats detalladas de 2026-27. Tarda ~2 min. Ponlo a False para el día a
# día y a True una vez por jornada, cuando quieras refrescar el histórico.
SCRAPEAR_STATS = False

# Limita cuántos jugadores procesa el scraper de stats. 0 = todos.
# Útil para test rápido: pon 5 para probar sin esperar 2 minutos.
MAX_JUGADORES_STATS = 0

# ─── REGLAS DE LA LIGA ──────────────────────────────────────
MAX_CAMBIOS = 4
POSICIONES = {1: 2, 3: 4, 5: 4}
MIN_LOCALES = 4
MAX_EXTRA = 2

# ─── OPTIMIZADOR ────────────────────────────────────────────
FORZAR_VENTA_LESIONADOS = True
TOP_POR_POSICION = 100
UMBRAL_MINIMO_CAMBIO = 0.5

# ─── BROKER VS PUNTOS ───────────────────────────────────────
PESO_REVAL_INICIAL = 15.0
PESO_REVAL_FINAL = 1.0
JORNADAS_DECAIMIENTO = 10
PESOS_EXPLORADOS = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0]

# ─── MODELO v1 vs v2 ────────────────────────────────────────
JORNADA_BLEND_INICIO = 2
JORNADA_V2_TECHO = 5
PESO_V2_FINAL = 0.10

# ─── MODELO ─────────────────────────────────────────────────
SUAVIZADO_JORNADAS = 4
SUAVIZADOS_EXPLORADOS = [0, 2, 3, 4, 6, 8]
MIN_PARTIDOS_FACTOR_HIST = 3
FACTOR_HIST_CAMBIO_EQUIPO = 0.3
FACTOR_HIST_MISMO_EQUIPO = 1.0

K_PRECIO = 50000
TOPE_PRECIO = 0.15

# ─── MODELO PROBABILÍSTICO DE REVALORIZACIÓN ────────────────
# La valoración jornada a jornada no es un punto, es una distribución.
# Asumimos normal con media = puntos_esperados y desviación típica que
# crece con la media (ajuste empírico sobre 2025-26).
SD_BASE = 4.5
SD_ESCALA_MU = 0.25
N_SIMULACIONES = 4000