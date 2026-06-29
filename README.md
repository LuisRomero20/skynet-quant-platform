# 🚀 Skynet Quant Platform V4 — FIFA World Cup 2026 Predictor

> Plataforma analítica de pronósticos deportivos con Motor Híbrido de Machine Learning y Modelo Estadístico de Poisson para el **FIFA World Cup 2026™**.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://skynet-quant-platform-ad5w7seuajetmp7mcnsip4.streamlit.app/)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-%3E%3D1.37-FF4B4B?logo=streamlit)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)](https://www.sqlite.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-%3E%3D1.4-F7931E?logo=scikit-learn)](https://scikit-learn.org/)

**🔗 Live Demo:** https://skynet-quant-platform-ad5w7seuajetmp7mcnsip4.streamlit.app/

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características Principales](#-características-principales)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Stack Tecnológico](#-stack-tecnológico)
- [Fuentes de Datos](#-fuentes-de-datos)
- [Motor Predictivo Híbrido](#-motor-predictivo-híbrido)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación Local](#-instalación-local)
- [Uso de la Aplicación](#-uso-de-la-aplicación)
- [Módulos del Sistema](#-módulos-del-sistema)
- [Base de Datos](#-base-de-datos)
- [Backtesting y Auditoría](#-backtesting-y-auditoría)
- [Scripts Auxiliares](#-scripts-auxiliares)
- [Despliegue en Streamlit Cloud](#-despliegue-en-streamlit-cloud)
- [Variables de Entorno](#-variables-de-entorno)

---

## 🧠 Descripción General

**Skynet Quant Platform V4** es una aplicación web de análisis cuantitativo deportivo construida con Streamlit. Combina dos motores predictivos independientes — un modelo de **Machine Learning (Random Forest)** y un **Motor Estadístico de Poisson** — para generar probabilidades de victoria, marcadores probables y líneas de mercados secundarios (corners y tarjetas) para los partidos del Mundial 2026.

La plataforma es completamente autónoma:
- **Al arrancar**, genera predicciones para todo el fixture del Mundial 2026 y las persiste en SQLite.
- **En cada carga**, sincroniza automáticamente los resultados reales desde un repositorio histórico en GitHub, resolviendo predicciones cerradas y actualizando el backtesting en tiempo real.
- **No requiere intervención manual** para registrar partidos ni actualizar resultados.

---

## ✨ Características Principales

| Feature | Descripción |
|---|---|
| 🤖 **IA Predictiva (Random Forest)** | Modelo entrenado con +25 años de resultados internacionales (2000–2026), ELO, penales y estadísticas recientes |
| 📊 **Modelo Poisson** | Distribución estadística basada en xG, goles recientes y métricas de los últimos 3 partidos |
| 💰 **Mercados Cuantitativos** | Líneas automáticas de Corners (Más/Menos) y Tarjetas basadas en promedios de FootyStats |
| ⚽ **Historial H2H** | Head-to-Head histórico entre selecciones directo desde el repositorio de GitHub `martj42/international_results` |
| 🏆 **Mundial Hasta Ahora** | Tabla de resultados del Mundial 2026 en curso, actualizada automáticamente |
| ✅ **Auditoría de Estimados** | Registro completo de todas las predicciones generadas, con resultado real cuando el partido ya se jugó |
| 📈 **Backtesting Histórico** | Métricas de precisión del modelo calculadas únicamente sobre predicciones con resultado verificado |
| 🔄 **Sync Automático** | Resultados reales se sincronizan en cada carga de la página sin intervención del usuario |
| 💾 **Persistencia SQLite** | Todas las predicciones y resultados se guardan en `data/skynet.db` con deduplicación automática |

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    SKYNET QUANT PLATFORM V4                     │
│                         (Streamlit UI)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
   ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Motor ML     │ │ Motor Poisson│ │  Mercados Quant  │
   │ (Random       │ │ (scipy.stats │ │  Corners/Cards   │
   │  Forest)      │ │  + xG)       │ │  (FootyStats)    │
   └───────┬───────┘ └──────┬───────┘ └────────┬─────────┘
           └───────────────┼───────────────────┘
                           ▼
              ┌────────────────────────┐
              │   SQLite: skynet.db    │
              │  ┌──────────────────┐  │
              │  │    partidos      │  │
              │  │   predicciones   │  │
              │  │    resultados    │  │
              │  └──────────────────┘  │
              └────────────┬───────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
  ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐
  │ GitHub CSV     │ │ FootyStats   │ │  ELO Rankings    │
  │ martj42/       │ │ form.csv     │ │  rankings_elo    │
  │ international_ │ │ (local)      │ │  .csv (local)    │
  │ results        │ └──────────────┘ └──────────────────┘
  └────────────────┘
```

**Flujo de datos en cada sesión:**

```
App Start
    │
    ├─► [1 vez por sesión] _generar_predicciones_fixture()
    │       └─► Genera predicciones Poisson para todos los partidos del fixture
    │           └─► buscar_o_crear_partido() + buscar_o_crear_prediccion() → SQLite
    │
    └─► [Cada carga] Sync de resultados
            └─► obtener_partidos_sin_resultado() → lista de pendientes
                └─► _persistir_resultado_si_disponible() → GitHub CSV → SQLite
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|---|---|
| **UI / Frontend** | [Streamlit](https://streamlit.io) ≥ 1.37 |
| **ML** | scikit-learn (RandomForestClassifier) + joblib |
| **Estadístico** | SciPy (Distribución de Poisson) |
| **Visualización** | Altair ≥ 6.0 |
| **Data** | Pandas ≥ 2.2, NumPy ≥ 1.26 |
| **Persistencia** | SQLite 3 (stdlib) |
| **Deploy** | Streamlit Community Cloud |
| **Datos históricos** | GitHub (`martj42/international_results`) via HTTP |

---

## 📡 Fuentes de Datos

### 1. `martj42/international_results` (GitHub — Live)
El dataset histórico más completo de resultados internacionales (1872 – presente), consumido directamente desde GitHub sin necesidad de descarga manual.

- `results.csv` — Resultados de partidos (fecha, local, visitante, goles, torneo, neutral)
- `goalscorers.csv` — Goleadores por partido (usado para features de penales en el modelo ML)

> 📌 Cached con `@st.cache_data(ttl=3600)` — se refresca cada hora en producción.

### 2. `data/footystats_form.csv` (Local)
Estadísticas detalladas de cada selección del Mundial 2026 extraídas de FootyStats:
- Corners promedio (local/visitante)
- Tarjetas amarillas y rojas promedio
- xG ofensivo y defensivo
- Partidos jugados, goles a favor/contra

### 3. `data/rankings_elo.csv` (Local)
Ranking ELO de selecciones nacionales:
- `Seleccion` — Nombre normalizado del país
- `Puntaje_Elo` — Rating ELO actual

> El ELO es el feature más predictivo del modelo Random Forest (`diferencia_elo`).

---

## 🔮 Motor Predictivo Híbrido

### Motor 1: Random Forest (Skynet ML)

Entrenado sobre **+25.000 partidos internacionales** desde el año 2000 con los siguientes features:

| Feature | Descripción |
|---|---|
| `elo_local` / `elo_visitante` | Rating ELO de cada selección |
| `diferencia_elo` | Diferencia absoluta de ELO |
| `es_oficial` | 1 si no es amistoso |
| `neutral_flag` | 1 si es cancha neutral |
| `tournament_importance` | Importancia del torneo (1-3) |
| `home_avg_goals_scored` | Promedio de goles anotados (últimos 3 partidos) |
| `home_avg_goals_conceded` | Promedio de goles recibidos |
| `home_avg_goal_diff` | Diferencia de goles promedio |
| `home_recent_win_rate` | % de victorias recientes |
| `home_penalty_avg` | Penales marcados en los últimos 3 partidos |
| *(idem para visitante)* | |

**Configuración del modelo:**
```python
RandomForestClassifier(
    n_estimators=250,
    max_depth=14,
    class_weight='balanced_subsample',
    random_state=42
)
```

**Output:** Probabilidades para 3 clases: `Victoria Local (1)`, `Empate (0)`, `Victoria Visitante (-1)`

**Blend con Poisson:** El resultado ML se mezcla con Poisson (80% Poisson + 20% ML) para mayor estabilidad.

> 🚀 **Auto-entrenamiento:** Si el modelo no existe en el servidor (primer deploy en cloud), se entrena automáticamente al arrancar la app con `@st.cache_resource`.

### Motor 2: Modelo de Poisson

Calcula la distribución de probabilidad de goles esperados (xG) para cada selección y genera:

1. **Probabilidades 1X2** — Victoria Local / Empate / Victoria Visitante
2. **Marcador más probable** — Par (goles_local, goles_visitante) con mayor probabilidad conjunta
3. **Probabilidad del marcador exacto**

**Pipeline de cálculo de xG:**
```
xG_local = promedio(xG_FootyStats, goles_recientes_3_partidos, ajuste_ELO)
xG_visitante = ídem
```

**Marcadores calculados:** Distribución conjunta de Poisson para todos los pares de goles de 0×0 a 5×5.

---

## 📁 Estructura del Proyecto

```
fifa-world-cup-predictor/
│
├── app.py                          # Aplicación principal Streamlit
│
├── ai/
│   └── entrenador.py               # Entrenamiento del modelo Random Forest
│
├── core/
│   ├── api_manager.py              # Gestión de llamadas a APIs externas
│   ├── auditoria.py                # Sistema de auditoría (legacy CSV)
│   ├── backtesting.py              # Cálculo de métricas de backtesting desde SQLite
│   ├── calculadora_elo.py          # Actualización dinámica de ratings ELO
│   ├── config.py                   # Configuración global y variables de entorno
│   ├── database.py                 # Capa de persistencia SQLite (CRUD + deduplicación)
│   └── diccionario.py              # Normalización de nombres de países
│
├── data/
│   ├── skynet.db                   # Base de datos SQLite (generada en runtime, no en git)
│   ├── footystats_form.csv         # Estadísticas de forma (FootyStats)
│   ├── rankings_elo.csv            # Rankings ELO de selecciones
│   └── international-world-cup-*   # CSVs del Mundial 2026 (FootyStats)
│
├── models/
│   ├── modelo_poisson.py           # Implementación del motor Poisson
│   └── predictor_maestro.py        # Orquestador de predicciones combinadas
│
├── scripts/
│   ├── actualizar_rankings_fifa.py # Actualiza rankings FIFA/ELO
│   ├── auditor_resultados.py       # Auditoría de resultados pasados
│   ├── ingesta_masiva.py           # Ingesta masiva de partidos históricos
│   ├── notificador_telegram.py     # Envío de predicciones por Telegram
│   ├── pipeline_api_db.py          # Pipeline: API → Base de datos
│   ├── pipeline_etl.py             # Pipeline ETL completo
│   ├── procesar_footystats_csv.py  # Procesamiento de datos FootyStats
│   ├── scraper_historial_libre.py  # Scraper de historial libre
│   ├── termometro_social.py        # Análisis de sentimiento en redes
│   ├── test_api_forma.py           # Tests de API de forma
│   └── test_git_h2h.py             # Historial H2H desde GitHub
│
├── tests/
│   ├── test_backtesting.py         # Tests del motor de backtesting
│   └── test_database_results.py    # Tests de la capa de base de datos
│
├── .streamlit/
│   └── config.toml                 # Configuración de Streamlit (tema dark, headless)
│
├── requirements.txt                # Dependencias Python
└── .gitignore                      # Excluye venv/, *.db, *.pkl, .env
```

---

## 🚀 Instalación Local

### Prerrequisitos
- Python 3.10 o superior
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/LuisRomero20/skynet-quant-platform.git
cd skynet-quant-platform
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. (Opcional) Entrenar el modelo ML localmente

Si es la primera vez, el modelo se entrenará automáticamente al arrancar la app. Si quieres entrenarlo manualmente antes:

```bash
python ai/entrenador.py
```

Esto descarga el dataset histórico de GitHub (~50MB), entrena el Random Forest y guarda el modelo en `ai/cerebro_mundial.pkl`.

### 4. Ejecutar la aplicación

```bash
streamlit run app.py
```

La app estará disponible en `http://localhost:8501`.

---

## 🖥️ Uso de la Aplicación

### Panel de Control Quant

Al abrir la aplicación, verás el **Panel de Control Quant** en la parte superior. Selecciona cualquier partido del fixture del Mundial 2026 desde el desplegable para activar todos los motores predictivos.

### Pestañas disponibles

#### 🤖 IA Predictiva
Probabilidades generadas por el modelo Random Forest (entrenado con datos históricos desde 2000). Muestra:
- Probabilidad de victoria para cada equipo y empate
- Barras de progreso de fuerza relativa
- Accuracy del modelo en el conjunto de validación

#### 📊 Modelo Poisson
Motor estadístico clásico. Muestra:
- Probabilidades 1X2 basadas en xG calculado
- Marcador más probable con su probabilidad exacta
- Gráfico de distribución de goles por equipo (Altair)
- Recomendación final del modelo

#### 💰 Mercados Cuantitativos
Líneas de apuesta derivadas de datos de FootyStats:
- **Corners:** Total esperado de tiros de esquina y línea Over/Under
- **Tarjetas:** Total esperado de tarjetas mostradas y línea Over/Under
- Tabla de métricas comparativas por equipo

#### ⚽ Historial H2H
Head-to-head histórico entre las dos selecciones seleccionadas, extraído en tiempo real del repositorio `martj42/international_results` en GitHub. Muestra los últimos enfrentamientos con fecha, torneo y resultado.

#### 🏆 Mundial Hasta Ahora
Todos los resultados del Mundial 2026 que ya se han jugado, con fecha, equipos y marcador final.

#### ✅ Auditoría de Estimados
Tabla completa de todas las predicciones generadas para el fixture. Cada fila muestra:
- Partido y fecha
- Predicción del modelo (Local/Empate/Visitante)
- Probabilidad y confianza
- Resultado real (cuando el partido ya se jugó)
- Estado: `pendiente` / `acierto` / `fallo`

---

## 🗄️ Módulos del Sistema

### `core/database.py`
Capa de acceso a datos sobre SQLite. Incluye deduplicación automática para evitar registros duplicados al recargar la app.

**Funciones principales:**

| Función | Descripción |
|---|---|
| `crear_esquema()` | Crea las tablas si no existen |
| `buscar_o_crear_partido(fecha, local, visitante, torneo, estado)` | Deduplicación por fecha+local+visitante |
| `buscar_o_crear_prediccion(partido_id, modelo, prediccion, probabilidad, confianza)` | Deduplicación por partido_id+modelo |
| `tiene_resultado(partido_id)` | Check booleano de si hay resultado registrado |
| `obtener_partidos_sin_resultado()` | Lista de partidos pendientes de resultado |
| `obtener_predicciones_auditoria()` | Query deduplicada para la tabla de auditoría |
| `obtener_estadisticas_predicciones()` | Total / resueltas / pendientes / aciertos / % |

### `core/backtesting.py`
Calcula métricas de rendimiento del modelo sobre predicciones ya cerradas.

```sql
SELECT COUNT(*), SUM(CASE WHEN p.prediccion = r.resultado THEN 1 ELSE 0 END)
FROM predicciones p
JOIN resultados r ON p.partido_id = r.partido_id
```

### `core/diccionario.py`
Normaliza nombres de países en múltiples idiomas/variantes al nombre canónico en español. Por ejemplo:
- `"Netherlands"` → `"Países Bajos"`
- `"USA"` / `"United States"` → `"Estados Unidos"`
- `"Ivory Coast"` / `"Côte d'Ivoire"` → `"Costa de Marfil"`

### `ai/entrenador.py`
Pipeline completo de entrenamiento:
1. Descarga `results.csv` y `goalscorers.csv` de GitHub
2. Feature engineering (ELO, estadísticas recientes, importancia del torneo, penales)
3. Entrena `RandomForestClassifier(n_estimators=250, max_depth=14)`
4. Evalúa accuracy en el 20% de test
5. Exporta el modelo a `ai/cerebro_mundial.pkl`

---

## 🗃️ Base de Datos

SQLite en `data/skynet.db` (excluido de git, generado en runtime).

### Esquema

```sql
CREATE TABLE partidos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha       TEXT NOT NULL,
    local       TEXT NOT NULL,
    visitante   TEXT NOT NULL,
    torneo      TEXT,
    estado      TEXT DEFAULT 'programado',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE predicciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    partido_id   INTEGER NOT NULL REFERENCES partidos(id),
    modelo       TEXT NOT NULL,
    prediccion   TEXT NOT NULL,
    probabilidad REAL,
    confianza    TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE resultados (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    partido_id  INTEGER NOT NULL REFERENCES partidos(id),
    resultado   TEXT NOT NULL,
    goles_local INTEGER,
    goles_visit INTEGER,
    fuente      TEXT DEFAULT 'github_csv',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📊 Backtesting y Auditoría

El sistema de auditoría es completamente autónomo:

1. **Generación automática de predicciones:** Al arrancar la sesión (`st.session_state`), el sistema genera predicciones Poisson para todos los partidos del fixture del Mundial 2026 y los persiste en SQLite.

2. **Sync de resultados en cada carga:** En cada recarga de la página, el sistema consulta los partidos sin resultado, busca si ya se jugaron en el histórico de GitHub y actualiza la base de datos.

3. **Deduplicación:** `buscar_o_crear_partido()` y `buscar_o_crear_prediccion()` garantizan que no se crean duplicados aunque el usuario recargue la app múltiples veces.

4. **Backtesting calculado en tiempo real:**

```
% Acierto = (predicciones correctas / partidos resueltos) × 100
```

Solo se cuentan partidos con resultado real verificado en la DB.

---

## 📜 Scripts Auxiliares

| Script | Uso |
|---|---|
| `scripts/actualizar_rankings_fifa.py` | Actualiza `data/rankings_elo.csv` con los últimos rankings |
| `scripts/auditor_resultados.py` | Revisa predicciones pasadas y actualiza estados |
| `scripts/ingesta_masiva.py` | Ingesta histórica masiva de partidos a la DB |
| `scripts/notificador_telegram.py` | Envía predicciones del día por Telegram |
| `scripts/pipeline_etl.py` | Pipeline ETL completo: extracción → transformación → carga |
| `scripts/pipeline_api_db.py` | Sincroniza datos desde API externa hacia la DB |
| `scripts/procesar_footystats_csv.py` | Procesa y normaliza los CSVs de FootyStats |
| `scripts/termometro_social.py` | Análisis de sentimiento social (Twitter/X) |
| `scripts/test_git_h2h.py` | Extrae historial H2H desde el repositorio de GitHub |

---

## ☁️ Despliegue en Streamlit Cloud

La aplicación está desplegada en [Streamlit Community Cloud](https://streamlit.io/cloud).

**Comportamiento en cloud:**
- La base de datos SQLite (`data/skynet.db`) es **efímera** — se recrea en cada restart del servidor.
- El modelo ML (`ai/cerebro_mundial.pkl`) **se entrena automáticamente** al primer arranque si no existe, usando `@st.cache_resource`. El entrenamiento tarda aproximadamente 60 segundos y se mantiene en memoria mientras el servidor esté activo.
- Los datos de GitHub se cachean con `@st.cache_data(ttl=3600)`.

**Archivo `.streamlit/config.toml`:**
```toml
[server]
headless = true
port = 8501

[theme]
base = "dark"
```

---

## 🔐 Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (no se sube a git):

```env
# Ruta personalizada para la base de datos (opcional)
SKYNET_DB_PATH=data/skynet.db

# Token de Telegram para notificaciones (opcional)
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

Si no existe el archivo `.env`, la app funciona con valores por defecto (la importación de `dotenv` está protegida con `try/except`).

---

## 🧪 Tests

```bash
# Ejecutar todos los tests
python -m unittest discover tests

# Tests individuales
python -m unittest tests.test_backtesting
python -m unittest tests.test_database_results
```

Los tests cubren:
- Creación de esquema y operaciones CRUD en SQLite
- Cálculo correcto de métricas de backtesting
- Estadísticas de predicciones (total, resueltas, pendientes, aciertos)

---

## 📄 Licencia

Este proyecto es de uso personal/educativo. Los datos históricos de resultados internacionales son propiedad de sus respectivas fuentes ([martj42/international_results](https://github.com/martj42/international_results), FootyStats).

---

*Desarrollado con ⚽ y 🤖 para el FIFA World Cup 2026™*
