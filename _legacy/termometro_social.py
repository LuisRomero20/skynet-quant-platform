import requests
from bs4 import BeautifulSoup
import urllib.parse
import unicodedata

def limpiar_texto(texto):
    """Elimina tildes y pasa todo a minúsculas para encontrar la raíz de las palabras."""
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    return texto.lower()

traductor_paises = {
    "Belgium": "Bélgica", "Iran": "Irán", "Japan": "Japón", "Spain": "España",
    "Saudi Arabia": "Arabia Saudita", "New Zealand": "Nueva Zelanda", "Egypt": "Egipto",
    "Tunisia": "Túnez", "Uruguay": "Uruguay", "Cape Verde": "Cabo Verde"
}

def analizar_moral_equipo(equipo, rival=None):
    from core.config import normalizar_nombre_pais
    equipo_es = normalizar_nombre_pais(equipo)
    
    # Truco de Data Engineer: Excluir el nombre del rival de la búsqueda para evitar noticias duplicadas
    if rival:
        rival_es = normalizar_nombre_pais(rival)
        query = urllib.parse.quote(f'"{equipo_es}" futbol -"{rival_es}"')
    else:
        query = urllib.parse.quote(f'"{equipo_es}" futbol')
        
    url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=PE&ceid=PE:es-419"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    palabras_negativas = ['lesion', 'baja', 'duda', 'crisis', 'escandalo', 'tension', 'pierde', 'alarma', 'fuera', 'desgarro', 'pelea', 'rompio', 'fractura', 'descartado']
    palabras_positivas = ['recupera', 'listo', 'goleada', 'invicto', 'confianza', 'figura', 'estrella', 'motivacion', 'regresa', 'poder', 'favorito']
    
    impacto_elo = 0
    evidencias = []
    
    try:
        respuesta = requests.get(url, headers=headers, timeout=10)
        respuesta.raise_for_status()
        sopa = BeautifulSoup(respuesta.content, 'xml')
        items = sopa.find_all('title')
        
        for item in items[1:16]: 
            titular_original = item.text
            titular_limpio = limpiar_texto(titular_original)
            encontrado = False
            
            for p in palabras_negativas:
                if p in titular_limpio:
                    impacto_elo -= 15
                    # Formateo en viñetas HTML para Streamlit
                    evidencias.append(f"<li>⚠️ <b>Alarma ({p}):</b> {titular_original.split(' - ')[0]}</li>")
                    encontrado = True
                    break
            
            if not encontrado:
                for p in palabras_positivas:
                    if p in titular_limpio:
                        impacto_elo += 10
                        evidencias.append(f"<li>🔥 <b>Impulso ({p}):</b> {titular_original.split(' - ')[0]}</li>")
                        break
                        
        return {"impacto": impacto_elo, "evidencias": evidencias[:4]}
        
    except Exception as e:
        print(f"❌ Error NLP al leer noticias de {equipo}: {e}")
        return {"impacto": 0, "evidencias": []}