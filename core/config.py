import os
import logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 2. Configurar el Sistema de Logging Profesional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("Skynet")

# 3. Exportar todas las credenciales del proyecto
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 4. CAPA DE NORMALIZACIÓN: Diccionario Maestro de Traducción de Países
# Mapea el formato de ESPN (Inglés) al formato de tu base de datos Elo (Español)
TRADUCTOR_PAISES = {
    "Morocco": "Marruecos",
    "Haiti": "Haití",
    "Switzerland": "Suiza",
    "Canada": "Canadá",
    "Scotland": "Escocia",
    "Brazil": "Brasil",
    "Czechia": "República Checa",
    "Mexico": "México",
    "Bosnia-Herzegovina": "Bosnia y Herzegovina",
    "Qatar": "Catar",
    "South Africa": "Sudáfrica",
    "South Korea": "Corea del Sur",
    "Jordan": "Jordania",
    "Algeria": "Argelia",
    "Norway": "Noruega",
    "Senegal": "Senegal",
    "France": "Francia",
    "Iraq": "Irak",
    "Argentina": "Argentina",
    "Austria": "Austria"
}

def normalizar_nombre_pais(nombre_espn: str) -> str:
    """Toma el nombre de ESPN y devuelve el nombre estandarizado para el CSV de Elo."""
    return TRADUCTOR_PAISES.get(nombre_espn, nombre_espn)
# (Mantén lo que ya tienes arriba en config.py y añade esto al final)

# 5. DICCIONARIO VISUAL (Banderas)
BANDERAS = {
    "Morocco": "🇲🇦", "Haiti": "🇭🇹", "Switzerland": "🇨🇭", "Canada": "🇨🇦",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Brazil": "🇧🇷", "Czechia": "🇨🇿", "Mexico": "🇲🇽",
    "Bosnia-Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "South Africa": "🇿🇦", 
    "South Korea": "🇰🇷", "Jordan": "🇯🇴", "Algeria": "🇩🇿", "Norway": "🇳🇴", 
    "Senegal": "🇸🇳", "France": "🇫🇷", "Iraq": "🇮🇶", "Argentina": "🇦🇷", "Austria": "🇦🇹"
}