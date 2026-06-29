import os
import pandas as pd

def procesar_csv_oficial():
    print("🚀 Iniciando Pipeline ETL con los CSVs oficiales de FootyStats...")
    
    # Apuntamos exactamente al archivo de equipos que acabas de descargar
    nombre_archivo = 'international-world-cup-teams-2026-to-2026-stats.csv'
    ruta_raw = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', nombre_archivo)
    ruta_limpia = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'footystats_form.csv')
    
    if not os.path.exists(ruta_raw):
        print(f"❌ ALERTA: No se encontró el archivo en {ruta_raw}")
        print(f"💡 Mueve el archivo '{nombre_archivo}' a la carpeta 'data'.")
        return None
        
    try:
        df = pd.read_csv(ruta_raw)
        
        # Mapeo Inteligente: Buscamos las columnas por palabras clave
        col_equipo = next((col for col in df.columns if 'name' in col.lower() or 'team' in col.lower()), None)
        col_partidos = next((col for col in df.columns if 'matches_played' in col.lower()), None)
        # El xG suele venir como 'xg_for_avg_overall'
        col_xg = next((col for col in df.columns if 'xg' in col.lower() and 'for' in col.lower()), None)
        col_corners = next((col for col in df.columns if 'corner' in col.lower()), None)
        col_cards = next((col for col in df.columns if 'card' in col.lower()), None)
        col_ppg = next((col for col in df.columns if 'points_per_game' in col.lower() or 'ppg' in col.lower()), None)
        
        # Armamos el DataFrame limpio con la estructura de nuestro modelo Quant
        df_limpio = pd.DataFrame()
        if col_equipo: df_limpio['Country'] = df[col_equipo]
        if col_partidos: df_limpio['P'] = df[col_partidos]
        if col_xg: df_limpio['xG'] = df[col_xg]
        if col_corners: df_limpio['Corners'] = df[col_corners]
        if col_cards: df_limpio['Cards'] = df[col_cards]
        if col_ppg: df_limpio['PPG'] = df[col_ppg]
        
        # Limpieza de nombres para el Diccionario Maestro
        df_limpio['Country'] = df_limpio['Country'].astype(str).str.replace(r'[^\x00-\x7F]+', '', regex=True).str.strip()
        
        print("\n🏆 ¡TRANSFORMACIÓN EXITOSA! Data extraída del CSV:")
        print(df_limpio.head(10).to_string(index=False))
        
        df_limpio.to_csv(ruta_limpia, index=False)
        print(f"\n💾 Data guardada como el motor estadístico principal en: {ruta_limpia}")
        
        return df_limpio
        
    except Exception as e:
        print(f"❌ Error procesando el CSV: {e}")
        return None

if __name__ == "__main__":
    procesar_csv_oficial()