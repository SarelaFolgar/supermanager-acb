# supermanager-acb
Supermanager ACB 2026-27 — Informe y optimizador de cambios
Repositorio personal para el juego Supermanager ACB. Genera, antes de cada jornada, un informe con los 4 mejores cambios para mi equipo, combinando datos históricos de la ACB, el mercado actual, el calendario y una estimación de puntos esperados.

Meta: ganar la liga privada con amigos (clasificación por puntos, aunque el valor del equipo también importa como desempate y para el Brokerbasket).

Índice
Objetivo

Reglas del juego

Cómo funciona el modelo

Estado actual del equipo

Instalación

Uso diario

Estructura del repositorio

Scripts

Configuración (config.py)

Fuentes de datos

Hallazgos clave

Campos y glosario

Seguridad

Limitaciones conocidas

Mejoras pendientes

Incidencias resueltas

Anexo: endpoints de la API

1. Objetivo
Construir un repositorio propio que, antes de cada jornada, genere un informe personalizado con los mejores 4 cambios para mi equipo, teniendo en cuenta:

Mi cuenta: plantilla actual, dinero en caja, cupos y cambios disponibles.

El mercado en ese momento: precios, lesiones, estado físico.

El calendario: rival y condición de local o visitante en la jornada siguiente.

Una estimación de puntos esperados por jugador, combinando:

lo que hizo cada jugador la temporada pasada (2025-26),

lo que lleva en esta temporada,

la probabilidad de que su equipo gane (bonus del 20%).

La evolución esperada de los precios (regla del tope del 15% por jornada).

Objetivo final: un solo comando (python src/run.py) que haga todo y genere el informe.

2. Reglas del juego
Resumen de las reglas oficiales del Supermanager ACB que condicionan el diseño del optimizador:

Regla	Detalle
Presupuesto inicial	5.000.000 € por equipo
Plantilla	10 jugadores: 2 bases, 4 aleros (escoltas o aleros), 4 pívots (ala-pívots o pívots)
Cupos	Máximo 2 extracomunitarios y mínimo 4 jugadores formados localmente (bandera española, isNational = True)
Cambios	4 por jornada. Se pueden hacer entre el final de una jornada y el inicio del último partido de la siguiente
Bloqueo	Cada jugador se bloquea cuando empieza su partido. Los lesionados (cruz roja) se pueden cambiar hasta el cierre
Saldo	Nunca puede quedar negativo
Puntuación	Valoración ACB del jugador en el partido. +20% si gana su equipo, salvo que la valoración sea ≤ 0. Si no juega, 0 puntos
Fórmula de valoración	PTS + asistencias + rebotes + tapones a favor + robos + faltas recibidas + T1C + T2C + T3C − pérdidas − tapones en contra − faltas personales − T1I − T2I − T3I
Precio	Valoración media ACB (incluido el +20% por victoria) × 50.000 € por punto
Variación de precio	Nunca más de ±15% entre una jornada y la siguiente
Equipo incompleto	Si un equipo llega a la jornada con menos de 10 jugadores, su puntuación se reduce a la mitad
Clasificaciones	Jornada, general y Brokerbasket (valor de los 10 jugadores + dinero en caja)
Desempate por jornada	1º mayor valor económico del equipo, 2º mejor puntuación general
Máximo de equipos	15 por usuario
Ligas de club	Solo se aspira a premio con el club favorito fijado hasta el 24 de octubre de 2026
Consecuencia: el problema es una optimización con restricciones. Dados mi plantilla, mi caja y mis 4 cambios, hay que elegir qué jugadores vender y fichar para maximizar los puntos esperados, respetando posiciones, cupos y saldo.

3. Cómo funciona el modelo
3.1 Pipeline
text
06_snapshot.py       → foto del mercado (238 jugadores)
10_mi_equipo.py      → mi plantilla, caja, cupos, rivales
13_prediccion_global.py → puntos esperados para cada uno de los 238
14_optimizador.py    → los 4 cambios óptimos
informe.py           → informe en Markdown
Todo orquestado por run.py.

3.2 Predicción de puntos esperados
Para cada jugador del mercado:

text
1. media_ponderada = W × puntos_J1 + (1 − W) × media_2526_con_bonus
2. media_sin_bonus = media_ponderada / (1 + 0,2 × win%_equipo)
3. p_win_J2 = sigmoide((win%_equipo − win%_rival) × 4 + localía × 5)
4. puntos_esperados = media_sin_bonus × (1 + 0,2 × p_win_J2)
Donde:

W = 0,20 al inicio de temporada (peso de la jornada actual). Sube a medida que avanza el calendario.

media_2526_con_bonus es la media real de la temporada pasada, usando bonusVictory cuando el equipo ganó (porque pointsJourney del CSV de 2025-26 no incluye el +20%).

win%_equipo es el porcentaje de victorias del equipo la temporada pasada.

localía = +0,10 si juega en casa, −0,10 si juega fuera.

Sigmoide convierte la diferencia de fuerzas en una probabilidad entre 5% y 95%.

3.3 Predicción de precios
text
media_acum_proyectada = (puntos_J1 + puntos_esperados_J2) / 2
precio_objetivo = 50.000 × media_acum_proyectada
precio_proyectado_J3 = clamp(precio_objetivo, precio × 0,85, precio × 1,15)
reval_esperada = precio_proyectado_J3 / precio − 1
Con una sola jornada, el reval_esperada sale saturado al ±15% en la mayoría de los jugadores. Sirve para saber quién sube o baja, pero no para discriminar entre ellos. El optimizador usa puntos esperados, no reval.

3.4 Optimización de los 4 cambios
Modelo de programación lineal entera (con pulp):

Variables: vender[i] ∈ {0,1} para cada jugador de mi plantilla, fichar[j] ∈ {0,1} para cada candidato.

Objetivo: maximizar Σ pts_esp_fichar − Σ pts_esp_vender.

Restricciones:

Σ vender ≤ 4, Σ fichar ≤ 4

caja + Σ precio_vender − Σ precio_fichar ≥ 0

bases = 2, aleros = 4, pívots = 4

extracomunitarios ≤ 2

formados localmente ≥ 4

Si FORZAR_VENTA_LESIONADOS: vender[i] = 1 para todo lesionado.

Candidatos: los 30 mejores por posición según puntos esperados (configurable con TOP_POR_POSICION).

4. Estado actual del equipo
29-sep-2026, tras la J1:

Dato	Valor
Nombre	equipo pocho
Puntos totales	113,2
Clasificación general	64.054
Valor del equipo	5.117.000 €
Dinero en caja	0 €
Extracomunitarios	2 / 2
Formados localmente	5 / mínimo 4
Implicación: con 0 € en caja, cada fichaje tiene que financiarse con la venta de otro jugador. Las subidas de precio de los jugadores que ya tengo son el dinero extra disponible.

Plantilla J1 → J2:

Pos	Jugador	Equipo	Estado
1	F. Campazzo	Real Madrid	fit
1	A. Díaz	Unicaja	injured
3	A. Barcello	Monbus Obradoiro	fit
3	López-Arostegui	La Laguna Tenerife	fit
3	K. Taylor	Valencia Basket	fit
3	K. Robertson	MoraBanc Andorra	fit
5	W. Tavares	Real Madrid	fit
5	J. Pradilla	Real Madrid	fit
5	M. Geben	FIATC Girona	fit
5	R. Kurucs	Kosner Baskonia	fit
Cambios recomendados para J2 (generados por el pipeline):

text
VENDER:  Barcello, Díaz (lesionado), Robertson, Kurucs
FICHAR:  McGhee, Corbalán, Ubal, Balcerowski
Saldo:   +6.500 €
Puntos:  119,37 → 147,82  (+28,45)
5. Instalación
5.1 Requisitos
Python 3.11+

Git para Windows

VS Code (recomendado)

Cuenta en GitHub

5.2 Pasos
powershell
# 1. Clonar el repo
git clone https://github.com/SarelaFolgar/supermanager-acb.git
cd supermanager-acb

# 2. Entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Dependencias
pip install pandas requests python-dotenv pulp

# 4. Crear carpetas
mkdir data, src, informes
5.3 Configurar el token de la API
Crea un archivo .env en la raíz del repo (nunca se sube a GitHub, lo ignora .gitignore):

text
SM_TOKEN=Bearer eyJhbGciOi...
Cómo conseguir el token:

Abre https://supermanager.acb.com con DevTools (F12).

Pestaña Network → filtro Fetch/XHR.

Recarga la página o pulsa cualquier pestaña (Mercado, Equipo…).

Busca cualquier llamada a /api/basic/....

En Request Headers, copia el valor completo de Authorization.

Pégalo en .env después de SM_TOKEN=. Debe empezar por Bearer.

El token caduca. Si la API responde 401 o 403, repite el paso.

5.4 Configurar el equipo
Edita src/config.py:

python
MI_EQUIPO_ID = 246638       # Tu id de equipo
NOMBRE_EQUIPO = "equipo pocho"
CAJA = 0                    # Dinero disponible AHORA
Cómo conseguir MI_EQUIPO_ID:

En supermanager.acb.com, entra en tu equipo.

F12 → Network → Fetch/XHR.

Busca una llamada userteamplayer/journeys/XXXXXX.

Copia el número.

6. Uso diario
Un solo comando:

powershell
cd "C:\...\supermanager-acb"
.venv\Scripts\Activate.ps1
python src/run.py
Esto ejecuta el pipeline completo y genera:

data/raw/mercado_AAAA-MM-DD_HHMM.json — respuesta íntegra de la API.

data/mercado/mercado_AAAA-MM-DD_HHMM.csv — tabla plana del mercado.

data/mi_equipo/plantilla_actual.csv — mi plantilla actual.

data/mi_equipo/cambios.csv — cambios propuestos.

data/prediccion_global.csv — 238 jugadores con puntos esperados.

informes/informe_J2_AAAA-MM-DD_HHMM.md — el informe final.

Ver el informe: ábrelo en VS Code y pulsa Ctrl+Shift+V.

Guardar en GitHub:

powershell
git add .
git status     # comprueba que .env NO aparece
git commit -m "Informe J2"
git push
7. Estructura del repositorio
text
supermanager-acb/
├── .env                          # SM_TOKEN (NUNCA se sube)
├── .gitignore
├── README.md                     # este archivo
├── .venv/                        # entorno virtual (ignorado)
├── data/
│   ├── jugadores_2526.csv        # 1 fila por jugador, temporada 2025-26
│   ├── stats_jornada_2526.csv    # 1 fila por jugador y jornada, 2025-26
│   ├── features_2526.csv         # generado por 04_features.py
│   ├── equipos_logos.csv         # mapeo logo → nombre de equipo
│   ├── prediccion_global.csv     # generado por 13_prediccion_global.py
│   ├── mercado/
│   │   └── mercado_AAAA-MM-DD_HHMM.csv
│   ├── raw/
│   │   └── mercado_AAAA-MM-DD_HHMM.json
│   └── mi_equipo/
│       ├── plantilla_actual.csv
│       ├── jornada_1_puntos.csv
│       ├── historico_cruzado.csv
│       └── cambios.csv
├── informes/
│   └── informe_J2_AAAA-MM-DD_HHMM.md
└── src/
    ├── config.py                 # ← toda la configuración del proyecto
    ├── 01_explorar.py
    ├── 02_rentabilidad.py
    ├── 03_revalorizacion.py
    ├── 04_features.py
    ├── 05_mercado.py
    ├── 06_snapshot.py
    ├── 07_ver_stats.py
    ├── 08_jornada.py
    ├── 09_prediccion_precios.py
    ├── 10_mi_equipo.py
    ├── 11_mapeo_equipos.py
    ├── 12_historico.py
    ├── 13_prediccion_global.py
    ├── 14_optimizador.py
    ├── run.py                    # orquestador
    └── informe.py                # generador del informe
8. Scripts
Todos se ejecutan desde la raíz del repo con el entorno activado: python src/NOMBRE.py.

8.1 01_explorar.py — primer vistazo a los CSV
Comprueba dimensiones y columnas de los CSV de la temporada 2025-26. 293 jugadores × 34 jornadas = 9.962 filas; 3.303 sin puntos.

8.2 02_rentabilidad.py — puntos por millón
Media de puntos por partido jugado (minutos > 0), regularidad, precio final. La métrica es circular (el precio ya es la media × una constante). Sirve para entender el sistema, no para decidir.

8.3 03_revalorizacion.py — chollos al inicio
Compara la media con el precio inicial y calcula la revalorización. Solo el 7% de los jugadores baratos se doblaron. Es una mirada hacia atrás.

8.4 04_features.py — dataset para modelos
Cada fila es un jugador en una jornada, con la media y minutos de las 3 jornadas anteriores y el precio previo (usa shift(1) para no mirar al futuro). Salida: data/features_2526.csv.

8.5 05_mercado.py — test de la API
Comprueba que el token funciona y muestra la forma del JSON. No guarda nada.

8.6 06_snapshot.py — foto del mercado
Guarda el estado actual del mercado en data/raw/ (JSON) y data/mercado/ (CSV). Se ejecuta en cada run.py.

Pendiente: actualmente acumula un archivo por ejecución. Conviene añadir un bloque que borre las capturas anteriores y deje solo la más reciente.

8.7 07_ver_stats.py — debug de playerStats
Inspecciona la estructura de playerStats de la captura más reciente. Útil si algo falla.

8.8 08_jornada.py — tabla de la jornada
Aplana playerStats y muestra el próximo partido por equipo y el top 10 de la jornada anterior. Sustituido por 13_prediccion_global.py, pero se mantiene como referencia.

8.9 09_prediccion_precios.py — gap de precios
Calcula gap = K × media / precio − 1. Con una sola jornada, decenas de jugadores tienen gap enorme y todos subirán el 15%. Usar K = 50.000 (config).

8.10 10_mi_equipo.py — mi plantilla
Descarga mi plantilla actual desde la API (userteamplayer/journeys/<MI_EQUIPO_ID>), guarda los 10 jugadores y muestra cupos y rivales.

8.11 11_mapeo_equipos.py — logos → nombres
Genera data/equipos_logos.csv a partir del mercado. Necesario porque el rival viene como nombre de archivo del escudo.

8.12 12_historico.py — histórico de mi plantilla
Cruza mi plantilla con la temporada 2025-26 por nick + birthdate. Sustituido por 13_prediccion_global.py, que lo hace para los 238 jugadores.

8.13 13_prediccion_global.py — la pieza clave
Genera data/prediccion_global.csv con los 238 jugadores del mercado y sus puntos esperados para la jornada siguiente.

Columnas principales: idPlayer, shortName, nameTeam, position, price, puntos_j1, media_2526, media_ponderada, win_pct_equipo, win_pct_rival, p_win_J2, puntos_esperados_J2, reval_esperada, alerta_lesion.

8.14 14_optimizador.py — los 4 cambios
Modelo con pulp que maximiza puntos netos respetando todas las restricciones. Salida: data/mi_equipo/cambios.csv.

8.15 run.py — orquestador
Ejecuta todo en orden. Un solo comando.

8.16 informe.py — generador del informe
Convierte cambios.csv y prediccion_global.csv en un Markdown con:

Cambios recomendados (vender / fichar).

Resumen económico.

Impacto en puntos.

Plantilla resultante.

Verificación de reglas (✅/❌).

Notas del modelo.

Salida: informes/informe_JX_AAAA-MM-DD_HHMM.md.

9. Configuración (config.py)
Todo lo que se puede ajustar está en src/config.py. No toques los scripts para cambiar comportamiento; edita solo este archivo.

python
"""Configuración del proyecto. Edita SOLO este archivo."""

# ─── MI EQUIPO ──────────────────────────────────────────────
MI_EQUIPO_ID = 246638
NOMBRE_EQUIPO = "equipo pocho"

# ─── CAJA ───────────────────────────────────────────────────
CAJA = 0

# ─── REGLAS DE LA LIGA ──────────────────────────────────────
MAX_CAMBIOS = 4
POSICIONES = {1: 2, 3: 4, 5: 4}
MIN_LOCALES = 4
MAX_EXTRA = 2

# ─── OPTIMIZADOR ────────────────────────────────────────────
FORZAR_VENTA_LESIONADOS = True
TOP_POR_POSICION = 30

# ─── MODELO ─────────────────────────────────────────────────
PESO_JORNADA_ACTUAL = 0.20
K_PRECIO = 50000
TOPE_PRECIO = 0.15
Qué tocar según el caso:

Situación	Cambio
Cambio de equipo	MI_EQUIPO_ID y NOMBRE_EQUIPO
He fichado y me queda caja	CAJA
Quiero que el modelo pese más la temporada actual	Subir PESO_JORNADA_ACTUAL
El solver tarda demasiado	Bajar TOP_POR_POSICION
Ya no quiero forzar venta de lesionados	FORZAR_VENTA_LESIONADOS = False
10. Fuentes de datos
10.1 Repos públicos de Ivo Villanueva (R, licencia MIT en algunos)
Repo	Qué contiene	¿Útil?
SUPERMANAGER-BROKER-GENERAL	Bot en R que genera rankings de managers	Solo referencia del método de acceso a la API
DATOS-JUGADORES-SUPERMANAGER-2025_26	CSV de 2025-26: 293 jugadores × 34 jornadas	Base histórica principal
pbp_acb_historico	Boxscores desde 1983, play-by-play desde 2016-17, calendario	Contexto: minutos reales, fuerza de equipos
Sofianel5/supermanager	Herramienta para equipos de desarrollo	No relacionado
Descarga de los CSV de 2025-26:

powershell
curl.exe -o data/jugadores_2526.csv https://raw.githubusercontent.com/IvoVillanueva/DATOS-JUGADORES-SUPERMANAGER-2025_26/main/data/supermanager_juagadores_2026.csv
curl.exe -o data/stats_jornada_2526.csv https://raw.githubusercontent.com/IvoVillanueva/DATOS-JUGADORES-SUPERMANAGER-2025_26/main/data/supermanager_juagadores_stats_2026.csv
10.2 API del Supermanager
Mercado: https://supermanager.acb.com/api/basic/player

_filters (JSON), _page, _perPage, _sort.

Devuelve los 238 jugadores en una sola llamada.

Autenticación: Authorization: Bearer ....

Mi equipo: https://supermanager.acb.com/api/basic/userteamplayer/journeys/<MI_EQUIPO_ID>

Devuelve una lista: una entrada por jornada (jugada o por jugar).

Ficha de jugador: https://supermanager.acb.com/api/basic/playerstats/1/<idPlayer>

11. Hallazgos clave
11.1 Sobre los datos de la temporada pasada
293 jugadores × 34 jornadas = 9.962 filas. 3.303 filas sin puntos.

Cuando un jugador no juega, el CSV pone playerPrice = 0. "Partido jugado" = minutos > 0.

price es el precio final del jugador (un único valor); playerPrice es el precio en cada jornada.

Los puntos del Supermanager coinciden al 100% con la suma de las columnas de puntos por estadística: es la valoración ACB.

bonusVictory = 0 cuando el equipo pierde; cuando gana, es pointsJourney × 1,2 (total con bonus).

Importante: los pointsJourney del CSV 2025-26 no incluyen el bonus. En 2026-27 la API sí lo incluye. Hay que unificar antes de comparar.

11.2 Sobre los precios
El precio final se correlaciona 1,00 con la media de puntos. Comparar "media / precio final" es circular.

Cada jornada el precio se mueve como máximo ±15%. En 2025-26, el 15% de los movimientos tocaron el tope de subida y el 9% el de bajada.

Fórmula: precio = K × media_acumulada. Con la regla oficial, K = 50.000 €.

Señal gap = K × media / precio − 1:

gap > 0,3: el precio subió el 15% en el 100% de los casos.

gap < −0,3: bajó el 15%.

Entre −0,1 y 0,1: sin cambio apreciable.

Con una sola jornada jugada, decenas de jugadores tienen gap enorme y todos subirán el 15%. El gap no discrimina; hay que combinarlo con nivel real y rol.

11.3 Sobre la predicción
Solo el 7% de los baratos (≤ 270.000 €) doblaron su precio. Los "chollos" de los rankings son supervivientes.

Los minutos son lo más estable (correlación ~0,82 entre primeros y siguientes partidos).

La media de los primeros partidos frente al resto correlaciona ~0,70.

Correlación con los puntos de la jornada siguiente: precio previo 0,44, media últimas 3 jornadas 0,38, minutos últimas 3 jornadas 0,33.

Con un solo partido, la media actual es ruido: hay que combinarla con el histórico del jugador.

11.4 Sobre el histórico de la ACB
Los puntos del Supermanager son la valoración ACB (más el bonus por victoria). El histórico de boxscores permite recalcular cuántos puntos habría hecho cada jugador en cualquier temporada desde 1983 y estimar la fuerza de los equipos.

12. Campos y glosario
Campo	Significado
idPlayer	Identificador del jugador en el Supermanager (cambia cada temporada)
shortName, nick, fullName	Nombre corto, apodo y nombre completo
nameTeam, idTeam	Equipo
position	1 = base, 3 = alero, 5 = pívot
price	Precio actual
initialPrice	Precio al inicio de la temporada
playerPrice	Precio del jugador en una jornada concreta (2025-26)
competitionAverage	Media de puntos en la competición
pointsJourney	Puntos del jugador en la jornada
numberJourney	Número de jornada
valueTimePlayed	Minutos en la jornada, en segundos (0 = no jugó)
valuePoints, pointsPoints, etc.	Valor bruto y puntos aportados por cada estadística
bonusVictory	En 2025-26, total con bonus cuando gana el equipo (0 si pierde)
injuredDays, fisicStatus	Días de lesión y estado físico (fit, injured…)
isExtraCommunity	Extracomunitario (True/False)
isNational	Formado localmente (True/False)
license	Tipo de licencia (EXT, JFL, EUR, COT…)
isLocal	Si el equipo juega en casa en la jornada por venir
up15, down15	Referencias de cambio de precio
gap	K × media / precio − 1
Brokerbasket	Valor de los 10 jugadores + dinero en caja
13. Seguridad
El token de la API está en .env. Nunca se pega en el chat ni se sube a GitHub. Antes de hacer git commit, comprobar con git status que .env no aparece.

El token caduca. Si la API responde 401 o 403, copiarlo de nuevo desde DevTools y pegarlo en .env.

Al compartir capturas de DevTools, tapar la cabecera Authorization y las cookies.

Respetar los términos de uso del Supermanager: consultar solo mis propios datos, con pausas entre peticiones, sin automatizar de forma agresiva.

14. Limitaciones conocidas
La regla de precios (K, tope del 15%) se ha deducido de una temporada y de las reglas oficiales.

Que los puntos de esta temporada incluyen el bonus es una deducción a partir de valores múltiplos de 1,2.

Con pocas jornadas jugadas las medias actuales son ruidosas. Pesa más el histórico.

La win% de 2025-26 es un único número por equipo. No distingue rival: ganar al Madrid no es como ganar al Obradoiro.

Los recién llegados sin histórico se estiman con la media de su posición. Es una muleta.

El peso W = 0,20 es fijo. Debería subir con las jornadas jugadas.

El histórico multitemporada de pbp_acb_historico no está integrado.

Los datos de la API pueden cambiar de estructura o de reglas durante la temporada.

15. Mejoras pendientes
Por orden de impacto:

15.1 Fáciles (1-2 h)
Usar minutos en el modelo: ponderar la media por minutos jugados. Un 8 en 20 min pesa más que un 8 en 8 min.

W dinámico: W = partidos_jugados / (partidos_jugados + 4). En J2 vale 0,20; en J4, 0,50; en J8, 0,67. Se ajusta solo.

Limpieza de snapshots: borrar automáticamente las capturas anteriores del mercado (dejar solo la última).

Nombre del equipo y puntos esperados en el informe (ya implementado en la última revisión de informe.py).

Añadir NOMBRE_EQUIPO a config.py.

15.2 Medio (1 fin de semana)
Fuerza de equipo ataque/defensa en vez de win%. Con los boxscores de pbp_acb_historico de una temporada ya sale algo mucho mejor.

Integrar pbp_acb_historico para tener 3-5 temporadas por jugador. Requiere mapear IDs de la ACB con los del Supermanager (por nombre + equipo + edad).

Modelo Elo de equipos para P(ganar) seria.

15.3 Avanzadas
Modelo de minutos esperados (regresión sencilla con minutos últimos 3 partidos + rol).

Predicción de puntos por posición en vez de una media global.

Informe en HTML con CSS para exportar a PDF bonito.

Informes de otros equipos: python src/run.py --equipo <id> si el token tiene permiso (probablemente no).

16. Incidencias resueltas
Problema	Causa	Solución
git no se reconoce	Git no estaba instalado	Instalar Git para Windows y reabrir PowerShell
Author identity unknown al hacer commit	Git no sabía quién era yo	git config --global user.name y user.email
RPC failed; curl 55 Send failure en git push	Corte de conexión	Repetir git push
inf en la tabla de rentabilidad	Filas con precio 0	Partido jugado = minutos > 0, precio desde price
.gitignore y README.md marcados "U"	Normal en Windows	Ignorar
Ventana "Restricted Mode" en VS Code	Carpeta sin confianza	Confiar en la carpeta
MergeError: duplicate columns en 12_historico.py	idPlayer_2526 ya existía	Renombrar a idPlayer_2526_ref antes del merge
KeyError: 'injuredDays' en 14_optimizador.py	Merge duplicaba columnas → injuredDays_x/_y	Traer solo puntos_esperados_J2 de pred
KeyError al verificar nueva plantilla	cand[[bool,...]] interpretado como columnas	Usar .loc[idx_fichar]
idPlayer cambia cada temporada	La API renumera	Cruzar por nick + birthdate
17. Anexo: endpoints de la API
17.1 Mercado
text
GET https://supermanager.acb.com/api/basic/player
Authorization: Bearer <token>

Parámetros:
  _filters = [
    {"field":"competition.idCompetition","value":1,"operator":"=","condition":"AND"},
    {"field":"edition.isActive","value":true,"operator":"=","condition":"AND"}
  ]
  _page = 1
  _perPage = 30
  _sort = [{"field":"price","type":"DESC"}]
Devuelve los 238 jugadores en una sola llamada, con playerStats anidado.

17.2 Mi equipo
text
GET https://supermanager.acb.com/api/basic/userteamplayer/journeys/<MI_EQUIPO_ID>
Authorization: Bearer <token>
Devuelve una lista con una entrada por jornada. Cada entrada tiene:

totalStats: puntos, rebotes, triples, asistencias, totalPoints.

idJourney, number, name.

playerList: los 10 jugadores con precio, posición, estado físico, cupos y próximo rival.

standings: clasificación global, liga oficial y liga privada.

17.3 Ficha de jugador
text
GET https://supermanager.acb.com/api/basic/playerstats/1/<idPlayer>
Authorization: Bearer <token>
Licencia y créditos
Datos históricos: repos de Ivo Villanueva (licencia MIT en algunos).

Este repositorio es privado y solo para uso personal. No redistribuir los datos de la API.

Última actualización: 30-sep-2026, tras generar el primer informe completo de la J2.