Supermanager ACB 2026-27 — Informe y optimizador de cambios
Repositorio personal para el juego Supermanager ACB. Genera, antes de cada jornada, un informe en Markdown y HTML con los 4 mejores cambios para tu equipo, combinando el mercado actual, tus datos de cuenta, el calendario, los minutos reales de la temporada y un modelo probabilístico de puntos y revalorización validado con backtest sobre 2025-26.

Índice
Objetivo

Reglas del juego

Cómo se ve un informe

Instalación

Uso diario

Estructura del repositorio

Scripts

Configuración

Cómo funciona el modelo

Backtest y validaciones

Pesos dinámicos

Fuentes de datos

Hallazgos clave

Limitaciones

Glosario

1. Objetivo
Construir un sistema que, antes de cada jornada del Supermanager ACB, genere un informe con los 4 mejores cambios para tu equipo. El informe debe:

Tener en cuenta tu cuenta: plantilla actual, caja, cupos y lesiones.

Considerar el mercado completo (~250 jugadores), no solo tu plantilla.

Calcular puntos esperados para cada jugador (mezcla de histórico 2025-26 y temporada actual).

Calcular revalorización esperada mediante simulación Monte Carlo.

Optimizar bajo las restricciones del juego: 2 bases / 4 aleros / 4 pívots, máximo 2 extracomunitarios, mínimo 4 locales, saldo no negativo, máximo 4 cambios.

Priorizar el broker al inicio (cuando tu caja es escasa) y los puntos al final (cuando la plantilla está consolidada).

Un solo comando hace todo el pipeline y genera el informe en Markdown + HTML.

Meta: ganar la liga privada con amigos.

2. Reglas del juego
Regla	Detalle
Presupuesto inicial	5.000.000 €
Plantilla	2 bases, 4 aleros, 4 pívots (10 jugadores)
Cupos	Máx. 2 extracomunitarios, mín. 4 formados localmente
Cambios	4 por jornada
Saldo	Nunca negativo
Puntuación	Valoración ACB. +20% si gana el equipo (solo si valoración > 0)
Precio	50.000 € × media_acumulada con tope ±15% por jornada
Clasificaciones	Jornada, general y Brokerbasket (valor + caja)
La valoración ACB se calcula:

text
valoración = PTS + asistencias + rebotes + tapones a favor + robos
           + faltas recibidas + T1C + T2C + T3C
           − pérdidas − tapones en contra − faltas personales
           − T1I − T2I − T3I
3. Cómo se ve un informe
El informe tiene dos salidas:

informes/informe_JX_AAAA-MM-DD.md — Markdown, para VS Code.

informes/informe_JX_AAAA-MM-DD.html — HTML autocontenido con tema oscuro, para abrir en navegador o compartir.

Secciones:

Cambios recomendados (vender + fichar) con probabilidades, reval. € y motivo.

Resumen económico y proyección económica.

Impacto en puntos.

Ranking de subidas (top 15 por reval en euros).

Frontera puntos vs. broker (Pareto con distintos pesos).

Sensibilidad al histórico (top 6 candidatos con distintos SUAVIZADO).

Plantilla actual con decisión de vender/mantener.

Plantilla resultante.

Verificación de reglas (cupos, posiciones, saldo).

Cómo funciona el modelo — 14 subsecciones explicando cada número.

Cada tabla va acompañada de una explicación de cómo leerla.

4. Instalación
Requisitos
Python 3.11+

Git

VS Code (recomendado)

Pasos
powershell
git clone https://github.com/SarelaFolgar/supermanager-acb.git
cd supermanager-acb
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
mkdir data, src, informes
Token del Supermanager
Crea .env en la raíz (nunca se sube):

text
SM_TOKEN=Bearer eyJhbGciOi...
Cómo conseguirlo:

Abre supermanager.acb.com con DevTools (F12).

Network → Fetch/XHR.

Pincha cualquier llamada a /api/basic/....

Request Headers → copia el valor completo de Authorization.

El token caduca cada pocos días. Si la API responde 401 o 403, repite.

ID de tu equipo
Edita src/config.py:

python
MI_EQUIPO_ID = 246638
Cómo conseguirlo: DevTools → busca userteamplayer/journeys/XXXXXX.

Datos históricos (una sola vez)
Descarga los CSV de Ivo Villanueva:

powershell
curl.exe -o data/jugadores_2526.csv https://raw.githubusercontent.com/IvoVillanueva/DATOS-JUGADORES-SUPERMANAGER-2025_26/main/data/supermanager_juagadores_2026.csv
curl.exe -o data/stats_jornada_2526.csv https://raw.githubusercontent.com/IvoVillanueva/DATOS-JUGADORES-SUPERMANAGER-2025_26/main/data/supermanager_juagadores_stats_2026.csv
Y el mapeo de logos (una sola vez, o cuando cambie):

powershell
python src/exploratorio/11_mapeo_equipos.py
5. Uso diario
Un solo comando
powershell
cd "ruta\al\repo"
.venv\Scripts\Activate.ps1
python src/run.py
Esto ejecuta el pipeline completo y genera el informe. Tarda ~1-2 minutos (incluye exploración de suavizado).

Cuando quieras refrescar minutos
Los minutos vienen de El Rincón del Supermanager y tardan ~5 minutos. Se activa con:

python
# config.py
SCRAPEAR_RINCON = True
Y luego:

powershell
python src/run.py
O directamente:

powershell
python src/16_rincon_scraper.py
python src/run.py
Hazlo una vez por jornada, después de que se jueguen los partidos.

Ver el informe
Markdown: abre el .md en VS Code y Ctrl+Shift+V.

HTML: clic derecho sobre el .html → abrir con navegador. O start informes\informe_JX_AAAA-MM-DD.html.

Validar la regla de precios (opcional)
powershell
python src/21_validar_precios.py
Compara precios reales con la fórmula oficial. Útil cuando hay capturas nuevas.

6. Estructura del repositorio
text
supermanager-acb/
├── .env                          # SM_TOKEN (NUNCA se sube)
├── .gitignore
├── README.md
├── requirements.txt
├── data/
│   ├── stats_jornada_2526.csv    # Histórico detallado 2025-26
│   ├── jugadores_2526.csv        # Resumen 2025-26
│   ├── equipos_logos.csv         # Mapa logo → equipo
│   ├── prediccion_global.csv     # v1 + modelo probabilístico
│   ├── prediccion_con_minutos.csv
│   ├── prediccion_v2.csv         # v2 (minutos)
│   ├── exploracion_suavizado.csv
│   ├── backtest_resumen.csv
│   ├── rincon/
│   │   └── minutos_actual.csv
│   ├── mercado/
│   │   └── mercado_AAAA-MM-DD.csv
│   ├── raw/
│   │   └── mercado_AAAA-MM-DD.json
│   └── mi_equipo/
│       ├── plantilla_actual.csv
│       ├── jornada_1_puntos.csv
│       ├── caja.json
│       ├── cambios.csv
│       └── pareto.csv
├── informes/
│   ├── informe_JX_AAAA-MM-DD.md
│   └── informe_JX_AAAA-MM-DD.html
└── src/
    ├── config.py
    ├── 06_snapshot.py
    ├── 10_mi_equipo.py
    ├── 13_prediccion_global.py
    ├── 14_optimizador.py
    ├── 15_mi_caja.py
    ├── 16_rincon_scraper.py
    ├── 17_minutos_features.py
    ├── 18_modelo_minutos.py
    ├── 19_backtest.py
    ├── 20_explorar_suavizado.py
    ├── 21_validar_precios.py
    ├── informe.py
    ├── run.py
    └── exploratorio/
        ├── 01_explorar.py
        ├── 02_rentabilidad.py
        ├── 03_revalorizacion.py
        ├── 04_features.py
        ├── 05_mercado.py
        ├── 07_ver_stats.py
        ├── 08_jornada.py
        ├── 09_prediccion_precios.py
        ├── 11_mapeo_equipos.py
        └── 12_historico.py
7. Scripts
Pipeline principal (van en run.py)
Script	Función
06_snapshot.py	Descarga el mercado actual
15_mi_caja.py	Caja, valor y posición desde /userteam/all
10_mi_equipo.py	Plantilla actual, cupos, rivales
13_prediccion_global.py	Modelo v1 + probabilístico. Genera prediccion_global.csv
17_minutos_features.py	Cruza el modelo con minutos de El Rincón
18_modelo_minutos.py	Modelo v2. Genera prediccion_v2.csv
14_optimizador.py	Optimiza los 4 cambios con pulp. Genera cambios.csv y pareto.csv
20_explorar_suavizado.py	Prueba distintos SUAVIZADO (opcional, activable en config)
informe.py	Genera informe MD + HTML
Scripts manuales
Script	Función
16_rincon_scraper.py	Scrapea minutos de El Rincón (~5 min)
19_backtest.py	Backtest sobre 2025-26 (6.261 predicciones)
21_validar_precios.py	Valida la fórmula de precios
exploratorio/*	Scripts antiguos de exploración
8. Configuración
Todo en src/config.py. Los parámetros clave:

python
# Equipo
MI_EQUIPO_ID = 246638
SCRAPEAR_RINCON = False
EXPLORAR_SUAVIZADO_EN_RUN = True

# Reglas
MAX_CAMBIOS = 4
POSICIONES = {1: 2, 3: 4, 5: 4}
MIN_LOCALES = 4
MAX_EXTRA = 2

# Optimizador
FORZAR_VENTA_LESIONADOS = True
TOP_POR_POSICION = 100
UMBRAL_MINIMO_CAMBIO = 0.5

# Broker vs puntos (peso lineal decreciente)
PESO_REVAL_INICIAL = 15.0       # J1
PESO_REVAL_FINAL = 1.0          # J10+
JORNADAS_DECAIMIENTO = 10

# Modelo v1 vs v2
JORNADA_BLEND_INICIO = 2
JORNADA_V2_TECHO = 5
PESO_V2_FINAL = 0.10

# Modelo
SUAVIZADO_JORNADAS = 4
MIN_PARTIDOS_FACTOR_HIST = 3
FACTOR_HIST_CAMBIO_EQUIPO = 0.3

# Precios
K_PRECIO = 50000
TOPE_PRECIO = 0.15

# Modelo probabilístico
SD_BASE = 4.5
SD_ESCALA_MU = 0.25
N_SIMULACIONES = 4000
9. Cómo funciona el modelo
9.1 Puntos esperados (Pts esp.)
Paso 1 — peso de cada temporada:

text
W = partidos_jugados / (partidos_jugados + SUAVIZADO)
Con SUAVIZADO=4: J1 → 0,20; J2 → 0,33; J4 → 0,50; J5 → 0,56; J10 → 0,71; J20 → 0,83.

Paso 2 — factor histórico si cambió de equipo:

factor_hist = 0,3 si cambió de equipo y lleva ≥ 3 partidos en el nuevo.

factor_hist = 1,0 en cualquier otro caso.

peso_hist = (1 − W) × factor_hist, peso_actual = 1 − peso_hist.

Paso 3 — media sin bonus:

text
media_sin_bonus = peso_actual × media_actual + peso_hist × media_2526
Paso 4 — probabilidad de victoria:

text
p_win = sigmoide((fuerza_equipo − fuerza_rival) × 4 + localía × 5)
Paso 5 — bonus por victoria:

text
puntos_v1 = media_sin_bonus × (1 + 0,2 × p_win)
Paso 6 — blend con v2 (minutos):

text
puntos_final = (1 − peso_v2) × v1 + peso_v2 × v2
puntos_v2 = minutos_esperados × PPM_esperado × (1 + 0,2 × p_win)
peso_v2 sube de 0 (J1) a 0,10 (J5+). El backtest demostró que v1 y v2 predicen similar (MAE 5,58 vs 5,61), así que v2 es un corrector residual.

Jugadores sin histórico 2025-26: usan initialPrice / 50.000 como referencia, mezclado con la media actual usando la misma W.

9.2 Modelo probabilístico de revalorización
En vez de comparar un único punto con el umbral, simulamos la distribución de la valoración del próximo partido:

text
valoración_simulada ~ Normal(mu = pts_esperados, sd = 4.5 + 0.25 × mu)
objetivo = 50.000 × (S + valoración_simulada) / (N + 1)
precio_nuevo = clip(objetivo, precio × 0.85, precio × 1.15)
Con 4.000 simulaciones por jugador:

Reval. € = media de la variación.

P(↑15%) = fracción donde toca el techo del 15%.

P(↓15%) = fracción donde toca el suelo del −15%.

La desviación típica 4.5 + 0.25 × mu está ajustada empíricamente sobre 2025-26.

9.3 Umbrales de precio
Fórmula oficial:

text
precio_nuevo = 50.000 × media_acumulada
media_acumulada = (suma de valoraciones) / (partidos jugados)
Con tope ±15%. Despejando:

text
X_mantiene = P × (N+1) / 50.000 − S
X_sube_15 = P × 1,15 × (N+1) / 50.000 − S
X_baja_15 = P × 0,85 × (N+1) / 50.000 − S
9.4 Score del optimizador
text
score = pts_final + PESO_REVAL × reval_euros / 100.000
El solver pulp maximiza Σ score_fichar − Σ score_vender sujeto a:

2/4/4 posiciones.

Máx. 2 extracomunitarios.

Mín. 4 locales.

Saldo ≥ 0.

Máx. 4 cambios.

Si FORZAR_VENTA_LESIONADOS, se venden obligatoriamente.

10. Backtest y validaciones
10.1 Backtest del SUAVIZADO
Sobre 2025-26 (34 jornadas, 6.261 predicciones). Método: dividir la temporada de cada jugador en "prior" (primeros 5 partidos) y "current" (partidos 6-34), predecir cada J usando solo datos hasta J−1.

Resultados:

SUAVIZADO	MAE	Correlación
2	5,592	0,453
3	5,578	0,455
4	5,575	0,456
6	5,584	0,454
8	5,600	0,451
Conclusión honesta: cualquier valor entre 3 y 6 es equivalente. Elegimos 4 por ser el más redondo.

Limitación: el backtest mide intratemporada, no año a año. No captura cambios de rol, equipo o edad entre temporadas.

10.2 Validación de la fórmula de precios
Reproducimos el precio actual desde initialPrice jornada a jornada y lo comparamos con el precio observado. Resultados:

Contar jornadas sin jugar	Error medio	Aciertos < 1%
Sí	1,05%	236 / 250
No	1,62%	231 / 250
Conclusión: la fórmula oficial funciona, y una jornada sin jugar cuenta como 0 en la media. El error del 1% es ruido de redondeo.

10.3 Backtest v1 vs v2
Sobre 2025-26 (6.261 predicciones): v1 puro MAE 5,576; v2 puro MAE 5,605. Diferencia ruido. Por eso v2 se usa solo como corrector residual (peso 10%).

11. Pesos dinámicos
11.1 Peso broker (PESO_REVAL)
Decae linealmente entre J1 (15.0) y J10 (1.0). Motivo:

En J1-J3 tu caja es escasa. Sin caja no puedes fichar. La única forma de conseguir caja es que tus jugadores suban de precio.

En J10+ la plantilla ya está consolidada. Importan más los puntos.

Equivalencia práctica: 100.000 € de reval valen ~2 puntos de media en el mercado.

No es un valor óptimo calculado. Es una heurística transparente y explicable. Un test empírico de "¿cuánto vale 1 punto de reval?" sería 2-3 tardes de trabajo y no está claro que merezca la pena.

11.2 Peso v2 (minutos)
Sube de 0 (J1) a 0,10 (J5+) y se queda fijo.

Jornada	Peso broker	Peso v2
J1	15,0	0,000
J2	13,4	0,000
J3	11,9	0,033
J4	10,3	0,067
J5+	8,8 → 1,0	0,100
12. Fuentes de datos
Fuente	Qué aporta	Uso
API Supermanager	Mercado, plantilla, caja	Principal
Ivo Villanueva (GitHub)	CSV detallados 2025-26	Histórico
El Rincón del Supermanager	Minutos 2026-27	Modelo v2
Endpoints API
GET /api/basic/player → mercado completo (~250 jugadores).

GET /api/basic/userteamplayer/journeys/{id} → plantilla.

GET /api/basic/userteam/all → caja, valor, posición.

13. Hallazgos clave
Sobre los datos de 2025-26
valueTimePlayed está en segundos (dividir por 60 para minutos).

"Partido jugado" = valueTimePlayed > 0.

pointsJourney de 2025-26 no incluye el bonus. En 2026-27 la API sí lo incluye.

Los IDs de jugador cambian cada temporada. Hay que cruzar por nick + birthdate.

Sobre los precios
Fórmula verificada empíricamente: precio = 50.000 × media_acumulada, con tope ±15%.

Las jornadas sin jugar cuentan como 0 en la media.

initialPrice refleja lo que la ACB esperaba del jugador.

Sobre la predicción
Los minutos son lo más estable (corr ~0,82 entre primeros y siguientes partidos).

Con pocas jornadas, la media es ruido. El modelo mezcla con histórico.

El bonus por victoria no se puede predecir con certeza: se estima con win% + localía.

Sobre el backtest
v1 y v2 predicen similar (MAE 5,58 vs 5,61).

SUAVIZADO entre 3 y 6 es equivalente.

La fórmula de precios es válida (error <1,1%).

14. Limitaciones
El modelo no usa racha ni estado de forma a corto plazo.

La probabilidad de victoria es tosca (win% + localía), sin bajas ni enfrentamientos previos.

Jugadores sin histórico usan initialPrice / 50.000 como estimación.

Factor de cambio de equipo no detecta cambios de rol sin cambio de equipo.

Peso broker es lineal, no óptimo calculado.

Backtest 2025-26 no garantiza los mismos resultados en 2026-27.

Token caduca cada pocos días.

Scraper de El Rincón tarda ~5 min y es frágil si cambia la web.

Reval. € es una media de una distribución, no una promesa.

15. Glosario
Término	Significado
Valoración	Puntos Supermanager (fórmula ACB).
Pts esp.	Media esperada de la valoración en la próxima jornada.
P(↑15%)	Probabilidad estimada de subir el 15% (tope máximo).
P(↓15%)	Probabilidad estimada de bajar el 15%.
Reval. €	Variación esperada del precio, en euros.
Score	Valor que el optimizador maximiza.
W	Peso de la temporada actual vs el histórico.
PPM	Puntos por minuto.
P(ganar)	Probabilidad de que gane el equipo.
K	Euros por punto (50.000).
EXT	Extracomunitario (máx. 2).
JFL	Formado localmente (mín. 4).
v1	Modelo basado en puntos históricos.
v2	Modelo basado en minutos.
Blend	Mezcla ponderada de v1 y v2.
Pareto	Exploración con distintos pesos de broker.
MAE	Error medio absoluto (métrica del backtest).
Licencia y créditos
Datos 2025-26: repos de Ivo Villanueva.

Minutos 2026-27: El Rincón del Supermanager.

Mercado y cuenta: API oficial del Supermanager ACB.

Última actualización: 5-oct-2026, tras añadir el modelo probabilístico, la validación empírica de precios y la limpieza del informe.