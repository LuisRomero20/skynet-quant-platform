import os
import sys
import pandas as pd

# Truco para importar desde core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.api_manager import APIManager

print("🧠 Construyendo el Dataset de Entrenamiento para la IA (Qatar 2022)...")

# 1. Cargar el Ranking Elo
ruta_elo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'rankings_elo.csv')
try:
    df_elo = pd.read_csv(ruta_elo)
    dict_elo = dict(zip(df_elo['Seleccion'], df_elo['Puntaje_Elo']))
except FileNotFoundError:
    print("⚠️ No se encontró rankings_elo.csv. Se usarán valores base 1500.")
    dict_elo = {}

# 2. Descargar TODOS los partidos de Qatar usando el APIManager
api = APIManager()
partidos = api.obtener_todos_los_partidos(temporada="2022")

if not partidos:
    print("❌ No se pudieron descargar los partidos. La API bloqueó la petición.")
    sys.exit()

datos_avanzados = []

for p in partidos:
    local = p['teams']['home']['name']
    visitante = p['teams']['away']['name']
    goles_local = p['goals']['home']
    goles_visitante = p['goals']['away']

    # Omitir partidos que aún no se han jugado o tienen errores
    if goles_local is None or goles_visitante is None:
        continue

    # 3. Matemática de Poder
    elo_local = float(dict_elo.get(local, 1500))
    elo_visitante = float(dict_elo.get(visitante, 1500))
    diferencia_elo = elo_local - elo_visitante

    # 4. Variable Objetivo (1=Local, X=Empate, 2=Visitante)
    if goles_local > goles_visitante: resultado_1x2 = '1'
    elif goles_local < goles_visitante: resultado_1x2 = '2'
    else: resultado_1x2 = 'X'

    datos_avanzados.append({
        'Local': local,
        'Visitante': visitante,
        'Elo_Local': elo_local,
        'Elo_Visitante': elo_visitante,
        'Diferencia_Elo': diferencia_elo,
        'Resultado_1X2': resultado_1x2
    })

# 5. Guardar el archivo procesado en disco duro
df_entrenamiento = pd.DataFrame(datos_avanzados)

# Crear la carpeta "processed" si no existe
carpeta_processed = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'processed')
os.makedirs(carpeta_processed, exist_ok=True)

ruta_guardado = os.path.join(carpeta_processed, 'dataset_qatar_avanzado.csv')
df_entrenamiento.to_csv(ruta_guardado, index=False)

print("\n========================================================")
print(f"✅ ¡Libro de texto creado! {len(df_entrenamiento)} partidos guardados.")
print(f"📁 Ruta: {ruta_guardado}")
print("========================================================\n")