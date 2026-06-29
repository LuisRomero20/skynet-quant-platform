import os
import sys
import time
import requests
from dotenv import load_dotenv

# Enseñar a Python dónde está la raíz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import logger

class APIManager:
    def __init__(self):
        """Inicializa la conexión cargando la llave secreta una sola vez."""
        load_dotenv()
        self.api_key = os.getenv("API_FOOTBALL_KEY")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": self.api_key
        }

    def hacer_peticion(self, endpoint: str, parametros: dict = None):
        """Método interno con escudo Anti-Rate Limit para cuentas gratuitas."""
        # 🛑 ESCUDO: Pausamos 6.1 segundos antes de disparar para nunca superar las 10 req/min
        time.sleep(6.1) 
        
        url = f"{self.base_url}/{endpoint}"
        try:
            respuesta = requests.get(url, headers=self.headers, params=parametros, timeout=10)
            datos = respuesta.json()
            
            if datos.get("errors"):
                logger.error(f"Alerta API: {datos['errors']}")
                return []
                
            return datos.get("response", [])
        except Exception as e:
            logger.error(f"Error de red crítico con API-Sports: {e}")
            return []

    def obtener_h2h(self, equipo_local: str, equipo_visitante: str) -> int:
        """
        Busca el historial directo entre dos equipos y devuelve un puntaje
        basado en sus enfrentamientos previos, usando bypass de plan gratuito.
        """
        if not self.api_key:
            logger.error("API_FOOTBALL_KEY faltante.")
            return 0

        # 1. Obtener IDs de ambos equipos
        datos_local = self.hacer_peticion("teams", {"name": equipo_local})
        datos_visitante = self.hacer_peticion("teams", {"name": equipo_visitante})
        
        if not datos_local or not datos_visitante:
            return 0
            
        id_local = datos_local[0]['team']['id']
        id_visitante = datos_visitante[0]['team']['id']
        
        # 2. Consultar Historial Directo (H2H)
        h2h_id = f"{id_local}-{id_visitante}"
        historial_completo = self.hacer_peticion("fixtures/headtohead", {"h2h": h2h_id})
        
        if not historial_completo:
            return 0
            
        terminados = [p for p in historial_completo if p['fixture']['status']['short'] in ['FT', 'AET', 'PEN']]
        ultimos_5 = terminados[-5:]
        
        puntaje_h2h = 0
        for partido in ultimos_5:
            if partido['teams']['home']['id'] == id_local and partido['goals']['home'] > partido['goals']['away']:
                puntaje_h2h += 30
            elif partido['teams']['away']['id'] == id_local and partido['goals']['away'] > partido['goals']['home']:
                puntaje_h2h += 30
            elif partido['goals']['home'] == partido['goals']['away']:
                puntaje_h2h += 5
            else:
                puntaje_h2h -= 20
                
        logger.info(f"⚔️ Historial H2H calculado para {equipo_local} vs {equipo_visitante}: {puntaje_h2h} pts")
        return puntaje_h2h

if __name__ == "__main__":
    api = APIManager()
    print("Iniciando auditoría de enfrentamiento directo...")
    puntaje = api.obtener_h2h("Brazil", "Argentina")
    print(f"Puntaje H2H: {puntaje}")