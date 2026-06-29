import sys
import os
import requests
import pandas as pd
import time
from datetime import datetime

# Conectar con la base de datos local
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from core.database import SessionLocal, Partido, EstadisticaEquipo

# ==========================================
# CONFIGURACIÓN API-FOOTBALL
# ==========================================
API_KEY = "5ce59a4f9b274ae419b346e75e0fcf5f"
HEADERS = {
    "x-apisports-key": API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}
BASE_URL = "https://v3.football.api-sports.io"

def obtener_equipos_hoy_git():
    """Lee el CSV de GitHub y devuelve los partidos que juegan en la fecha actual"""
    print("🔄 Consultando Git para obtener los equipos que juegan hoy...")
    url_git = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    try:
        df = pd.read_csv(url_git)
        hoy = datetime.now().strftime("%Y-%m-%d")
        partidos_hoy = df[df['date'] == hoy]
        
        equipos = set()
        for _, row in partidos_hoy.iterrows():
            equipos.add(row['home_team'])
            equipos.add(row['away_team'])
            
        print(f"✅ Se encontraron {len(equipos)} equipos jugando hoy.")
        return list(equipos)
    except Exception as e:
        print(f"❌ Error leyendo Git: {e}")
        return []

def buscar_partidos_historicos_por_nombre(nombre_equipo):
    """
    Busca partidos históricos directamente por nombre de equipo usando el endpoint de búsqueda.
    Esto evita el problema de IDs no encontrados.
    """
    print(f"\n🔍 Buscando historial para: {nombre_equipo}")
    
    # Mapeo manual de contingencia para nombres problemáticos conocidos entre Git y API-Sports
    mapeo_nombres = {
        "DR Congo": "Congo DR",
        "Cape Verde Islands": "Cape Verde",
        "South Africa": "South Africa",
        "South Korea": "Korea Republic",
        "North Korea": "Korea DPR",
        "USA": "USA",
        "United States": "USA"
    }
    
    nombre_busqueda = mapeo_nombres.get(nombre_equipo, nombre_equipo)
    
    try:
        # Buscamos el ID del equipo primero, pero con el nombre mapeado
        res_team = requests.get(f"{BASE_URL}/teams?search={nombre_busqueda}", headers=HEADERS).json()
        
        if not res_team or not res_team.get("response"):
             print(f"  ⚠️ No se encontró el equipo '{nombre_busqueda}' en la API. Saltando...")
             return []
             
        team_id = res_team["response"][0]["team"]["id"]
        print(f"  ✓ ID de API encontrado para '{nombre_busqueda}': {team_id}")
        
        # Buscamos los últimos 3 partidos de ese equipo
        # Usamos el parámetro season 2026 o simplemente last=3
        res_fixtures = requests.get(f"{BASE_URL}/fixtures?team={team_id}&last=3&status=FT", headers=HEADERS).json()
        
        if res_fixtures and res_fixtures.get("response"):
             return [f["fixture"]["id"] for f in res_fixtures["response"]]
             
    except Exception as e:
        print(f"  ❌ Error buscando datos para {nombre_busqueda}: {e}")
        
    return []

def ingerir_fixture_completo(fixture_id):
    """Descarga el partido y sus estadísticas en una transacción atómica"""
    db = SessionLocal()
    try:
        # Verificar si ya existe
        if db.query(Partido).filter(Partido.api_id == fixture_id).first():
            return True

        # 1. Obtener Macro (Partido)
        res_partido = requests.get(f"{BASE_URL}/fixtures?id={fixture_id}", headers=HEADERS).json()
        if not res_partido or not res_partido.get("response"): 
            return False
        
        p_data = res_partido["response"][0]
        nuevo_partido = Partido(
            api_id=fixture_id,
            fecha=datetime.fromisoformat(p_data["fixture"]["date"].replace("Z", "+00:00")),
            torneo=p_data["league"]["name"],
            equipo_local=p_data["teams"]["home"]["name"],
            equipo_visitante=p_data["teams"]["away"]["name"],
            goles_local=p_data["goals"]["home"],
            goles_visitante=p_data["goals"]["away"],
            estado=p_data["fixture"]["status"]["short"]
        )
        
        db.add(nuevo_partido)
        db.flush() 

        # 2. Obtener Micro (Estadísticas)
        res_stats = requests.get(f"{BASE_URL}/fixtures/statistics?fixture={fixture_id}", headers=HEADERS).json()
        
        tiene_stats = False
        if res_stats and res_stats.get("response"):
            tiene_stats = True
            for t_stats in res_stats["response"]:
                nombre = t_stats["team"]["name"]
                metricas = {item["type"]: item["value"] for item in t_stats["statistics"]}
                
                def c_stat(val, is_float=False):
                    if val is None: return None
                    if isinstance(val, str) and "%" in val: return float(val.replace("%", ""))
                    return float(val) if is_float else int(val)

                stat_db = EstadisticaEquipo(
                    partido_id=nuevo_partido.id,
                    equipo=nombre,
                    corners=c_stat(metricas.get("Corner Kicks")),
                    tarjetas_amarillas=c_stat(metricas.get("Yellow Cards")),
                    tarjetas_rojas=c_stat(metricas.get("Red Cards")),
                    tiros_al_arco=c_stat(metricas.get("Shots on Goal")),
                    posesion_porcentaje=c_stat(metricas.get("Ball Possession"), True)
                )
                db.add(stat_db)

        # 🔥 AHORA SÍ: Confirmamos la transacción
        db.commit()
        
        if tiene_stats:
            print(f"  ✅ Guardado COMPLETO: {nuevo_partido.equipo_local} vs {nuevo_partido.equipo_visitante}")
        else:
            print(f"  ⚠️ Guardado SOLO RESULTADO (Sin Stats): {nuevo_partido.equipo_local} vs {nuevo_partido.equipo_visitante}")
            
    except Exception as e:
        db.rollback() 
        print(f"  ❌ Error ingestando fixture {fixture_id}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 INICIANDO PIPELINE DE BACKFILL DINÁMICO (V3 - Búsqueda Optimizada)...")
    
    equipos_hoy = obtener_equipos_hoy_git()
    
    if not equipos_hoy:
        print("🛑 No hay equipos para procesar hoy.")
        sys.exit()

    for equipo in equipos_hoy:
        fixture_ids = buscar_partidos_historicos_por_nombre(equipo)
        
        if fixture_ids:
             print(f"  ✓ Encontrados {len(fixture_ids)} partidos históricos. Procesando...")
             for fixture_id in fixture_ids:
                 ingerir_fixture_completo(fixture_id)
                 time.sleep(1.5) # Respetar Rate Limit
        
        time.sleep(1) # Pausa entre equipos

    print("\n🏆 PROCESO ETL FINALIZADO. REVISA PGADMIN.")