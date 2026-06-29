import os
import sys
import pandas as pd
import joblib

# Conectar con las herramientas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _legacy.scraper_partidos_hoy import obtener_partidos_de_internet
from scripts.termometro_social import analizar_moral_equipo
from models.modelo_poisson import predecir_partido_avanzado
from core.config import logger  # <--- Importamos nuestro sistema profesional

logger.info("INICIANDO SKYNET V3: IA + SENTIMIENTO + POISSON")

def ejecutar_escanner():
    # 1. Cargar Bases de Datos
    ruta_elo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'rankings_elo.csv')
    ruta_ia = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ai', 'cerebro_mundial.pkl')
    
    try:
        df_elo = pd.read_csv(ruta_elo)
        dict_elo = dict(zip(df_elo['Seleccion'], df_elo['Puntaje_Elo']))
        modelo_ia = joblib.load(ruta_ia)
        logger.info("Bases de datos Elo y Cerebro IA (Random Forest) cargados con éxito.")
    except Exception as e:
        logger.error(f"Fallo crítico al cargar los datos base: {e}")
        sys.exit(1)

    # 2. Obtener Partidos
    partidos_hoy = obtener_partidos_de_internet()

    if not partidos_hoy:
        logger.warning("El radar está vacío. No hay partidos programados para hoy.")
        return

    logger.info(f"Procesando análisis integral de {len(partidos_hoy)} encuentros...")

    # 3. Analizar partido a partido
    for local, visitante in partidos_hoy:
        logger.info(f"--- PREPARANDO PARTIDO: {local} vs {visitante} ---")
        
        elo_base_local = float(dict_elo.get(local, 1500))
        elo_base_visitante = float(dict_elo.get(visitante, 1500))
        
        nlp_local = analizar_moral_equipo(local)
        nlp_visitante = analizar_moral_equipo(visitante)
        
        elo_final_local = elo_base_local + nlp_local['impacto']
        elo_final_visitante = elo_base_visitante + nlp_visitante['impacto']
        diferencia_elo = elo_final_local - elo_final_visitante
        
        # Inteligencia Artificial Pura
        datos_para_ia = pd.DataFrame([{'Elo_Local': elo_final_local, 'Elo_Visitante': elo_final_visitante, 'Diferencia_Elo': diferencia_elo}])
        prediccion_ia = modelo_ia.predict(datos_para_ia)[0]
        
        ganador_ia = local if prediccion_ia == '1' else visitante if prediccion_ia == '2' else "Empate"
        logger.info(f"Veredicto IA (Random Forest): Predice resultado a favor de {ganador_ia}")

        # Matemática Estadística (Poisson)
        ventaja = (diferencia_elo / 100) * 0.25
        xg_local = max(0.1, 1.4 + ventaja)
        xg_visitante = max(0.1, 1.4 - ventaja)
        x_corners_total = 9.2 + (abs(diferencia_elo) / 200)
        
        if abs(diferencia_elo) < 100: x_tarjetas_total = 4.8
        elif abs(diferencia_elo) > 300: x_tarjetas_total = 2.8
        else: x_tarjetas_total = 3.8

        # Imprimir el reporte visual (Poisson mantendrá sus prints para formateo visual en consola)
        predecir_partido_avanzado(
            xg_local=xg_local, 
            xg_visitante=xg_visitante, 
            x_corners_total=x_corners_total, 
            x_tarjetas_total=x_tarjetas_total, 
            equipo_local=local, 
            equipo_visitante=visitante
        )

if __name__ == "__main__":
    ejecutar_escanner()
    logger.info("Escaneo finalizado.")