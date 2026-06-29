import sys
import os
import requests
from datetime import datetime

# Conectar con nuestra base de datos local
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from core.database import SessionLocal, Partido, EstadisticaEquipo

# ==========================================
# CONFIGURACIÓN API-FOOTBALL
# ==========================================
# Reemplaza "tu_api_key_aqui" con tu llave real de API-Sports
API_KEY = "5ce59a4f9b274ae419b346e75e0fcf5f" 
HEADERS = {
    "x-apisports-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}
BASE_URL = "https://v3.football.api-sports.io"

def ingerir_partido_historico(fixture_id):
    """Extrae un partido de la API y lo guarda en PostgreSQL"""
    print(f"🔄 Solicitando datos del Fixture ID {fixture_id} a la API...")
    
    if API_KEY == "tu_api_key_aqui":
         print("❌ DETENIDO: Debes colocar tu API Key real en el script.")
         return False

    try:
        # Petición al endpoint de fixtures
        response = requests.get(f"{BASE_URL}/fixtures?id={fixture_id}", headers=HEADERS)
        data = response.json()
        
        if not data.get("response"):
            print("📭 La API no devolvió datos para este ID.")
            return False
            
        partido_api = data["response"][0]
        
        # 1. Preparar datos Macro (Tabla: partidos)
        local_nombre = partido_api["teams"]["home"]["name"]
        visitante_nombre = partido_api["teams"]["away"]["name"]
        goles_l = partido_api["goals"]["home"]
        goles_v = partido_api["goals"]["away"]
        
        print(f"⚽ Procesando: {local_nombre} vs {visitante_nombre}")
        
        # Abrimos sesión con PostgreSQL
        db = SessionLocal()
        
        # Verificar si el partido ya existe para no duplicar
        existe = db.query(Partido).filter(Partido.api_id == fixture_id).first()
        if existe:
            print("⚠️ El partido ya existe en la Base de Datos. Saltando...")
            db.close()
            return True
            
        nuevo_partido = Partido(
            api_id=fixture_id,
            fecha=datetime.fromisoformat(partido_api["fixture"]["date"].replace("Z", "+00:00")),
            torneo=partido_api["league"]["name"],
            equipo_local=local_nombre,
            equipo_visitante=visitante_nombre,
            goles_local=goles_l,
            goles_visitante=goles_v,
            estado=partido_api["fixture"]["status"]["short"]
        )
        
        db.add(nuevo_partido)
        db.commit() # Guardamos para generar el ID interno
        db.refresh(nuevo_partido)
        
        # 2. Preparar datos Micro (Tabla: estadisticas_equipos)
        # Endpoint secundario para estadísticas detalladas (Córners, Tarjetas)
        stats_response = requests.get(f"{BASE_URL}/fixtures/statistics?fixture={fixture_id}", headers=HEADERS)
        stats_data = stats_response.json()
        
        if stats_data.get("response"):
            for team_stats in stats_data["response"]:
                nombre_equipo = team_stats["team"]["name"]
                metricas = {item["type"]: item["value"] for item in team_stats["statistics"]}
                
                # Mapeo seguro de tipos (limpiando strings como "55%")
                def clean_stat(val, is_float=False):
                    if val is None: return None
                    if isinstance(val, str) and "%" in val: return float(val.replace("%", ""))
                    return float(val) if is_float else int(val)

                stats_db = EstadisticaEquipo(
                    partido_id=nuevo_partido.id,
                    equipo=nombre_equipo,
                    corners=clean_stat(metricas.get("Corner Kicks")),
                    tarjetas_amarillas=clean_stat(metricas.get("Yellow Cards")),
                    tarjetas_rojas=clean_stat(metricas.get("Red Cards")),
                    tiros_al_arco=clean_stat(metricas.get("Shots on Goal")),
                    posesion_porcentaje=clean_stat(metricas.get("Ball Possession"), True)
                )
                db.add(stats_db)
            
            db.commit()
            print(f"✅ Estadísticas granulares guardadas exitosamente para {local_nombre} y {visitante_nombre}.")
        else:
            print("⚠️ Partido guardado, pero la API no tenía estadísticas granulares para este fixture.")
            
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error crítico en el Pipeline ETL: {e}")
        return False

import time

if __name__ == "__main__":
    # IDs reales de la fase final del Mundial Qatar 2022
    partidos_top = [
        855736, # Argentina vs Francia (Final)
        855735, # Croacia vs Marruecos (3er Puesto)
        855734  # Francia vs Marruecos (Semifinal)
    ]
    
    print("🚀 INICIANDO INGESTA MASIVA ETL...")
    for id_partido in partidos_top:
        ingerir_partido_historico(id_partido)
        # Pausa de 2 segundos para no saturar la API (Rate Limiting)
        time.sleep(2) 
        
    print("🏆 PROCESO ETL FINALIZADO CON ÉXITO.")