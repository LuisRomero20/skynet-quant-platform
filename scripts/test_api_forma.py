import numpy as np

def testear_api_forma(equipo):
    print(f"🔄 Consultando API para los últimos 5 partidos de: {equipo}...")
    
    # ⚠️ En producción, aquí iría el código requests.get() hacia la API real.
    # Por ahora, simulamos la respuesta estructurada de una API (JSON)
    # para probar que nuestra lógica de extracción funcione.
    
    # Supongamos que la API nos devuelve esto para Colombia y Portugal
    datos_simulados_api = {
        "Colombia": {"goles_promedio": 1.8, "corners_promedio": 5.2, "tarjetas_promedio": 2.1},
        "Portugal": {"goles_promedio": 2.4, "corners_promedio": 6.8, "tarjetas_promedio": 1.5}
    }
    
    try:
        # Simulamos la latencia de la red
        import time
        time.sleep(1)
        
        if equipo in datos_simulados_api:
            stats = datos_simulados_api[equipo]
            print(f"✅ ¡API respondió! {equipo} -> Goles: {stats['goles_promedio']}, Córners: {stats['corners_promedio']}, Tarjetas: {stats['tarjetas_promedio']}")
            return stats
        else:
            print(f"⚠️ La API no tiene datos recientes para {equipo}.")
            return {"goles_promedio": np.nan, "corners_promedio": np.nan, "tarjetas_promedio": np.nan}
            
    except Exception as e:
        print(f"❌ Error en la API: {e}")
        return None

if __name__ == "__main__":
    testear_api_forma("Colombia")
    testear_api_forma("Portugal")