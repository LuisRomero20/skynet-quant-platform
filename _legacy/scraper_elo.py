import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

os.makedirs('data/raw', exist_ok=True)
print("Iniciando extracción de Rankings Elo desde la web...")

url = "https://en.wikipedia.org/wiki/World_Football_Elo_Ratings"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    respuesta = requests.get(url, headers=headers)
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    
    tabla = soup.find('table', {'class': 'wikitable'})
    filas = tabla.find_all('tr')
    
    equipos = []
    
    for fila in filas[1:]:
        columnas = fila.find_all(['td', 'th'])
        
        # Asegurarnos de que la fila tenga al menos 4 columnas
        if len(columnas) >= 4:
            # ¡Ajustamos la puntería! Columna 2 es País, Columna 3 es Puntaje
            equipo = columnas[2].text.strip()
            puntaje = columnas[3].text.strip().split()[0]
            
            # Filtramos para que no guarde los subtítulos que dicen "Team" o cosas vacías
            if equipo != "Team" and len(equipo) > 2:
                equipos.append({
                    'Seleccion': equipo,
                    'Puntaje_Elo': puntaje
                })
            
    df_elo = pd.DataFrame(equipos)
    ruta = 'data/raw/rankings_elo.csv'
    df_elo.to_csv(ruta, index=False)
    
    print("\n======================================")
    print("✅ ¡RANKING ELO CORREGIDO Y DESCARGADO!")
    print(f"🌍 Equipos guardados: {len(df_elo)}")
    print(f"🥇 Equipo #1 actual: {df_elo.iloc[0]['Seleccion']} (Elo: {df_elo.iloc[0]['Puntaje_Elo']})")
    print(f"🥈 Equipo #2 actual: {df_elo.iloc[1]['Seleccion']} (Elo: {df_elo.iloc[1]['Puntaje_Elo']})")
    print("======================================")
    
except Exception as e:
    print(f"❌ Hubo un error al extraer los datos: {e}")