import numpy as np
from scipy.stats import poisson

def predecir_partido_avanzado(xg_local, xg_visitante, x_corners_total, x_tarjetas_total, equipo_local, equipo_visitante):
    print(f"\n========================================================")
    print(f"🧠 MOTOR PREDICTIVO NIVEL DIOS: {equipo_local} vs {equipo_visitante}")
    print(f"========================================================")
    
    # ---------------------------------------------------------
    # 1. MATEMÁTICA DE GOLES (1X2, Over/Under, BTTS)
    # ---------------------------------------------------------
    max_goles = 7
    prob_local = [poisson.pmf(i, xg_local) for i in range(max_goles)]
    prob_visitante = [poisson.pmf(i, xg_visitante) for i in range(max_goles)]
    matriz_marcadores = np.outer(prob_local, prob_visitante)
    
    prob_empate = np.sum(np.diag(matriz_marcadores))
    prob_gana_local = np.sum(np.tril(matriz_marcadores, -1))
    prob_gana_visitante = np.sum(np.triu(matriz_marcadores, 1))
    
    # Over / Under 2.5 Goles
    prob_under_25 = sum(matriz_marcadores[i, j] for i in range(max_goles) for j in range(max_goles) if i + j < 2.5)
    prob_over_25 = 1 - prob_under_25
    
    # Ambos Anotan (BTTS)
    prob_btts_no = np.sum(matriz_marcadores[0, :]) + np.sum(matriz_marcadores[:, 0]) - matriz_marcadores[0, 0]
    prob_btts_si = 1 - prob_btts_no

    idx_max = np.unravel_index(np.argmax(matriz_marcadores), matriz_marcadores.shape)
    marcador_probable = f"{equipo_local} {idx_max[0]} - {idx_max[1]} {equipo_visitante}"

    # ---------------------------------------------------------
    # 2. MATEMÁTICA DE CÓRNERES (Over/Under 8.5 y 9.5)
    # ---------------------------------------------------------
    # Función de distribución acumulada (CDF) para saber probabilidad de que haya X o menos.
    prob_under_8_5_corners = poisson.cdf(8, x_corners_total)
    prob_over_8_5_corners = 1 - prob_under_8_5_corners
    prob_over_9_5_corners = 1 - poisson.cdf(9, x_corners_total)

    # ---------------------------------------------------------
    # 3. MATEMÁTICA DE TARJETAS (Over/Under 3.5 y 4.5)
    # ---------------------------------------------------------
    prob_under_3_5_tarjetas = poisson.cdf(3, x_tarjetas_total)
    prob_over_3_5_tarjetas = 1 - prob_under_3_5_tarjetas
    prob_over_4_5_tarjetas = 1 - poisson.cdf(4, x_tarjetas_total)

    # ---------------------------------------------------------
    # 4. REPORTE PARA EL APOSTADOR PROFESIONAL
    # ---------------------------------------------------------
    print("\n⚽ MERCADOS PRINCIPALES (GOLES)")
    print("-" * 35)
    print(f"➤ Gana {equipo_local}:   {prob_gana_local*100:05.1f}% | Cuota Real: {(1/prob_gana_local):.2f}")
    print(f"➤ Empate:           {prob_empate*100:05.1f}% | Cuota Real: {(1/prob_empate):.2f}")
    print(f"➤ Gana {equipo_visitante}:   {prob_gana_visitante*100:05.1f}% | Cuota Real: {(1/prob_gana_visitante):.2f}")
    print(f"➤ Over 2.5 Goles:   {prob_over_25*100:05.1f}% | Cuota Real: {(1/prob_over_25):.2f}")
    print(f"➤ Ambos Anotan:     {prob_btts_si*100:05.1f}% | Cuota Real: {(1/prob_btts_si):.2f}")
    print(f"🔮 Marcador Exacto: {marcador_probable} ({matriz_marcadores[idx_max]*100:.1f}%)")

    print("\n🚩 MERCADOS SECUNDARIOS (CÓRNERES Y TARJETAS)")
    print("-" * 35)
    print(f"➤ Más de 8.5 Córneres: {prob_over_8_5_corners*100:05.1f}% | Cuota Real: {(1/prob_over_8_5_corners):.2f}")
    print(f"➤ Más de 9.5 Córneres: {prob_over_9_5_corners*100:05.1f}% | Cuota Real: {(1/prob_over_9_5_corners):.2f}")
    print(f"➤ Más de 3.5 Tarjetas: {prob_over_3_5_tarjetas*100:05.1f}% | Cuota Real: {(1/prob_over_3_5_tarjetas):.2f}")
    print(f"➤ Más de 4.5 Tarjetas: {prob_over_4_5_tarjetas*100:05.1f}% | Cuota Real: {(1/prob_over_4_5_tarjetas):.2f}")

    # ---------------------------------------------------------
    # 5. EL BOT RECOMIENDA (Busca probabilidades mayores al 55%)
    # ---------------------------------------------------------
    print("\n🔥 APUESTAS RECOMENDADAS POR LA IA:")
    print("-" * 35)
    recomendaciones = []
    if prob_gana_local > 0.55: recomendaciones.append(f"Victoria Fija: {equipo_local}")
    if prob_gana_visitante > 0.55: recomendaciones.append(f"Victoria Fija: {equipo_visitante}")
    if prob_over_25 > 0.55: recomendaciones.append("Alta probabilidad de goles (Over 2.5)")
    if prob_under_25 > 0.60: recomendaciones.append("Partido muy cerrado (Under 2.5 Goles)")
    if prob_over_8_5_corners > 0.65: recomendaciones.append("Apuesta segura a Más de 8.5 Córneres")
    if prob_over_3_5_tarjetas > 0.65: recomendaciones.append("Partido violento/friccionado (Over 3.5 Tarjetas)")
    
    if not recomendaciones:
        print("⚠️ Partido inestable. Evitar apostar fuertes sumas (No Bet).")
    else:
        for r in recomendaciones:
            print(f"✅ {r}")
    print("========================================================\n")


if __name__ == "__main__":
    # Prueba del modelo con datos alimentados
    # Simulamos un Brasil (xG: 2.2) vs México (xG: 0.9)
    # Promedio histórico de córneres combinados: 9.8 / Promedio de tarjetas: 4.2
    predecir_partido_avanzado(xg_local=2.2, xg_visitante=0.9, 
                              x_corners_total=9.8, x_tarjetas_total=4.2, 
                              equipo_local="Brasil", equipo_visitante="México")