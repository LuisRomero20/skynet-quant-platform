import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import os
import sys

# Blindaje de rutas
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.diccionario import normalizar_pais

def _normalizar_goals_df(df_goals):
    df_goals['date'] = pd.to_datetime(df_goals['date'], errors='coerce')
    df_goals['home_team'] = df_goals['home_team'].apply(normalizar_pais)
    df_goals['away_team'] = df_goals['away_team'].apply(normalizar_pais)
    df_goals['team'] = df_goals['team'].apply(normalizar_pais)
    df_goals['penalty'] = df_goals['penalty'].astype(str).str.upper().eq('TRUE').astype(int)
    df_goals['own_goal'] = df_goals['own_goal'].astype(str).str.upper().eq('TRUE').astype(int)
    return df_goals


def _tournament_importance(tournament):
    if pd.isna(tournament):
        return 0
    torneo = str(tournament).lower()
    if any(key in torneo for key in ['world cup', 'euro', 'copa', 'nations league', 'confederations cup', 'champions league']):
        return 3
    if any(key in torneo for key in ['qualifier', 'qualification', 'play-off', 'gold cup', 'afcon', 'concacaf', 'coppa', 'world cup qualifying']):
        return 2
    if 'friendly' in torneo or 'exhibition' in torneo or 'cup' not in torneo and 'cup' not in torneo:
        return 1
    return 1


def _team_recent_stats(df_matches, team, current_date, n=3):
    team_matches = df_matches[((df_matches['home_team'] == team) | (df_matches['away_team'] == team)) &
                               (df_matches['date'] < current_date)].sort_values('date', ascending=False).head(n)
    if team_matches.empty:
        return 0.0, 0.0, 0.0

    goals_scored = []
    goals_conceded = []
    wins = 0

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

    return (
        float(np.mean(goals_scored)),
        float(np.mean(goals_conceded)),
        float(wins / len(team_matches))
    )


def _team_penalty_avg(df_goals, team, current_date, n=3):
    team_goals = df_goals[(df_goals['team'] == team) & (df_goals['date'] < current_date)]
    if team_goals.empty:
        return 0.0

    recent_penalties = team_goals.groupby('date')['penalty'].sum().sort_index(ascending=False).head(n)
    return float(recent_penalties.mean()) if not recent_penalties.empty else 0.0


def _build_recent_match_features(df_matches, df_goals, window=3):
    df_matches = df_matches.copy()
    df_matches['match_id'] = df_matches.index

    home = pd.DataFrame({
        'match_id': df_matches['match_id'],
        'team': df_matches['home_team'],
        'date': df_matches['date'],
        'goals_scored': df_matches['home_score'],
        'goals_conceded': df_matches['away_score'],
        'is_win': (df_matches['home_score'] > df_matches['away_score']).astype(int),
        'side': 'home'
    })

    away = pd.DataFrame({
        'match_id': df_matches['match_id'],
        'team': df_matches['away_team'],
        'date': df_matches['date'],
        'goals_scored': df_matches['away_score'],
        'goals_conceded': df_matches['home_score'],
        'is_win': (df_matches['away_score'] > df_matches['home_score']).astype(int),
        'side': 'away'
    })

    team_df = pd.concat([home, away], ignore_index=True)
    team_df = team_df.sort_values(['team', 'date'])

    grouped = team_df.groupby('team')[['goals_scored', 'goals_conceded', 'is_win']]
    team_df[['avg_goals_scored', 'avg_goals_conceded', 'recent_win_rate']] = grouped.shift().rolling(window, min_periods=1).mean().reset_index(level=0, drop=True)

    goals_by_team = df_goals.groupby(['team', 'date'])['penalty'].sum().reset_index()
    goals_by_team = goals_by_team.sort_values(['team', 'date'])
    goals_by_team['penalty_avg'] = goals_by_team.groupby('team')['penalty'].shift().rolling(window, min_periods=1).mean().reset_index(level=0, drop=True)

    team_df = team_df.merge(goals_by_team[['team', 'date', 'penalty_avg']], on=['team', 'date'], how='left')
    team_df['penalty_avg'] = team_df['penalty_avg'].fillna(0.0)

    home_features = team_df[team_df['side'] == 'home'][[
        'match_id', 'avg_goals_scored', 'avg_goals_conceded', 'recent_win_rate', 'penalty_avg'
    ]].rename(columns={
        'avg_goals_scored': 'home_avg_goals_scored',
        'avg_goals_conceded': 'home_avg_goals_conceded',
        'recent_win_rate': 'home_recent_win_rate',
        'penalty_avg': 'home_penalty_avg'
    })

    away_features = team_df[team_df['side'] == 'away'][[
        'match_id', 'avg_goals_scored', 'avg_goals_conceded', 'recent_win_rate', 'penalty_avg'
    ]].rename(columns={
        'avg_goals_scored': 'away_avg_goals_scored',
        'avg_goals_conceded': 'away_avg_goals_conceded',
        'recent_win_rate': 'away_recent_win_rate',
        'penalty_avg': 'away_penalty_avg'
    })

    features = df_matches[['match_id']].merge(home_features, on='match_id').merge(away_features, on='match_id')
    return features


def entrenar_modelo_mundial():
    print("🧠 Iniciando el Entrenamiento del Motor Predictivo (Skynet ML)...")
    
    # 1. CARGA DE DATOS HISTÓRICOS
    url_git = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    url_goals = "https://raw.githubusercontent.com/martj42/international_results/refs/heads/master/goalscorers.csv"
    print("⏳ Descargando dataset histórico (1872 - Presente)...")
    df = pd.read_csv(url_git)
    
    print("⏳ Descargando dataset de goleadores y penales...")
    df_goals = pd.read_csv(url_goals)
    df_goals = _normalizar_goals_df(df_goals)
    
    # 2. FEATURE ENGINEERING
    print("⏳ Procesando variables objetivo (Target)...")
    
    def determinar_resultado(row):
        if row['home_score'] > row['away_score']: return 1
        elif row['home_score'] == row['away_score']: return 0
        else: return -1
        
    df['resultado'] = df.apply(determinar_resultado, axis=1)
    
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df[df['date'].dt.year >= 2000]
    
    df['home_team'] = df['home_team'].apply(normalizar_pais)
    df['away_team'] = df['away_team'].apply(normalizar_pais)

    # 3. ENRIQUECIMIENTO CON ELO
    print("⏳ Inyectando Rankings ELO a la matriz de entrenamiento...")
    ruta_elo = os.path.join(ROOT_DIR, 'data', 'rankings_elo.csv')
    
    if not os.path.exists(ruta_elo):
        print("❌ CRÍTICO: No se encontró rankings_elo.csv.")
        return
        
    df_elo = pd.read_csv(ruta_elo)
    df_elo.columns = df_elo.columns.str.strip()
    if 'Team' in df_elo.columns and 'Elo' in df_elo.columns:
        df_elo = df_elo.rename(columns={'Team': 'Seleccion', 'Elo': 'Puntaje_Elo'})
    if 'Seleccion' not in df_elo.columns or 'Puntaje_Elo' not in df_elo.columns:
        raise ValueError(f"El CSV de Elo necesita columnas 'Seleccion'/'Puntaje_Elo' o 'Team'/'Elo'. Columnas encontradas: {list(df_elo.columns)}")
    dict_elo = dict(zip(df_elo['Seleccion'], df_elo['Puntaje_Elo']))
    
    # 🔥 EL FIX: Forzamos la conversión a numérico y llenamos los NaNs de forma agresiva
    df['elo_local'] = pd.to_numeric(df['home_team'].map(dict_elo), errors='coerce').fillna(1500.0)
    df['elo_visitante'] = pd.to_numeric(df['away_team'].map(dict_elo), errors='coerce').fillna(1500.0)
    
    df['diferencia_elo'] = df['elo_local'] - df['elo_visitante']
    df['es_oficial'] = np.where(df['tournament'] == 'Friendly', 0, 1)
    df['neutral_flag'] = np.where(df['neutral'] == True, 1,
                                  np.where(df['neutral'] == 'TRUE', 1,
                                           np.where(df['neutral'] == 'FALSE', 0, 0)))
    df['tournament_importance'] = df['tournament'].apply(_tournament_importance)

    df = df.sort_values('date').reset_index(drop=True)
    print("⏳ Calculando estadísticas recientes de goles y penales para cada partido...")
    recent_features = _build_recent_match_features(df, df_goals, window=3)
    df = pd.concat([df, recent_features.drop(columns=['match_id'])], axis=1)

    df['home_avg_goal_diff'] = df['home_avg_goals_scored'] - df['home_avg_goals_conceded']
    df['away_avg_goal_diff'] = df['away_avg_goals_scored'] - df['away_avg_goals_conceded']

    # 4. PREPARACIÓN DEL MODELO
    # 🔥 EL FIX PARTE 2: Nos aseguramos de que no pase ni un solo NaN al modelo
    X = df[[
        'elo_local', 'elo_visitante', 'diferencia_elo', 'es_oficial',
        'neutral_flag', 'tournament_importance',
        'home_avg_goals_scored', 'home_avg_goals_conceded', 'home_avg_goal_diff', 'home_recent_win_rate',
        'away_avg_goals_scored', 'away_avg_goals_conceded', 'away_avg_goal_diff', 'away_recent_win_rate',
        'home_penalty_avg', 'away_penalty_avg'
    ]].fillna(0)
    y = df['resultado']
    
    print(f"📊 Dataset final: {len(df)} partidos procesados sin datos nulos.")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 5. EL ENTRENAMIENTO
    print("⚙️ Entrenando Bosque Aleatorio (Random Forest)...")
    modelo = RandomForestClassifier(n_estimators=250, max_depth=14, class_weight='balanced_subsample', random_state=42)
    modelo.fit(X_train, y_train)
    
    # 6. EVALUACIÓN
    y_pred = modelo.predict(X_test)
    precision = accuracy_score(y_test, y_pred)
    
    print("\n✅ ¡ENTRENAMIENTO COMPLETADO!")
    print(f"🎯 Precisión del Modelo (Accuracy): {precision * 100:.2f}%")
    
    # 7. EXPORTACIÓN DEL CEREBRO
    ruta_modelo = os.path.join(ROOT_DIR, 'ai', 'cerebro_mundial.pkl')
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)
    
    cerebro = {
        'model': modelo,
        'accuracy': precision,
        'features': X.columns.tolist()
    }
    joblib.dump(cerebro, ruta_modelo)
    print(f"\n💾 Cerebro predictivo exportado y guardado en: {ruta_modelo}")

if __name__ == "__main__":
    entrenar_modelo_mundial()