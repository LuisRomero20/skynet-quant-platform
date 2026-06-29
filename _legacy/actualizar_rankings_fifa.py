import os
import time
import pandas as pd
import undetected_chromedriver as uc
import sys

def actualizar_ranking_fifa():
    print("🚀 Iniciando tubería automatizada para extraer el Ranking Oficial FIFA...")
    url = "https://inside.fifa.com/es/fifa-world-ranking/men"
    
    options = uc.ChromeOptions()
    
    try:
        # Reutilizamos la versión 149 que ya validamos que funciona en tu entorno
        print("⏳ Levantando entorno Chromium (v149)...")
        driver = uc.Chrome(options=options, version_main=149)
        driver.get(url)
        
        print("⏳ Esperando 8 segundos para el renderizado asíncrono de Javascript...")
        time.sleep(8)
        
        html = driver.page_source
        tablas = pd.read_html(html)
        
        if not tablas:
            print("❌ No se encontró ninguna tabla en la estructura del HTML de la FIFA.")
            return
            
        df_fifa = tablas[0]
        
        # Analizamos las columnas disponibles para evitar roturas si la FIFA cambia los nombres
        columnas_texto = df_fifa.select_dtypes(include=['object']).columns
        columnas_num = df_fifa.select_dtypes(include=['number', 'float64', 'int64']).columns
        
        if len(columnas_texto) > 0 and len(columnas_num) > 0:
            df_limpio = pd.DataFrame()
            
            # La selección suele ser el primer string, y los puntos totales son el número más alto
            df_limpio['Seleccion'] = df_fifa[columnas_texto[0]]
            df_limpio['Puntaje_Elo'] = df_fifa[columnas_num[-1]]
            
            # Limpiamos artefactos visuales y normalizamos strings
            df_limpio['Seleccion'] = df_limpio['Seleccion'].astype(str).str.replace(r'[^\x00-\x7F]+', '', regex=True).str.strip()
            
            # Definimos la ruta destino para que reemplace el archivo Legacy
            ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ruta_destino = os.path.join(ROOT_DIR, 'data', 'rankings_elo.csv')
            os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
            
            df_limpio.to_csv(ruta_destino, index=False)
            
            print(f"\n🏆 ¡Ingesta completada con éxito! Dataset almacenado en: {ruta_destino}")
            print(df_limpio.head(15).to_string(index=False))
        else:
             print("❌ La tabla extraída no contiene el formato esperado (Texto/Números).")
             
    except Exception as e:
        print(f"❌ Error de ejecución en el conector FIFA: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    actualizar_ranking_fifa()