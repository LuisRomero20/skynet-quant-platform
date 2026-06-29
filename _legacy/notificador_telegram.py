import os
import sys
import pandas as pd
import joblib
import requests
import numpy as np
from scipy.stats import poisson
from datetime import datetime

# Conectar con las demás carpetas del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _legacy.scraper_partidos_hoy import obtener_partidos_de_internet
from scripts.termometro_social import analizar_moral_equipo
from core.config import logger, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, normalizar_nombre_pais
from core.auditoria import registrar_prediccion

# 🚀 IMPORTAMOS TU NUEVO MOTOR DE DATOS LOCAL (Adiós API de pago)
from scripts.scraper_historial_libre import calcular_h2h_local

def enviar_mensaje_telegram(mensaje: str) -> bool:
    """Envía el reporte a Telegram usando HTML robusto y un botón Inline."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Faltan credenciales en el archivo .env")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML", 
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "📊 Abrir Dashboard Termo-Quant", "url": "https://skynet-predictor.streamlit.app"}
            ]]
        }
    }
    
    try:
        respuesta = requests.post(url, json=payload, timeout=10)
        if respuesta.status_code != 200:
            logger.error(f"Telegram rechazó el envío. Detalle: {respuesta.text}")
        respuesta.raise_for_status()
        logger.info("⚡ Notificación Premium enviada a Telegram con éxito.")
        return True
    except Exception as e:
        logger.error(f"Fallo al enviar a Telegram: {e}")
        return False

if __name__ == "__main__":
    logger.info("Iniciando motor predictivo para Telegram V2 (Data Lake Local)...")
    
    ruta_elo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'rankings_elo.csv')
    ruta_ia = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ai', 'cerebro_mundial.pkl')

    try:
        df_elo = pd.read_csv(ruta_elo)
        dict_elo = dict(zip(df_elo['Seleccion'], df_elo['Puntaje_Elo']))
        modelo_ia = joblib.load(ruta_ia)
    except Exception as e:
        logger.error(f"Error cargando los modelos o datos: {e}")
        sys.exit(1)
    
    partidos_hoy_brutos = obtener_partidos_de_internet()
    partidos_hoy = list(dict.fromkeys(partidos_hoy_brutos))
    fecha_hoy = datetime.now().strftime('%d/%m/%Y')
    
    mensaje_reporte = f"🤖 <b>SKYNET ALGORITHMIC SEALS V2</b> 🤖\n📅 <i>Reporte de Inteligencia: {fecha_hoy}</i>\n\n"
    
    if not partidos_hoy:
        logger.warning("Radar limpio. No hay partidos programados para hoy.")
        mensaje_reporte += "📭 Radar limpio de operaciones para hoy."
    else:
        logger.info(f"Se encontraron {len(partidos_hoy)} partidos únicos. Iniciando inferencia ultrarrápida...")
        picks_premium = []
        picks_riesgo = []
        
        for local, visitante in partidos_hoy:
            local_es = normalizar_nombre_pais(local)
            visitante_es = normalizar_nombre_pais(visitante)
            
            elo_base_local = float(dict_elo.get(local_es, 1500))
            elo_base_visitante = float(dict_elo.get(visitante_es, 1500))
            
            nlp_local = analizar_moral_equipo(local, rival=visitante)
            nlp_visitante = analizar_moral_equipo(visitante, rival=local)
            
            # 🔥 CÁLCULO DE PATERNIDAD AL INSTANTE (Leyendo el CSV Local)
            puntaje_h2h = calcular_h2h_local(local, visitante)
            
            elo_final_local = elo_base_local + nlp_local['impacto']
            elo_final_visitante = elo_base_visitante + nlp_visitante['impacto']
            
            diferencia_elo = (elo_final_local - elo_final_visitante) + puntaje_h2h
            
            ventaja = (diferencia_elo / 100) * 0.25
            xg_local = max(0.1, 1.4 + ventaja)
            xg_visitante = max(0.1, 1.4 - ventaja)
            
            prob_l = [poisson.pmf(i, xg_local) for i in range(6)]
            prob_v = [poisson.pmf(i, xg_visitante) for i in range(6)]
            matriz = np.outer(prob_l, prob_v)
            
            p_gana_l = np.sum(np.tril(matriz, -1))
            p_gana_v = np.sum(np.triu(matriz, 1))
            
            datos_ia = pd.DataFrame([{
                'Elo_Local': elo_final_local, 
                'Elo_Visitante': elo_final_visitante, 
                'Diferencia_Elo': diferencia_elo
            }])
            pred_ia = modelo_ia.predict(datos_ia)[0]
            ganador_ia = local if pred_ia == '1' else visitante if pred_ia == '2' else "Empate"
            
            prob_max = max(p_gana_l, p_gana_v) * 100
            
            bloque_partido = f"⚔️ <b>{local} vs {visitante}</b>\n"
            bloque_partido += f"🧠 Proyección IA: Gana {ganador_ia}\n"
            bloque_partido += f"📊 Probabilidad de Éxito: <code>{prob_max:.1f}%</code> \n\n"
            
            if prob_max >= 70.0:
                nivel = "Premium"
                picks_premium.append(bloque_partido)
            else:
                nivel = "Alto Riesgo"
                picks_riesgo.append(bloque_partido)
                
            registrar_prediccion(local, visitante, ganador_ia, prob_max, nivel)
        
        if picks_premium:
            mensaje_reporte += "💎 <b>OPORTUNIDADES ALTA CONFIANZA (>70%)</b>\n"
            mensaje_reporte += "".join(picks_premium)
            
        if picks_riesgo:
            mensaje_reporte += "🎲 <b>OPERACIONES DE ALTO RIESGO</b>\n"
            mensaje_reporte += "".join(picks_riesgo)

    enviar_mensaje_telegram(mensaje_reporte)