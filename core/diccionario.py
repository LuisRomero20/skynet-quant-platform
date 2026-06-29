# core/diccionario.py

MAPEO_PAISES = {
    # Formatos de FootyStats y GitHub (Inglés) -> Español FIFA Estandarizado
    "USA": "EE. UU.",
    "United States": "EE. UU.",
    "DR Congo": "RD Congo",
    "Congo DR": "RD Congo",
    "England": "Inglaterra",
    "Spain": "España",
    "Germany": "Alemania",
    "France": "Francia",
    "Japan": "Japón",
    "Brazil": "Brasil",
    "South Korea": "República de Corea",
    "Korea Republic": "República de Corea",
    "North Korea": "RPD de Corea",
    "Korea DPR": "RPD de Corea",
    "Ivory Coast": "Costa de Marfil",
    "Canada": "Canadá",
    "South Africa": "Sudáfrica",
    "Czech Republic": "República Checa",
    "Curaçao": "Curazao",
    "Curaao": "Curazao",
    "Cote d'Ivoire": "Costa de Marfil",
    "Morocco": "Marruecos",
    "Netherlands": "Países Bajos",
    "Saudi Arabia": "Arabia Saudí",
    "Cape Verde Islands": "Islas de Cabo Verde",
    "Cape Verde": "Islas de Cabo Verde",
    "New Zealand": "Nueva Zelanda",
    "Belgium": "Bélgica",
    "Croatia": "Croacia",
    "Iran": "RI de Irán",
    "IR Iran": "RI de Irán",
    "China PR": "RP China",
    "China": "RP China",
    
    # Países que ya están bien pero los aseguramos
    "Argentina": "Argentina",
    "Colombia": "Colombia",
    "Portugal": "Portugal",
    "Panama": "Panamá",
    "Peru": "Perú",
    "Uruguay": "Uruguay"
}

def normalizar_pais(nombre_crudo):
    """
    Recibe un nombre de cualquier fuente (Git, API, FootyStats, FIFA)
    y devuelve el nombre oficial en español.
    """
    nombre_limpio = str(nombre_crudo).strip()
    return MAPEO_PAISES.get(nombre_limpio, nombre_limpio)