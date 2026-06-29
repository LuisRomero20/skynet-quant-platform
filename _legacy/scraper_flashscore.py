import os
import sys
import time
import numpy as np
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import logger

RUTA_FLASHSCORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'h2h_flashscore.csv')

class FlashscoreBot:
    def __init__(self):
        self.options = uc.ChromeOptions()
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        # Flashscore usa mucha publicidad, bloqueamos popups nativos de chrome
        self.options.add_argument("--disable-popup-blocking") 
        
    def raspar_forma_reciente(self):
        logger.info("🤖 Iniciando Robot Flashscore (Manejo de Ventanas Múltiples)...")
        driver = None
        try:
            driver = uc.Chrome(options=self.options, version_main=149)
            driver.get("https://www.flashscore.pe/")
            
            logger.info("⏳ Esperando carga de la página principal...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".event__match"))
            )
            
            # Obtener el ID de la ventana principal
            ventana_principal = driver.current_window_handle
            
            partidos_elementos = driver.find_elements(By.CSS_SELECTOR, ".event__match")
            logger.info(f"⚽ Se encontraron {len(partidos_elementos)} partidos programados en pantalla.")
            
            datos_h2h = []
            
            # Solo procesaremos los primeros 3 para no alargar el test, puedes quitar el [0:3] luego
            for partido in partidos_elementos[0:3]: 
                try:
                    local = partido.find_element(By.CSS_SELECTOR, ".event__participant--home").text
                    visitante = partido.find_element(By.CSS_SELECTOR, ".event__participant--away").text
                    logger.info(f"➡️ Analizando: {local} vs {visitante}")
                    
                    # Hacer clic en el partido abrirá una nueva pestaña de Flashscore
                    driver.execute_script("arguments[0].click();", partido)
                    time.sleep(3) # Esperar a que la pestaña abra
                    
                    # Cambiar el foco del robot a la nueva ventana
                    ventanas_abiertas = driver.window_handles
                    for ventana in ventanas_abiertas:
                        if ventana != ventana_principal:
                            driver.switch_to.window(ventana)
                            break
                    
                    # Ya en la ventana de detalle, buscar la pestaña H2H
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='#/h2h']"))
                    ).click()
                    
                    time.sleep(2) # Esperar renderizado del historial AJAX
                    
                    # Extraer filas de los últimos partidos del equipo local
                    filas_historial = driver.find_elements(By.CSS_SELECTOR, ".h2h__row")
                    
                    goles_anotados_recientes = 0
                    partidos_validos = 0
                    
                    # Leer solo los últimos 5
                    for fila in filas_historial[:5]: 
                        try:
                            # Flashscore guarda los resultados en spans dentro de la fila
                            resultado_texto = fila.find_element(By.CSS_SELECTOR, ".h2h__result").text
                            # Ejemplo de texto: "3\n1" -> Separamos por salto de línea
                            goles = resultado_texto.split('\n')
                            goles_anotados_recientes += int(goles[0]) + int(goles[1])
                            partidos_validos += 1
                        except:
                            pass
                            
                    promedio_reciente = round(goles_anotados_recientes / partidos_validos, 2) if partidos_validos > 0 else np.nan
                    
                    datos_h2h.append({
                        'Local': local,
                        'Visitante': visitante,
                        'Goles_Recientes_H2H': promedio_reciente
                    })
                    
                    # Cerrar pestaña de detalle y volver a la principal
                    driver.close()
                    driver.switch_to.window(ventana_principal)
                    
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo procesar un partido: {e}")
                    # Retorno de seguridad, cerramos extra tabs
                    while len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])
                        driver.close()
                    driver.switch_to.window(ventana_principal)

            # Guardar resultados
            df_flashscore = pd.DataFrame(datos_h2h)
            os.makedirs(os.path.dirname(RUTA_FLASHSCORE), exist_ok=True)
            df_flashscore.to_csv(RUTA_FLASHSCORE, index=False)
            
            logger.info(f"🏆 Robot Flashscore finalizó. Datos guardados en {RUTA_FLASHSCORE}")
            return True

        except Exception as e:
            logger.error(f"❌ Error crítico en Flashscore Bot: {e}")
            return False
            
        finally:
            if driver:
                try: driver.quit()
                except: pass

if __name__ == "__main__":
    FlashscoreBot().raspar_forma_reciente()