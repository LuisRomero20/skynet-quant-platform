import os
import sys
import requests
import pandas as pd
from datetime import datetime

# Enseñar a Python dónde está la raíz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import logger

# Configuración de rutas absolutas
DIRECTORIO_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_HISTORIAL_CSV = os.path.join(DIRECTORIO_RAIZ, 'data', 'raw', 'resultados_historicos.csv')

def descargar_master_dataset() -> bool:
    """
    ETAPA EXTRACT: Descarga el dataset maestro con la historia completa 
    del fútbol internacional (actualizado constantemente en servidores abiertos).
    """
    url_fuente = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    logger.info("📡 Conectando con el repositorio maestro de fútbol internacional...")
    
    try:
        os.makedirs(os.path.dirname(RUTA_HISTORIAL_CSV), exist_ok=True)
        respuesta = requests.get(url_fuente, timeout=15)
        respuesta.raise_for_status()
        
        with open(RUTA_HISTORIAL_CSV, 'w', encoding='utf-8') as f:
            f.write(respuesta.text)
            
        logger.info("💾 LOAD: Dataset histórico global guardado en data/raw/resultados_historicos.csv")
        return True
    except Exception as e:
        logger.error(f"❌ Error descargando el dataset maestro: {e}")
        return False

def calcular_h2h_local(equipo_local: str, equipo_visitante: str) -> int:
    """
    ETAPA TRANSFORM: Consulta el archivo local y calcula la paternidad histórica (H2H)
    de los últimos 5 enfrentamientos directos entre ambos países.
    """
    if not os.path.exists(RUTA_HISTORIAL_CSV):
        logger.warning("⚠️ No existe el dataset maestro local. Descargándolo ahora...")
        descargar_master_dataset()

    try:
        df = pd.read_csv(RUTA_HISTORIAL_CSV)
        
        # Filtro bivalente: Partido donde A vs B o B vs A
        filtro_choques = (
            ((df['home_team'] == equipo_local) & (df['away_team'] == equipo_visitante)) |
            ((df['home_team'] == equipo_visitante) & (df['away_team'] == equipo_local))
        )
        
        historial_choques = df[filtro_choques].copy()
        
        if historial_choques.empty:
            logger.info(f"⚪ Sin enfrentamientos previos registrados entre {equipo_local} y {equipo_visitante}")
            return 0
            
        # Convertir fecha para ordenar cronológicamente los más recientes
        historial_choques['date'] = pd.to_datetime(historial_choques['date'])
        historial_choques = historial_choques.sort_values(by='date', ascending=True)
        
        # Cortar los últimos 5 enfrentamientos
        ultimos_5 = historial_choques.tail(5)
        
        puntaje_h2h = 0
        for _, partido in ultimos_5.iterrows():
            goles_home = partido['home_score']
            goles_away = partido['away_score']
            
            # Verificar quién es el dueño de la casa en este registro histórico
            if partido['home_team'] == equipo_local:
                if goles_home > goles_away: puntaje_h2h += 30   # Ganó nuestro local actual
                elif goles_home == goles_away: puntaje_h2h += 5 # Empate
                else: puntaje_h2h -= 20                         # Perdió nuestro local actual
            else:
                if goles_away > goles_home: puntaje_h2h += 30   # Ganó nuestro local jugando como visitante atrás
                elif goles_home == goles_away: puntaje_h2h += 5 
                else: puntaje_h2h -= 20
                
        logger.info(f"⚔️ [H2H LOCAL] {equipo_local} vs {equipo_visitante}: {puntaje_h2h} pts basados en {len(ultimos_5)} partidos.")
        return puntaje_h2h

    except Exception as e:
        logger.error(f"Error procesando H2H local: {e}")
        return 0

if __name__ == "__main__":
    print("🧪 Probando el Motor de Datos Libre de Skynet...")
    # Forzar descarga inicial para pruebas
    descargar_master_dataset()
    
    # Prueba de cálculo inmediato en local sin APIs
    print("\n🔍 Analizando un clásico del fútbol mundial en base de datos local:")
    puntos = calcular_h2h_local("Brazil", "Argentina")
    print(f"Resultado del cálculo de paternidad: {puntos} puntos.")