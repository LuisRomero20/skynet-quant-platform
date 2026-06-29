import requests
from datetime import datetime

def obtener_partidos_de_internet():
    # El "Truco Nivel Dios": en lugar de raspar el HTML visual que cambia a cada rato, 
    # interceptamos el servidor de datos oculto de ESPN (es público y no pide llave).
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    print(f"🕷️ Infiltrándose en la tubería de datos de ESPN para buscar partidos del {hoy}...")
    
    try:
        # Hacemos la petición directa al servidor
        respuesta = requests.get(url)
        respuesta.raise_for_status()
        
        datos = respuesta.json()
        eventos = datos.get('events', [])
        
        partidos_encontrados = []
        
        for evento in eventos:
            # Navegamos por el JSON para extraer los equipos
            competidores = evento['competitions'][0]['competitors']
            
            # Extraemos los nombres
            equipo_1 = competidores[0]['team']['name']
            equipo_2 = competidores[1]['team']['name']
            
            # Nos aseguramos de mantener el orden correcto (Local vs Visitante)
            if competidores[0]['homeAway'] == 'home':
                local = equipo_1
                visitante = equipo_2
            else:
                local = equipo_2
                visitante = equipo_1
                
            partidos_encontrados.append((local, visitante))
            
        return partidos_encontrados

    except Exception as e:
        print(f"❌ Error al interceptar el servidor: {e}")
        return []

# Bloque de prueba
if __name__ == "__main__":
    partidos_de_hoy = obtener_partidos_de_internet()
    
    print("\n========================================================")
    if not partidos_de_hoy:
        print("📭 No se encontraron partidos programados para hoy en el servidor.")
    else:
        print(f"⚽ ¡ÉXITO TOTAL! La araña interceptó {len(partidos_de_hoy)} partidos en tiempo real:")
        for i, (local, visitante) in enumerate(partidos_de_hoy, 1):
            print(f"   {i}. {local} vs {visitante}")
    print("========================================================\n")