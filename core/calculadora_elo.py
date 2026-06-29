import os
import sys
import pandas as pd

# Enseñar a Python dónde está la raíz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import logger, normalizar_nombre_pais

# Rutas absolutas
DIRECTORIO_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_ELO_CSV = os.path.join(DIRECTORIO_RAIZ, 'data', 'raw', 'rankings_elo.csv')

def calcular_nuevo_elo(elo_local: float, elo_visitante: float, resultado: str, factor_k: int = 40) -> tuple:
    """
    Aplica la fórmula matemática oficial de Elo para actualizar los puntajes.
    """
    esperado_local = 1 / (1 + 10 ** ((elo_visitante - elo_local) / 400))
    esperado_visitante = 1 / (1 + 10 ** ((elo_local - elo_visitante) / 400))

    if resultado == 'Victoria Local':
        real_local, real_visitante = 1.0, 0.0
    elif resultado == 'Empate':
        real_local, real_visitante = 0.5, 0.5
    else: # Victoria Visitante
        real_local, real_visitante = 0.0, 1.0

    nuevo_elo_local = elo_local + factor_k * (real_local - esperado_local)
    nuevo_elo_visitante = elo_visitante + factor_k * (real_visitante - esperado_visitante)

    # 🔥 RECUPERAMOS LA PRECISIÓN: Dejamos 2 decimales
    return round(nuevo_elo_local, 2), round(nuevo_elo_visitante, 2)

def actualizar_elo_post_partido(equipo_local: str, equipo_visitante: str, resultado: str):
    """
    Lee el CSV de rankings, actualiza los puntos de los equipos involucrados y guarda.
    """
    if not os.path.exists(RUTA_ELO_CSV):
        logger.error("No se encontró el archivo de rankings Elo.")
        return

    try:
        df_elo = pd.read_csv(RUTA_ELO_CSV)
        
        # 🔥 EL PARCHE CRÍTICO: Forzar la columna a Float antes de inyectar decimales
        df_elo['Puntaje_Elo'] = df_elo['Puntaje_Elo'].astype(float)
        
        local_norm = normalizar_nombre_pais(equipo_local)
        visitante_norm = normalizar_nombre_pais(equipo_visitante)
        
        if local_norm not in df_elo['Seleccion'].values or visitante_norm not in df_elo['Seleccion'].values:
            logger.warning(f"No se pudieron actualizar los Elos: {local_norm} o {visitante_norm} no están en la base de datos.")
            return
            
        elo_actual_local = df_elo.loc[df_elo['Seleccion'] == local_norm, 'Puntaje_Elo'].values[0]
        elo_actual_visitante = df_elo.loc[df_elo['Seleccion'] == visitante_norm, 'Puntaje_Elo'].values[0]
        
        nuevo_local, nuevo_visitante = calcular_nuevo_elo(elo_actual_local, elo_actual_visitante, resultado)
        
        dif_local = nuevo_local - elo_actual_local
        dif_vis = nuevo_visitante - elo_actual_visitante
        signo_l = "+" if dif_local > 0 else ""
        signo_v = "+" if dif_vis > 0 else ""
        
        logger.info(f"📈 ACTUALIZACIÓN ELO [{resultado}]:")
        logger.info(f"   {local_norm}: {elo_actual_local:.2f} -> {nuevo_local:.2f} ({signo_l}{dif_local:.2f})")
        logger.info(f"   {visitante_norm}: {elo_actual_visitante:.2f} -> {nuevo_visitante:.2f} ({signo_v}{dif_vis:.2f})")
        
        df_elo.loc[df_elo['Seleccion'] == local_norm, 'Puntaje_Elo'] = nuevo_local
        df_elo.loc[df_elo['Seleccion'] == visitante_norm, 'Puntaje_Elo'] = nuevo_visitante
        
        df_elo.to_csv(RUTA_ELO_CSV, index=False)
        logger.info("💾 Base de datos Elo sobrescrita con los nuevos coeficientes decimales.")
        
    except Exception as e:
        logger.error(f"Error actualizando el Elo en disco: {e}")

if __name__ == "__main__":
    print("Prueba de fluctuación de Elo (Precisión Decimal)...")
    l, v = calcular_nuevo_elo(1500.0, 1800.0, 'Victoria Local')
    print(f"El equipo chico sube a: {l} (+{round(l-1500, 2)} pts)")
    print(f"El equipo grande baja a: {v} ({round(v-1800, 2)} pts)")