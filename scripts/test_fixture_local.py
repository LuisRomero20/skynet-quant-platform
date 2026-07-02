import sys, os, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.diccionario import normalizar_pais

ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'international-world-cup-matches-2026-to-2026-stats.csv')
df = pd.read_csv(ruta)
df['date'] = pd.to_datetime(df['date_GMT'].str.extract(r'^(\w+ \d+ \d+)')[0], format='%b %d %Y', errors='coerce')
df['home_team'] = df['home_team_name'].apply(normalizar_pais)
df['away_team']  = df['away_team_name'].apply(normalizar_pais)
df['home_score'] = pd.to_numeric(df['home_team_goal_count'], errors='coerce')
df['away_score'] = pd.to_numeric(df['away_team_goal_count'], errors='coerce')

print("=== Proximos partidos (incomplete) ===")
incomplete = df[df['status'] == 'incomplete'].sort_values('date')
for _, row in incomplete.iterrows():
    print(f"  {row['date'].date()} | {row['home_team']} vs {row['away_team']}")

print("\n=== Ultimos 5 resultados (complete) ===")
complete = df[df['status'] == 'complete'].sort_values('date', ascending=False).head(5)
for _, row in complete.iterrows():
    print(f"  {row['date'].date()} | {row['home_team']} {int(row['home_score'])}-{int(row['away_score'])} {row['away_team']}")

print("\n=== fecha_local_map sample ===")
fecha_map = {}
for _, row in df.iterrows():
    if pd.notna(row['date']):
        fecha_map[(row['home_team'], row['away_team'])] = row['date'].strftime('%Y-%m-%d')

sample_keys = [('Espana','Austria'),('Brasil','Noruega'),('Mexico','Inglaterra'),('EE. UU.','Belgica')]
real_keys = [('España','Austria'),('Brasil','Noruega'),('México','Inglaterra'),('EE. UU.','Bélgica')]
for k in real_keys:
    result = fecha_map.get(k, 'NOT FOUND')
    print(f"  {k[0]} vs {k[1]} -> {result}")
