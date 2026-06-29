import pandas as pd
import sys
import os

# ==========================================
# BLINDAJE DE RUTAS PARA EL MDM
# ==========================================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.diccionario import normalizar_pais

def testear_h2h_git(equipo1_crudo, equipo2_crudo):
    """
    Busca el historial directo (H2H) entre dos equipos en el dataset de GitHub.
    Implementa resolución de entidades (MDM) y manejo de tablas vacías.
    """
    # 1. Normalizamos lo que pide el usuario (Ej: "England" -> "Inglaterra")
    equipo1 = normalizar_pais(equipo1_crudo)
    equipo2 = normalizar_pais(equipo2_crudo)
    
    url_git = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    
    try:
        df = pd.read_csv(url_git)
        
        # 2. Aplicamos el Diccionario al Dataset de GitHub en memoria
        # Esto nos asegura que todo se compare en el mismo idioma estandarizado
        df['home_team_norm'] = df['home_team'].apply(normalizar_pais)
        df['away_team_norm'] = df['away_team'].apply(normalizar_pais)
        
        # 3. Filtramos buscando exactamente el cruce entre los dos equipos
        mask_robusta = (
            ((df['home_team_norm'] == equipo1) & (df['away_team_norm'] == equipo2)) |
            ((df['home_team_norm'] == equipo2) & (df['away_team_norm'] == equipo1))
        )
        
        h2h_df = df[mask_robusta].copy()
        
        # 4. PROTECCIÓN CONTRA EL KEYERROR
        # Si nunca han jugado en la historia, devolvemos un DataFrame vacío pero seguro
        if h2h_df.empty:
            return pd.DataFrame() 
            
        # 5. Si hay datos, los ordenamos desde el más reciente al más antiguo
        if 'date' in h2h_df.columns:
            h2h_df = h2h_df.sort_values('date', ascending=False)
            
        return h2h_df
        
    except Exception as e:
        print(f"Error procesando H2H desde Git: {e}")
        return pd.DataFrame()

# Bloque de prueba local
if __name__ == "__main__":
    df_test = testear_h2h_git("Argentina", "Colombia")
    if not df_test.empty:
        print("Historial encontrado con éxito.")
        print(df_test.head())
    else:
        print("No hay historial o falló la conexión.")