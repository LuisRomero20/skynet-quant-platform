import pandas as pd
import os
from datetime import datetime
from core.config import logger

# 1. Definir la ruta raíz del proyecto dinámicamente
DIRECTORIO_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_AUDITORIA = os.path.join(DIRECTORIO_RAIZ, 'data', 'processed', 'historial_predicciones.csv')

def registrar_prediccion(local: str, visitante: str, ganador_ia: str, probabilidad: float, nivel_confianza: str):
    """Guarda la predicción en el track record de forma absoluta, evitando duplicados."""
    os.makedirs(os.path.dirname(RUTA_AUDITORIA), exist_ok=True)

    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    partido = f"{local} vs {visitante}"

    nuevo_registro = pd.DataFrame([{
        'Fecha': fecha_hoy,
        'Partido': partido,
        'Prediccion_IA': ganador_ia,
        'Probabilidad': round(probabilidad, 2),
        'Confianza': nivel_confianza,
        'Resultado_Real': 'Pendiente',
        'Acierto': 'Pendiente'
    }])

    try:
        logger.info(f"Intentando guardar auditoría en: {RUTA_AUDITORIA}")

        if os.path.exists(RUTA_AUDITORIA):
            df_existente = pd.read_csv(RUTA_AUDITORIA)
            if not ((df_existente['Fecha'] == fecha_hoy) & (df_existente['Partido'] == partido)).any():
                df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                df_final.to_csv(RUTA_AUDITORIA, index=False)
                logger.info(f"✅ Registro auditado correctamente: {partido}")
        else:
            nuevo_registro.to_csv(RUTA_AUDITORIA, index=False)
            logger.info(f"✅ Base de datos creada. Primer registro: {partido}")
    except Exception as e:
        logger.error(f"❌ Error crítico al guardar en auditoría: {e}")


def actualizar_resultado_prediccion(local: str, visitante: str, resultado_real: str, fecha: str | None = None):
    """Actualiza un registro existente con el resultado real y si acertó la predicción."""
    if not os.path.exists(RUTA_AUDITORIA):
        return

    try:
        df = pd.read_csv(RUTA_AUDITORIA)
        partido = f"{local} vs {visitante}"
        mask = (df['Partido'] == partido)
        if fecha is not None:
            mask_fecha = mask & (df['Fecha'] == fecha)
            if mask_fecha.any():
                mask = mask_fecha
            else:
                mask = mask & (df['Acierto'].fillna('Pendiente') == 'Pendiente')

        if mask.any():
            idx = df.index[mask][-1]
            prediccion = str(df.loc[idx, 'Prediccion_IA']).strip()
            resultado_real_norm = str(resultado_real).strip()
            acierto = 'Sí' if prediccion == resultado_real_norm else 'No'
            df.loc[idx, 'Resultado_Real'] = resultado_real_norm
            df.loc[idx, 'Acierto'] = acierto
            df.to_csv(RUTA_AUDITORIA, index=False)
            logger.info(f"✅ Auditoría actualizada para {partido}: {resultado_real_norm}")
    except Exception as e:
        logger.error(f"❌ Error actualizando auditoría: {e}")