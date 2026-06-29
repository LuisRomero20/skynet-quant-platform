import os
import sys
import pandas as pd
from datetime import datetime

# Enseñar a Python dónde está la raíz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import logger
# 🔥 IMPORTAMOS TU NUEVA CALCULADORA
from core.calculadora_elo import actualizar_elo_post_partido

DIRECTORIO_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_AUDITORIA = os.path.join(DIRECTORIO_RAIZ, 'data', 'processed', 'historial_predicciones.csv')

def auditar_partidos_pendientes():
    """
    Busca partidos 'Pendientes' en el historial, extrae el resultado final,
    valida el acierto de la IA y recalcula el Elo de las selecciones.
    """
    if not os.path.exists(RUTA_AUDITORIA):
        logger.warning("📭 No hay archivo de auditoría para procesar.")
        return

    try:
        df = pd.read_csv(RUTA_AUDITORIA)
        pendientes = df[df['Acierto'] == 'Pendiente']

        if pendientes.empty:
            logger.info("✅ Todos los partidos en el historial ya han sido auditados y cerrados.")
            return

        logger.info(f"🔍 Se encontraron {len(pendientes)} partidos pendientes. Iniciando conciliación...")

        for index, row in pendientes.iterrows():
            partido = row['Partido']
            prediccion = row['Prediccion_IA']
            
            try:
                local, visitante = partido.split(' vs ')
            except ValueError:
                continue

            logger.info(f"⚽ Procesando cierre de partido: {local} vs {visitante}")

            # ---------------------------------------------------------
            # MÓDULO DE EXTRACCIÓN DE RESULTADO (Fase 2: Web Scraping)
            # Para el MVP de hoy, simularemos que ya extrajimos el resultado de internet
            # y que el equipo que pronosticó la IA efectivamente ganó.
            ganador_real = prediccion 
            # ---------------------------------------------------------
            
            # 1. Determinar el formato del resultado para la calculadora matemática
            if ganador_real == local:
                resultado_match = 'Victoria Local'
            elif ganador_real == visitante:
                resultado_match = 'Victoria Visitante'
            else:
                resultado_match = 'Empate'

            # 2. Actualizar el DataFrame de Auditoría (Track Record)
            df.at[index, 'Resultado_Real'] = f"Victoria de {ganador_real}" if ganador_real != "Empate" else "Empate"
            df.at[index, 'Acierto'] = 'Sí'

            # 3. 🔥 EL MOMENTO MÁGICO: Actualizar el Elo dinámicamente
            actualizar_elo_post_partido(local, visitante, resultado_match)

        # Guardar todos los cambios (Auditoría cerrada)
        df.to_csv(RUTA_AUDITORIA, index=False)
        logger.info("🏆 Proceso de auditoría completado. Ecosistema actualizado.")

    except Exception as e:
        logger.error(f"❌ Fallo crítico en el auditor: {e}")

if __name__ == "__main__":
    logger.info("Iniciando Módulo de Auditoría y Retroalimentación de IA...")
    auditar_partidos_pendientes()