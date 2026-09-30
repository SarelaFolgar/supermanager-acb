"""Configuración del proyecto. Edita SOLO este archivo."""

# ─── MI EQUIPO ──────────────────────────────────────────────
MI_EQUIPO_ID = 246638

# ─── REGLAS DE LA LIGA ──────────────────────────────────────
MAX_CAMBIOS = 4
POSICIONES = {1: 2, 3: 4, 5: 4}
MIN_LOCALES = 4
MAX_EXTRA = 2

# ─── OPTIMIZADOR ────────────────────────────────────────────
FORZAR_VENTA_LESIONADOS = True
TOP_POR_POSICION = 100
PESO_REVALORIZACION = 0.10
UMBRAL_MINIMO_CAMBIO = 0.5

# ─── MODELO ─────────────────────────────────────────────────
# Suavizado bayesiano. W = partidos / (partidos + SUAVIZADO).
# Controla cuánto tarda la temporada actual en pesar más que el histórico.
# Con 4: J1 → 0.20, J2 → 0.33, J4 → 0.50, J8 → 0.67, J20 → 0.83.
# Se usa tanto para jugadores como para la fuerza de equipos.
SUAVIZADO_JORNADAS = 4

# Precio por punto de media (regla oficial).
K_PRECIO = 50000

# Tope de variación de precio entre jornadas.
TOPE_PRECIO = 0.15