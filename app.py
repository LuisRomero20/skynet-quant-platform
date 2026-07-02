import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import joblib
from datetime import datetime
from scipy.stats import poisson
import altair as alt

# ==========================================
# BLINDAJE DE RUTAS
# ==========================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.diccionario import normalizar_pais
from scripts.test_git_h2h import testear_h2h_git
from core.auditoria import actualizar_resultado_prediccion
from core.database import (
    guardar_partido,
    guardar_prediccion,
    guardar_resultado,
    actualizar_estado_partido,
    obtener_estadisticas_basicas,
    obtener_estadisticas_predicciones,
    buscar_o_crear_partido,
    buscar_o_crear_prediccion,
    tiene_resultado,
    obtener_predicciones_auditoria,
    obtener_partidos_sin_resultado,
)
from core.backtesting import ejecutar_backtesting

st.set_page_config(page_title="Skynet Quant Platform V4", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2.5rem !important; }
    .stMetric { background-color: #0f172a; border: 1px solid #1e293b; padding: 15px; border-radius: 10px; }
    .sportsbook-box { background-color: #1e293b; padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #3b82f6;}
    .badge-mdm { background-color: #f59e0b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .ml-box { background-color: #064e3b; padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #10b981;}
    </style>
""", unsafe_allow_html=True)

st.title("🚀 SKYNET ANALYTICAL SPORTSBOOK")
st.markdown("🤖 Modelo híbrido de Machine Learning y Poisson para pronósticos inteligentes de partidos internacionales.")
st.divider()

backtesting = ejecutar_backtesting(limit=20)
st.markdown("### 📈 Backtesting histórico")
st.caption("Rendimiento del modelo sobre predicciones ya cerradas. Solo se incluyen partidos con resultado real verificado en la base de datos.")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Partidos cerrados", backtesting["total"])
col_b.metric("Aciertos", backtesting["aciertos"])
col_c.metric("% Acierto", f"{backtesting['porcentaje']}%")
st.divider()

# ==========================================
# 1. CARGA DE DATOS Y MODELOS
# ==========================================
@st.cache_data
def cargar_footystats():
    ruta = os.path.join(ROOT_DIR, 'data', 'footystats_form.csv')
    if os.path.exists(ruta): return pd.read_csv(ruta)
    return None

@st.cache_data
def cargar_datos_elo():
    ruta = os.path.join(ROOT_DIR, 'data', 'rankings_elo.csv')
    if os.path.exists(ruta):
        df = pd.read_csv(ruta)
        df.columns = df.columns.str.strip()
        if 'Team' in df.columns and 'Elo' in df.columns:
            df = df.rename(columns={'Team': 'Seleccion', 'Elo': 'Puntaje_Elo'})
        if 'Seleccion' in df.columns and 'Puntaje_Elo' in df.columns:
            return dict(zip(df['Seleccion'], df['Puntaje_Elo']))
        return {}
    return {}

@st.cache_data
def cargar_fixture_local():
    """Carga el fixture completo del Mundial 2026 desde el CSV local de FootyStats.
    Retorna un DataFrame con columnas: date, home_team, away_team, home_score, away_score, status.
    Los nombres de equipo ya están normalizados con normalizar_pais.
    """
    ruta = os.path.join(ROOT_DIR, 'data', 'international-world-cup-matches-2026-to-2026-stats.csv')
    if not os.path.exists(ruta):
        return pd.DataFrame()
    try:
        df = pd.read_csv(ruta)
        # Parsear fecha desde "Jul 02 2026 - 7:00pm"
        df['date'] = pd.to_datetime(
            df['date_GMT'].str.extract(r'^(\w+ \d+ \d+)')[0],
            format='%b %d %Y', errors='coerce'
        )
        df['home_team'] = df['home_team_name'].apply(normalizar_pais)
        df['away_team']  = df['away_team_name'].apply(normalizar_pais)
        df['home_score'] = pd.to_numeric(df['home_team_goal_count'], errors='coerce')
        df['away_score'] = pd.to_numeric(df['away_team_goal_count'], errors='coerce')
        return df[['date', 'home_team', 'away_team', 'home_score', 'away_score', 'status']].copy()
    except Exception:
        return pd.DataFrame()

@st.cache_data
def normalizar_country_footystats(country_name):
    if country_name is None:
        return ''
    nombre = str(country_name).strip()
    for sufijo in ["Men's National Team", "Women's National Team", 'National Team', 'National team', 'Team']:
        if nombre.endswith(sufijo):
            nombre = nombre[: -len(sufijo)].strip()
            break
    return normalizar_pais(nombre)


def _tournament_importance(tournament):
    if pd.isna(tournament):
        return 0
    torneo = str(tournament).lower()
    if any(key in torneo for key in ['world cup', 'euro', 'copa', 'nations league', 'confederations cup', 'champions league']):
        return 3
    if any(key in torneo for key in ['qualifier', 'qualification', 'play-off', 'gold cup', 'afcon', 'concacaf']):
        return 2
    if 'friendly' in torneo or 'exhibition' in torneo:
        return 1
    return 1


def _match_context(df_results, local, visitante):
    if df_results is None or df_results.empty:
        return 'Friendly', 0

    mask = ((df_results['home_team'] == local) & (df_results['away_team'] == visitante)) | \
           ((df_results['home_team'] == visitante) & (df_results['away_team'] == local))
    df_match = df_results[mask]
    if df_match.empty:
        return 'Friendly', 0

    row = df_match.sort_values('date', ascending=False).iloc[0]
    neutral = row.get('neutral', False)
    neutral_flag = 1 if str(neutral).upper() == 'TRUE' or neutral is True else 0
    return row.get('tournament', 'Friendly'), neutral_flag


def _team_recent_stats(df_matches, team, current_date, n=3):
    if df_matches is None or df_matches.empty:
        return 0.0, 0.0, 0.0
    team_matches = df_matches[((df_matches['home_team'] == team) | (df_matches['away_team'] == team)) &
                               (df_matches['date'] < current_date)].sort_values('date', ascending=False).head(n)
    if team_matches.empty:
        return 0.0, 0.0, 0.0

    goals_scored, goals_conceded, wins = [], [], 0
    for _, row in team_matches.iterrows():
        if row['home_team'] == team:
            goals_scored.append(row['home_score'])
            goals_conceded.append(row['away_score'])
            if row['home_score'] > row['away_score']:
                wins += 1
        else:
            goals_scored.append(row['away_score'])
            goals_conceded.append(row['home_score'])
            if row['away_score'] > row['home_score']:
                wins += 1

    return float(np.mean(goals_scored)), float(np.mean(goals_conceded)), float(wins / len(team_matches))


def _team_penalty_avg(df_goals, team, current_date, n=3):
    if df_goals is None or df_goals.empty:
        return 0.0
    team_goals = df_goals[(df_goals['team'] == team) & (df_goals['date'] < current_date)]
    if team_goals.empty:
        return 0.0
    recent_penalties = team_goals.groupby('date')['penalty'].sum().sort_index(ascending=False).head(n)
    return float(recent_penalties.mean()) if not recent_penalties.empty else 0.0


def _resultado_real_historico(row, local, visitante):
    if row is None or pd.isna(row.get('home_score')) or pd.isna(row.get('away_score')):
        return None

    try:
        home_score = int(row['home_score'])
        away_score = int(row['away_score'])
    except (TypeError, ValueError):
        return None

    if home_score == away_score:
        return 'Empate'

    ganador = row['home_team'] if home_score > away_score else row['away_team']
    if ganador == local:
        return f'Victoria {local}'
    if ganador == visitante:
        return f'Victoria {visitante}'
    return 'Empate'


def _get_metric(df_team, col):
    if df_team is not None and not df_team.empty and col in df_team.columns:
        return df_team[col].values[0]
    return np.nan


def _get_avg_metric(df_team, col):
    valor = _get_metric(df_team, col)
    partidos = _get_metric(df_team, 'P')
    if pd.isna(valor) or pd.isna(partidos) or partidos == 0:
        return np.nan
    return float(valor) / float(partidos)


def _predecir_poisson(local, visitante, df_results, df_stats, dict_elo):
    """Calcula predicción Poisson pura para un partido. Devuelve (prediccion, prob, confianza)."""
    stats_l = df_stats[df_stats['Country'].apply(normalizar_country_footystats) == local] if df_stats is not None else None
    stats_v = df_stats[df_stats['Country'].apply(normalizar_country_footystats) == visitante] if df_stats is not None else None

    xg_l_fs = _get_avg_metric(stats_l, 'xG')
    xg_v_fs = _get_avg_metric(stats_v, 'xG')

    elo_base_l = float(dict_elo.get(local, 1600))
    elo_base_v = float(dict_elo.get(visitante, 1500))
    diferencia_elo = elo_base_l - elo_base_v

    hoy = pd.Timestamp(datetime.now().date())
    home_goals, home_conceded, home_win_rate = _team_recent_stats(df_results, local, hoy, n=3)
    away_goals, away_conceded, away_win_rate = _team_recent_stats(df_results, visitante, hoy, n=3)
    home_goal_diff = home_goals - home_conceded
    away_goal_diff = away_goals - away_conceded

    if not np.isnan(xg_l_fs) and not np.isnan(xg_v_fs):
        xg_l_final = max(0.1, 0.5 * xg_l_fs + 0.2 * home_goals + 0.15 * home_win_rate + 0.1 * home_goal_diff + 0.05 * max(diferencia_elo / 100, 0))
        xg_v_final = max(0.1, 0.5 * xg_v_fs + 0.2 * away_goals + 0.15 * away_win_rate + 0.1 * away_goal_diff + 0.05 * max(-diferencia_elo / 100, 0))
    else:
        ventaja = (diferencia_elo / 100) * 0.25
        xg_l_final = max(0.1, 1.3 + ventaja)
        xg_v_final = max(0.1, 1.3 - ventaja)

    prob_l = [poisson.pmf(i, xg_l_final) for i in range(6)]
    prob_v = [poisson.pmf(i, xg_v_final) for i in range(6)]
    matriz = np.outer(prob_l, prob_v)
    p_local = float(np.sum(np.tril(matriz, -1)))
    p_empate = float(np.sum(np.diag(matriz)))
    p_visitante = float(np.sum(np.triu(matriz, 1)))

    if p_local >= p_empate and p_local >= p_visitante:
        pred, prob = f'Victoria {local}', p_local
    elif p_visitante > p_empate:
        pred, prob = f'Victoria {visitante}', p_visitante
    else:
        pred, prob = 'Empate', p_empate

    confianza = 'Alta' if prob >= 0.4 else 'Media' if prob >= 0.25 else 'Baja'
    return pred, prob, confianza


def _persistir_resultado_desde_local(partido_id, local, visitante, df_local):
    """Guarda el resultado desde el CSV local de FootyStats si el partido está completo."""
    if df_local is None or df_local.empty or tiene_resultado(partido_id):
        return
    mask = (
        ((df_local['home_team'] == local) & (df_local['away_team'] == visitante)) |
        ((df_local['home_team'] == visitante) & (df_local['away_team'] == local))
    ) & (df_local['status'] == 'complete')
    completados = df_local[mask & df_local['home_score'].notna() & df_local['away_score'].notna()]
    if completados.empty:
        return
    row = completados.sort_values('date', ascending=False).iloc[0]
    resultado = _resultado_real_historico(
        {'home_team': row['home_team'], 'away_team': row['away_team'],
         'home_score': row['home_score'], 'away_score': row['away_score']},
        local, visitante
    )
    if resultado:
        guardar_resultado(partido_id, resultado, 1.0)
        actualizar_estado_partido(partido_id, 'jugado')


def _persistir_resultado_si_disponible(partido_id, local, visitante, df_results):
    """Si el partido ya se jugó (2026) y no tiene resultado guardado, lo guarda."""
    if df_results is None or df_results.empty or tiene_resultado(partido_id):
        return
    hoy = pd.Timestamp(datetime.now().date())
    mask = (
        ((df_results['home_team'] == local) & (df_results['away_team'] == visitante)) |
        ((df_results['home_team'] == visitante) & (df_results['away_team'] == local))
    )
    # <= hoy para incluir partidos jugados hoy
    hist = df_results[mask & (df_results['date'] <= hoy)].copy()
    if hist.empty:
        return
    row = hist.sort_values('date', ascending=False).iloc[0]
    if row['date'] < pd.Timestamp('2026-06-01'):
        return
    resultado = _resultado_real_historico(row, local, visitante)
    if resultado:
        guardar_resultado(partido_id, resultado, 1.0)
        actualizar_estado_partido(partido_id, 'jugado')


def _generar_predicciones_fixture(lista_partidos, df_results, df_stats, dict_elo):
    """Genera y persiste predicciones para todos los partidos del fixture al arrancar."""
    # CSV local como fuente canónica de fechas del Mundial 2026
    df_local = cargar_fixture_local()
    fecha_local_map = {}
    if not df_local.empty:
        for _, row in df_local.iterrows():
            if pd.notna(row['date']):
                key = (row['home_team'], row['away_team'])
                fecha_local_map[key] = row['date'].strftime('%Y-%m-%d')
                fecha_local_map[(row['away_team'], row['home_team'])] = row['date'].strftime('%Y-%m-%d')

    hoy = pd.Timestamp(datetime.now().date())
    fecha_hoy = hoy.strftime('%Y-%m-%d')

    for partido_str in lista_partidos:
        if ' vs ' not in partido_str:
            continue
        try:
            local_crudo, visitante_crudo = partido_str.split(' vs ', 1)
            local = normalizar_pais(local_crudo)
            visitante = normalizar_pais(visitante_crudo)

            # 1º: buscar fecha en CSV local (fuente más fiable)
            fecha_partido = fecha_local_map.get((local, visitante)) or \
                            fecha_local_map.get((visitante, local))

            # 2º: fallback en GitHub (solo partidos del Mundial 2026)
            if fecha_partido is None and df_results is not None and not df_results.empty:
                mask_wc = (
                    ((df_results['home_team'] == local) & (df_results['away_team'] == visitante)) |
                    ((df_results['home_team'] == visitante) & (df_results['away_team'] == local))
                ) & df_results['tournament'].str.lower().str.contains('world cup', na=False) \
                  & (df_results['date'] >= pd.Timestamp('2026-06-01'))
                wc_matches = df_results[mask_wc]
                if not wc_matches.empty:
                    fecha_partido = wc_matches.sort_values('date').iloc[0]['date'].strftime('%Y-%m-%d')

            # 3º: último recurso = hoy
            if fecha_partido is None:
                fecha_partido = fecha_hoy

            pred, prob, confianza = _predecir_poisson(local, visitante, df_results, df_stats, dict_elo)
            partido_id = buscar_o_crear_partido(fecha_partido, local, visitante, 'World Cup', 'programado')
            buscar_o_crear_prediccion(partido_id, 'poisson', pred, prob, confianza)
            # Persistir resultado si el partido ya está completo en el CSV local
            _persistir_resultado_desde_local(partido_id, local, visitante, df_local)
            if df_results is not None:
                _persistir_resultado_si_disponible(partido_id, local, visitante, df_results)
        except Exception:
            continue


@st.cache_data(ttl=1800)
def cargar_results_git():
    try:
        url_git = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
        df = pd.read_csv(url_git)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['home_team'] = df['home_team'].apply(normalizar_pais)
        df['away_team'] = df['away_team'].apply(normalizar_pais)
        if 'neutral' in df.columns:
            df['neutral'] = df['neutral'].astype(str).str.upper().eq('TRUE')
        else:
            df['neutral'] = False
        if 'tournament' not in df.columns:
            df['tournament'] = 'Friendly'
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def cargar_goalscorers_git():
    try:
        url_goals = "https://raw.githubusercontent.com/martj42/international_results/refs/heads/master/goalscorers.csv"
        df = pd.read_csv(url_goals)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['home_team'] = df['home_team'].apply(normalizar_pais)
        df['away_team'] = df['away_team'].apply(normalizar_pais)
        df['team'] = df['team'].apply(normalizar_pais)
        df['penalty'] = df['penalty'].astype(str).str.upper().eq('TRUE').astype(int)
        df['own_goal'] = df['own_goal'].astype(str).str.upper().eq('TRUE').astype(int)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def cargar_partidos_mundial_historicos():
    """Retorna todos los partidos del Mundial con resultado.
    Usa el CSV local como fuente primaria (más actualizado) y complementa con GitHub.
    """
    try:
        hoy = pd.Timestamp(datetime.now().date())
        filas = []

        # ── Fuente 1: CSV local de FootyStats (más actualizado) ──
        df_local = cargar_fixture_local()
        if not df_local.empty:
            completados = df_local[
                (df_local['status'] == 'complete') &
                (df_local['home_score'].notna()) &
                (df_local['away_score'].notna())
            ].copy()
            for _, row in completados.iterrows():
                filas.append({
                    'Fecha': row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else '',
                    'Torneo': 'FIFA World Cup 2026',
                    'Local': row['home_team'],
                    'Score Local': int(row['home_score']),
                    'Score Visita': int(row['away_score']),
                    'Visita': row['away_team'],
                })

        if filas:
            df_out = pd.DataFrame(filas).sort_values('Fecha', ascending=False).reset_index(drop=True)
            return df_out

        # ── Fuente 2: GitHub (fallback) ──
        df_git = cargar_results_git()
        if df_git is None or df_git.empty:
            return pd.DataFrame(columns=['Fecha', 'Torneo', 'Local', 'Score Local', 'Score Visita', 'Visita'])
        df_git = df_git.copy()
        df_git['date'] = pd.to_datetime(df_git['date'], errors='coerce')
        mundiales = df_git[
            (df_git['date'] <= hoy) &
            df_git['tournament'].fillna('').str.lower().str.contains('world cup', na=False) &
            df_git['home_score'].notna()
        ].sort_values('date', ascending=False)
        if mundiales.empty:
            return pd.DataFrame(columns=['Fecha', 'Torneo', 'Local', 'Score Local', 'Score Visita', 'Visita'])
        mundiales = mundiales[['date', 'tournament', 'home_team', 'home_score', 'away_score', 'away_team']].copy()
        mundiales = mundiales.rename(columns={
            'date': 'Fecha', 'tournament': 'Torneo', 'home_team': 'Local',
            'home_score': 'Score Local', 'away_score': 'Score Visita', 'away_team': 'Visita'
        })
        mundiales['Fecha'] = mundiales['Fecha'].dt.strftime('%Y-%m-%d')
        return mundiales
    except Exception:
        return pd.DataFrame(columns=['Fecha', 'Torneo', 'Local', 'Score Local', 'Score Visita', 'Visita'])

@st.cache_resource(show_spinner="🧠 Entrenando Skynet ML por primera vez (~60s)...")
def cargar_o_entrenar_cerebro_ml():
    ruta = os.path.join(ROOT_DIR, 'ai', 'cerebro_mundial.pkl')
    if not os.path.exists(ruta):
        try:
            from ai.entrenador import entrenar_modelo_mundial
            entrenar_modelo_mundial()
        except Exception as e:
            st.warning(f"No se pudo entrenar el modelo ML: {e}")
            return None
    if os.path.exists(ruta):
        modelo_data = joblib.load(ruta)
        if isinstance(modelo_data, dict) and 'model' in modelo_data:
            return modelo_data
        return {'model': modelo_data, 'accuracy': None, 'features': None}
    return None

@st.cache_data(ttl=1800)
def obtener_partidos_mundial_futuros():
    """Retorna los partidos del Mundial 2026 aún no jugados.
    Prefiere el CSV local (más fiable); cae en GitHub como respaldo.
    """
    hoy = pd.Timestamp(datetime.now().date())

    # ── Fuente primaria: CSV local ──
    df_local = cargar_fixture_local()
    if not df_local.empty:
        futuros = df_local[
            (df_local['status'] == 'incomplete') |
            (df_local['date'] >= hoy)
        ].copy()
        # Solo los que aún no tienen resultado completo
        futuros = futuros[df_local['status'] != 'complete']
        partidos = []
        for _, row in futuros.sort_values('date').iterrows():
            partido = f"{row['home_team']} vs {row['away_team']}"
            if partido not in partidos:
                partidos.append(partido)
        if partidos:
            return partidos

    # ── Fallback: GitHub ──
    try:
        df = cargar_results_git()
        if df.empty:
            return ["No se encontraron partidos del Mundial."]
        futuros = df[(df['date'] >= hoy) & df['tournament'].str.lower().str.contains('world cup', na=False)]
        if futuros.empty:
            futuros = df[df['date'] >= hoy]
        partidos = []
        for _, row in futuros.sort_values('date').iterrows():
            partido = f"{row['home_team']} vs {row['away_team']}"
            if partido not in partidos:
                partidos.append(partido)
        return partidos if partidos else ["No se encontraron partidos del Mundial."]
    except Exception:
        return ["Error de red"]

@st.cache_data(ttl=1800)
def obtener_todos_los_partidos_mundial():
    """Todos los partidos del Mundial 2026 (pasados + futuros) para el batch completo.
    Prefiere el CSV local; cae en GitHub como respaldo.
    """
    # ── Fuente primaria: CSV local ──
    df_local = cargar_fixture_local()
    if not df_local.empty:
        partidos = []
        for _, row in df_local.sort_values('date').iterrows():
            partido = f"{row['home_team']} vs {row['away_team']}"
            if partido not in partidos:
                partidos.append(partido)
        if partidos:
            return partidos

    # ── Fallback: GitHub ──
    try:
        df = cargar_results_git()
        if df.empty:
            return []
        wc = df[
            (df['date'] >= pd.Timestamp('2026-06-01')) &
            (df['date'] <= pd.Timestamp('2026-07-19')) &
            df['tournament'].str.lower().str.contains('world cup', na=False)
        ]
        partidos = []
        for _, row in wc.sort_values('date').iterrows():
            partido = f"{row['home_team']} vs {row['away_team']}"
            if partido not in partidos:
                partidos.append(partido)
        return partidos
    except Exception:
        return []

# Inicializar recursos
df_stats = cargar_footystats()
dict_elo = cargar_datos_elo()
lista_partidos = obtener_partidos_mundial_futuros()
modelo_ml_data = cargar_o_entrenar_cerebro_ml()
modelo_ml = modelo_ml_data['model'] if modelo_ml_data is not None else None
modelo_ml_accuracy = modelo_ml_data.get('accuracy') if modelo_ml_data is not None else None

# Generar predicciones para TODO el fixture del Mundial al arrancar (solo una vez por sesión)
if 'predicciones_generadas' not in st.session_state:
    _df_results_batch = cargar_results_git()
    _todos_los_partidos = obtener_todos_los_partidos_mundial()
    _generar_predicciones_fixture(_todos_los_partidos, _df_results_batch, df_stats, dict_elo)
    st.session_state['predicciones_generadas'] = True
    st.rerun()  # Fuerza re-render para que el backtesting lea la DB ya poblada

# Sincronizar resultados en cada carga usando CSV local (sin latencia de red)
_df_local_sync = cargar_fixture_local()
_df_results_sync = cargar_results_git()
for _pid, _local, _visitante in obtener_partidos_sin_resultado():
    _persistir_resultado_desde_local(_pid, _local, _visitante, _df_local_sync)
    _persistir_resultado_si_disponible(_pid, _local, _visitante, _df_results_sync)

# ==========================================
# 2. LÓGICA DE EXTRACCIÓN Y PREDICCIÓN
# ==========================================
st.markdown("### ⚡ Panel de Control Quant")

partido_seleccionado = st.selectbox("Selecciona un partido del Fixture:", lista_partidos, index=0)

if partido_seleccionado and " vs " in partido_seleccionado:
    local_crudo, visitante_crudo = partido_seleccionado.split(" vs ")
    local = normalizar_pais(local_crudo)
    visitante = normalizar_pais(visitante_crudo)
    
    st.markdown(f"## 🏴 {local} vs {visitante} 🏴")
    
    with st.spinner(f'Procesando Red Neuronal y Modelos Estadísticos para {local} vs {visitante}...'):
        
        # 1. H2H Histórico
        h2h_df = testear_h2h_git(local, visitante)
        victorias_l, empates, victorias_v = 0, 0, 0
        if h2h_df is not None and not h2h_df.empty:
            h2h_df = h2h_df[pd.notna(h2h_df['home_score']) & pd.notna(h2h_df['away_score'])]
            for _, p in h2h_df.iterrows():
                if normalizar_pais(p['home_team']) == local:
                    if p['home_score'] > p['away_score']: victorias_l += 1
                    elif p['home_score'] < p['away_score']: victorias_v += 1
                    else: empates += 1
                else:
                    if p['away_score'] > p['home_score']: victorias_l += 1
                    elif p['away_score'] < p['home_score']: victorias_v += 1
                    else: empates += 1

        # 2. Obtener Métricas y ELO
        stats_l = df_stats[df_stats['Country'].apply(normalizar_country_footystats) == local] if df_stats is not None else None
        stats_v = df_stats[df_stats['Country'].apply(normalizar_country_footystats) == visitante] if df_stats is not None else None

        def get_metric(df_team, col):
            return _get_metric(df_team, col)

        def get_avg_metric(df_team, col):
            return _get_avg_metric(df_team, col)

        xg_l_fs, xg_v_fs = get_avg_metric(stats_l, 'xG'), get_avg_metric(stats_v, 'xG')
        c_l, c_v = get_avg_metric(stats_l, 'Corners'), get_avg_metric(stats_v, 'Corners')
        t_l, t_v = get_avg_metric(stats_l, 'Cards'), get_avg_metric(stats_v, 'Cards')

        elo_base_l = float(dict_elo.get(local, 1600))
        elo_base_v = float(dict_elo.get(visitante, 1500))
        diferencia_elo = elo_base_l - elo_base_v

        # 3. MOTOR POISSON (Goles Esperados)
        df_results = cargar_results_git()
        home_goals, home_conceded, home_win_rate = _team_recent_stats(df_results, local, pd.Timestamp(datetime.now().date()), n=3)
        away_goals, away_conceded, away_win_rate = _team_recent_stats(df_results, visitante, pd.Timestamp(datetime.now().date()), n=3)
        home_goal_diff = home_goals - home_conceded
        away_goal_diff = away_goals - away_conceded

        if not np.isnan(xg_l_fs) and not np.isnan(xg_v_fs):
             xg_l_final = max(0.1, 0.5 * xg_l_fs + 0.2 * home_goals + 0.15 * home_win_rate + 0.1 * home_goal_diff + 0.05 * max(diferencia_elo / 100, 0))
             xg_v_final = max(0.1, 0.5 * xg_v_fs + 0.2 * away_goals + 0.15 * away_win_rate + 0.1 * away_goal_diff + 0.05 * max(-diferencia_elo / 100, 0))
        else:
             ventaja = (diferencia_elo / 100) * 0.25
             xg_l_final, xg_v_final = max(0.1, 1.3 + ventaja), max(0.1, 1.3 - ventaja)
        
        prob_l = [poisson.pmf(i, xg_l_final) for i in range(6)]
        prob_v = [poisson.pmf(i, xg_v_final) for i in range(6)]
        matriz = np.outer(prob_l, prob_v)
        p_local_poisson, p_empate_poisson, p_visitante_poisson = np.sum(np.tril(matriz, -1)), np.sum(np.diag(matriz)), np.sum(np.triu(matriz, 1))

        idx_max = np.unravel_index(np.argmax(matriz), matriz.shape)
        marcador_probable = f"{local} {idx_max[0]} - {idx_max[1]} {visitante}"
        prob_marcador = float(matriz[idx_max])

        if p_local_poisson >= p_empate_poisson and p_local_poisson >= p_visitante_poisson:
            prediccion_poisson = f"Victoria {local}"
            prob_prediccion = p_local_poisson
        elif p_visitante_poisson > p_empate_poisson:
            prediccion_poisson = f"Victoria {visitante}"
            prob_prediccion = p_visitante_poisson
        else:
            prediccion_poisson = "Empate"
            prob_prediccion = p_empate_poisson

        confianza = "Alta" if prob_prediccion >= 0.4 else "Media" if prob_prediccion >= 0.25 else "Baja"

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        partido_id = buscar_o_crear_partido(
            fecha=fecha_hoy,
            local=local,
            visitante=visitante,
            torneo='World Cup',
            estado='programado',
        )
        buscar_o_crear_prediccion(
            partido_id=partido_id,
            modelo='poisson',
            prediccion=prediccion_poisson,
            probabilidad=float(prob_prediccion),
            confianza=confianza,
        )

        resultado_real = None
        if df_results is not None and not df_results.empty:
            _persistir_resultado_si_disponible(partido_id, local, visitante, df_results)

        # 4. MOTOR MACHINE LEARNING (Random Forest)
        p_local_ml, p_empate_ml, p_visitante_ml = 0, 0, 0
        
        # BLINDAJE: Solo ejecutamos si el modelo cargó y tenemos datos
        if modelo_ml is not None and not np.isnan(diferencia_elo):
            try:
                df_goals = cargar_goalscorers_git()
                current_date = pd.Timestamp(datetime.now().date())
                home_penalty_avg = _team_penalty_avg(df_goals, local, current_date, n=3)
                away_penalty_avg = _team_penalty_avg(df_goals, visitante, current_date, n=3)
                tournament, neutral_flag = _match_context(df_results, local, visitante)
                tournament_importance = _tournament_importance(tournament)

                X_pred = pd.DataFrame([[
                    elo_base_l,
                    elo_base_v,
                    diferencia_elo,
                    1,
                    neutral_flag,
                    tournament_importance,
                    home_goals,
                    home_conceded,
                    home_goal_diff,
                    home_win_rate,
                    away_goals,
                    away_conceded,
                    away_goal_diff,
                    away_win_rate,
                    home_penalty_avg,
                    away_penalty_avg
                ]], columns=[
                    'elo_local', 'elo_visitante', 'diferencia_elo', 'es_oficial',
                    'neutral_flag', 'tournament_importance',
                    'home_avg_goals_scored', 'home_avg_goals_conceded', 'home_avg_goal_diff', 'home_recent_win_rate',
                    'away_avg_goals_scored', 'away_avg_goals_conceded', 'away_avg_goal_diff', 'away_recent_win_rate',
                    'home_penalty_avg', 'away_penalty_avg'
                ])
                
                probabilidades_ml = modelo_ml.predict_proba(X_pred)[0]
                clase_ml = dict(zip(modelo_ml.classes_, probabilidades_ml))
                p_visitante_ml = clase_ml.get(-1, 0.0)
                p_empate_ml = clase_ml.get(0, 0.0)
                p_local_ml = clase_ml.get(1, 0.0)

                # Alineamos la salida de IA Predictiva con el motor Poisson más actual.
                # Poisson es la base actual, y el ML aporta un ajuste histórico ligero.
                blend_weight_ml = 0.20
                p_local_ml = blend_weight_ml * p_local_ml + (1 - blend_weight_ml) * p_local_poisson
                p_empate_ml = blend_weight_ml * p_empate_ml + (1 - blend_weight_ml) * p_empate_poisson
                p_visitante_ml = blend_weight_ml * p_visitante_ml + (1 - blend_weight_ml) * p_visitante_poisson
                total_prob = p_local_ml + p_empate_ml + p_visitante_ml
                if total_prob > 0:
                    p_local_ml /= total_prob
                    p_empate_ml /= total_prob
                    p_visitante_ml /= total_prob

                diff_sum = abs(p_local_ml - p_local_poisson) + abs(p_empate_ml - p_empate_poisson) + abs(p_visitante_ml - p_visitante_poisson)
                alineacion = max(0.0, min(1.0, 1.0 - diff_sum / 2.0))
            except Exception:
                st.warning("El modelo está calibrando...")
        total_corners = c_l + c_v
        total_tarjetas = t_l + t_v

    # ==========================================
    # 3. RENDERIZADO DE INTERFAZ
    # ==========================================
    tab_ml, tab_poisson, tab_mercados, tab_h2h, tab_mundial, tab_auditoria = st.tabs(["🤖 IA Predictiva", "📊 Modelo Poisson", "💰 Mercados Cuantitativos", "⚽ Historial H2H", "🏆 Mundial Hasta Ahora", "✅ Auditoría de Estimados"])
    
    with tab_ml:
        if modelo_ml:
            accuracy_text = f"{modelo_ml_accuracy * 100:.2f}%" if modelo_ml_accuracy is not None else "N/A"
            st.html(f"""
            <div class="ml-box">
                <h4 style='color: white; margin-top:0px;'>🤖 Skynet Random Forest (Accuracy: {accuracy_text})</h4>
                <p style='color: #a7f3d0;'>Basado en Rankings ELO, resultados históricos y métricas recientes de goles y penales.</p>
            </div>
            """)
            
            st.write("")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Prob. Victoria {local}", f"{p_local_ml*100:.1f}%")
            c2.metric("Prob. Empate", f"{p_empate_ml*100:.1f}%")
            c3.metric(f"Prob. Victoria {visitante}", f"{p_visitante_ml*100:.1f}%")
            
            st.progress(float(p_local_ml), text=f"Fuerza Local ({local})")
            st.progress(float(p_visitante_ml), text=f"Fuerza Visitante ({visitante})")
        else:
            st.error("No se encontró el cerebro_mundial.pkl. Entrena el modelo primero.")

    with tab_poisson:
        st.markdown(f"**Motor Estadístico Clásico:** Distribución basada en xG ({xg_l_final:.2f} vs {xg_v_final:.2f})")
        st.markdown("_Probabilidades calculadas a partir de xG, goles recientes y métricas de los últimos 3 partidos._")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Victoria {local}", f"{p_local_poisson*100:.1f}%")
        c2.metric("Empate", f"{p_empate_poisson*100:.1f}%")
        c3.metric(f"Victoria {visitante}", f"{p_visitante_poisson*100:.1f}%")

        st.info(f"🧠 Recomendación Poisson: {prediccion_poisson} · Marcador más probable: {marcador_probable} ({prob_marcador * 100:.1f}%)")

        chart_data = pd.DataFrame({
            'Goles': list(range(6)),
            local: prob_l,
            visitante: prob_v
        })
        chart_data = chart_data.melt(id_vars=['Goles'], value_vars=[local, visitante], var_name='Equipo', value_name='Probabilidad')
        chart = alt.Chart(chart_data).mark_bar(opacity=0.85).encode(
            x=alt.X('Goles:O', title='Goles', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Probabilidad:Q', title='Probabilidad', axis=alt.Axis(format='%')),
            color=alt.Color('Equipo:N', title='Equipo'),
            tooltip=[alt.Tooltip('Equipo:N', title='Equipo'), alt.Tooltip('Goles:O', title='Goles'), alt.Tooltip('Probabilidad:Q', title='Probabilidad', format='.1%')]
        ).properties(width=520)
        chart = chart.configure_axis(labelFontSize=12, titleFontSize=14)
        chart = chart.configure_legend(titleFontSize=13, labelFontSize=12)
        st.altair_chart(chart, use_container_width=True)
        
    with tab_mercados:
        col1, col2 = st.columns(2)
        with col1:
            st.html(f"""
            <div class="sportsbook-box">
                <h4 style='margin-top:0px;'>🚩 Tiros de Esquina Promedio</h4>
                <p><strong>{local}:</strong> {c_l:.2f}</p>
                <p><strong>{visitante}:</strong> {c_v:.2f}</p>
                <hr>
                <h3 style='color:{"#3b82f6" if pd.notna(total_corners) else "#ef4444"};'>Línea: Más de {int(total_corners - 1) if pd.notna(total_corners) else 0}.5</h3>
            </div>
            """)
            
        with col2:
            st.html(f"""
            <div class="sportsbook-box">
                <h4 style='margin-top:0px;'>🟨 Tarjetas Mostradas Promedio</h4>
                <p><strong>{local}:</strong> {t_l:.2f}</p>
                <p><strong>{visitante}:</strong> {t_v:.2f}</p>
                <hr>
                <h3 style='color:{"#ef4444" if pd.notna(total_tarjetas) else "#ef4444"};'>Línea: Más de {int(total_tarjetas - 0.5) if pd.notna(total_tarjetas) else 0}.5</h3>
            </div>
            """)

        def _safe_int(val):
            try:
                return int(val) if pd.notna(val) else None
            except (TypeError, ValueError):
                return None

        footy_metrics = pd.DataFrame([
            {'Equipo': local, 'P': _safe_int(get_metric(stats_l, 'P')), 'xG': xg_l_fs, 'Corners': c_l, 'Cards': t_l},
            {'Equipo': visitante, 'P': _safe_int(get_metric(stats_v, 'P')), 'xG': xg_v_fs, 'Corners': c_v, 'Cards': t_v}
        ])

        if not footy_metrics[['xG', 'Corners', 'Cards']].isnull().all().all():
            st.markdown("### 📈 Datos de FootyStats (últimos partidos)")
            st.dataframe(footy_metrics, use_container_width=True)
        else:
            st.info("No se encontraron datos de FootyStats para los equipos seleccionados.")
            
    with tab_h2h:
        if h2h_df is not None and not h2h_df.empty:
            h2h_validos = h2h_df[pd.notna(h2h_df['home_score']) & pd.notna(h2h_df['away_score'])].copy()
            h2h_validos['date'] = pd.to_datetime(h2h_validos['date'], errors='coerce')
            h2h_validos = h2h_validos[h2h_validos['date'] < pd.Timestamp(datetime.now().date())]
            if not h2h_validos.empty:
                st.markdown(f"📋 📋 **Resumen Total:** {local} ({victorias_l}) - Empates ({empates}) - {visitante} ({victorias_v})")
                h2h_validos = h2h_validos.rename(columns={
                    'date': 'Fecha',
                    'tournament': 'Torneo',
                    'home_team': 'Local',
                    'home_score': 'Score Local',
                    'away_score': 'Score Visita',
                    'away_team': 'Visita'
                })
                st.dataframe(h2h_validos[['Fecha', 'Torneo', 'Local', 'Score Local', 'Score Visita', 'Visita']], use_container_width=True, hide_index=True)
            else:
                st.info("No hay encuentros con resultado disponible para mostrar.")
        else:
            st.info("No hay historial directo de enfrentamientos en la base de datos.")

    with tab_mundial:
        st.markdown("### 🏆 Partidos del Mundial hasta ahora")
        df_mundial = cargar_partidos_mundial_historicos()
        if not df_mundial.empty:
            st.dataframe(df_mundial, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron partidos del Mundial con resultados cerrados.")

    with tab_auditoria:
        col_ref1, col_ref2 = st.columns([4, 1])
        with col_ref2:
            if st.button("🔄 Forzar actualización", use_container_width=True):
                cargar_results_git.clear()
                _df_force = cargar_results_git()
                for _pid2, _loc2, _vis2 in obtener_partidos_sin_resultado():
                    _persistir_resultado_si_disponible(_pid2, _loc2, _vis2, _df_force)
                st.rerun()
        registros = obtener_predicciones_auditoria()
        if registros:
            df_auditoria = pd.DataFrame(registros)
            total_r = len(df_auditoria)
            resueltos = df_auditoria[df_auditoria['Resultado_Real'] != 'Pendiente'].shape[0]
            st.caption(f"Total: {total_r} predicciones · {resueltos} resueltas · {total_r - resueltos} pendientes")
            st.dataframe(df_auditoria, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay predicciones registradas.")
