import os
import sys
import pandas as pd
import time
import numpy as np
import undetected_chromedriver as uc
from io import StringIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import logger

DIRECTORIO_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MERCADOS = os.path.join(DIRECTORIO_RAIZ, 'data', 'raw', 'mercados_secundarios.csv')

class ScraperMercadosCompleto:
    def __init__(self):
        self.options = uc.ChromeOptions()
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-popup-blocking")
        
    def extraer_todo(self) -> bool:
        logger.info("🚀 Iniciando Motor Macro FBref (Goles, Tarjetas y Córners)...")
        driver = None
        try:
            driver = uc.Chrome(options=self.options, version_main=149)
            fuentes = {
                "standard": "https://fbref.com/en/comps/1/stats/World-Cup-Stats",
                "shooting": "https://fbref.com/en/comps/1/shooting/World-Cup-Stats",
                "passing": "https://fbref.com/en/comps/1/passing_types/World-Cup-Stats"
            }
            datasets = {}
            
            for clave, url in fuentes.items():
                logger.info(f"📡 Raspando: {url}")
                driver.get(url)
                time.sleep(7)
                
                html = driver.page_source
                tablas = pd.read_html(StringIO(html))
                
                df_tabla = None
                for t in tablas:
                    if isinstance(t.columns, pd.MultiIndex):
                        t.columns = ['_'.join(col).strip() for col in t.columns]
                    else:
                        t.columns = [str(col).strip() for col in t.columns]
                        
                    col_squad = [c for c in t.columns if 'Squad' in c or 'squad' in c.lower()]
                    if col_squad:
                        t.rename(columns={col_squad[0]: 'Squad'}, inplace=True)
                        df_tabla = t
                        break
                
                if df_tabla is not None:
                    df_tabla = df_tabla.dropna(subset=['Squad'])
                    df_tabla = df_tabla[df_tabla['Squad'] != 'Squad']
                    datasets[clave] = df_tabla
                else:
                    logger.error(f"❌ Tabla no hallada en {clave}")
                    return False
            
            # --- CONSOLIDACIÓN ---
            df_std, df_sht, df_pas = datasets["standard"], datasets["shooting"], datasets["passing"]
            
            def buscar_col(df, key):
                for c in df.columns:
                    if key in c: return c
                return None

            col_mp, col_gls, col_crdy, col_ck = buscar_col(df_std, 'MP'), buscar_col(df_std, 'Gls'), buscar_col(df_std, 'CrdY'), buscar_col(df_pas, 'CK')
            
            # Si no existe la data, forzamos np.nan (Cero inventos)
            res = pd.DataFrame({
                'Seleccion': df_std['Squad'],
                'Partidos': pd.to_numeric(df_std[col_mp], errors='coerce') if col_mp else np.nan,
                'Goles_Totales': pd.to_numeric(df_std[col_gls], errors='coerce') if col_gls else np.nan,
                'Tarjetas_Totales': pd.to_numeric(df_std[col_crdy], errors='coerce') if col_crdy else np.nan,
            })
            
            res_pas = pd.DataFrame({
                'Seleccion': df_pas['Squad'],
                'Corners_Totales': pd.to_numeric(df_pas[col_ck], errors='coerce') if col_ck else np.nan
            })
            
            df_final = pd.merge(res, res_pas, on='Seleccion', how='inner')
            
            # Cálculos estrictos (Si un valor es NaN, el promedio será NaN)
            df_final['Promedio_Goles'] = round(df_final['Goles_Totales'] / df_final['Partidos'], 2)
            df_final['Promedio_Tarjetas'] = round(df_final['Tarjetas_Totales'] / df_final['Partidos'], 2)
            df_final['Promedio_Corners'] = round(df_final['Corners_Totales'] / df_final['Partidos'], 2)
            
            df_final = df_final[['Seleccion', 'Promedio_Goles', 'Promedio_Tarjetas', 'Promedio_Corners']]
            os.makedirs(os.path.dirname(RUTA_MERCADOS), exist_ok=True)
            df_final.to_csv(RUTA_MERCADOS, index=False)
            
            logger.info("🏆 DATA FBref ACTUALIZADA: Archivo consolidado guardado.")
            return True
        finally:
            if driver:
                try: driver.quit()
                except OSError: pass

if __name__ == "__main__":
    ScraperMercadosCompleto().extraer_todo()