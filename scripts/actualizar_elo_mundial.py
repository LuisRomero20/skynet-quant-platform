"""
Recalcula los rankings ELO a partir de:
  - data/rankings_elo_pretorneo.csv  (base inmutable, se crea en el primer run)
  - data/international-world-cup-matches-2026-to-2026-stats.csv  (partidos completados)

Guarda el resultado en data/rankings_elo.csv.
Idempotente: puede ejecutarse múltiples veces sin acumular errores.
"""

import os
import sys
import shutil
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from core.diccionario import normalizar_pais

RUTA_ELO         = os.path.join(ROOT_DIR, 'data', 'rankings_elo.csv')
RUTA_ELO_BASE    = os.path.join(ROOT_DIR, 'data', 'rankings_elo_pretorneo.csv')
RUTA_PARTIDOS    = os.path.join(ROOT_DIR, 'data', 'international-world-cup-matches-2026-to-2026-stats.csv')

K_MUNDIAL = 60   # Factor K oficial FIFA para partidos de Copa del Mundo


def _elo_esperado(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def _aplicar_resultado(elo_dict: dict, team_local: str, team_visita: str,
                       goles_local: int, goles_visita: int) -> None:
    """Actualiza elo_dict in-place aplicando un resultado."""
    local_key   = normalizar_pais(team_local)
    visita_key  = normalizar_pais(team_visita)

    elo_l = elo_dict.get(local_key)
    elo_v = elo_dict.get(visita_key)

    if elo_l is None or elo_v is None:
        missing = []
        if elo_l is None: missing.append(f"'{team_local}' -> '{local_key}'")
        if elo_v is None: missing.append(f"'{team_visita}' -> '{visita_key}'")
        print(f"  ⚠️  Sin ELO para: {', '.join(missing)}  — partido omitido")
        return

    exp_l = _elo_esperado(elo_l, elo_v)
    exp_v = 1.0 - exp_l

    if goles_local > goles_visita:
        res_l, res_v = 1.0, 0.0
    elif goles_local < goles_visita:
        res_l, res_v = 0.0, 1.0
    else:
        res_l, res_v = 0.5, 0.5

    elo_dict[local_key]  = round(elo_l + K_MUNDIAL * (res_l - exp_l), 2)
    elo_dict[visita_key] = round(elo_v + K_MUNDIAL * (res_v - exp_v), 2)


def actualizar_elo_mundial():
    # ── 1. Crear backup inmutable si aún no existe ────────────────────────────
    if not os.path.exists(RUTA_ELO_BASE):
        shutil.copy2(RUTA_ELO, RUTA_ELO_BASE)
        print(f"📁 Backup pre-torneo creado: {RUTA_ELO_BASE}")

    # ── 2. Cargar ELO base ────────────────────────────────────────────────────
    df_elo = pd.read_csv(RUTA_ELO_BASE)
    df_elo.columns = df_elo.columns.str.strip()
    elo_dict = dict(zip(df_elo['Team'], df_elo['Elo'].astype(float)))
    print(f"🏆 ELO base cargado: {len(elo_dict)} equipos")

    # ── 3. Cargar partidos completados ────────────────────────────────────────
    df_matches = pd.read_csv(RUTA_PARTIDOS)
    completados = df_matches[df_matches['status'] == 'complete'].copy()
    print(f"⚽ Partidos completados del Mundial 2026: {len(completados)}")

    # Ordenar por timestamp para respetar el orden cronológico
    completados = completados.sort_values('timestamp').reset_index(drop=True)

    # ── 4. Aplicar cada resultado ─────────────────────────────────────────────
    actualizados = 0
    for _, row in completados.iterrows():
        try:
            goles_l = int(row['home_team_goal_count'])
            goles_v = int(row['away_team_goal_count'])
        except (ValueError, TypeError):
            continue
        _aplicar_resultado(elo_dict, row['home_team_name'], row['away_team_name'],
                           goles_l, goles_v)
        actualizados += 1

    print(f"✅ Resultados aplicados: {actualizados}")

    # ── 5. Guardar ELO actualizado ────────────────────────────────────────────
    df_nuevo = pd.DataFrame(list(elo_dict.items()), columns=['Team', 'Elo'])
    df_nuevo = df_nuevo.sort_values('Elo', ascending=False).reset_index(drop=True)
    df_nuevo.to_csv(RUTA_ELO, index=False)
    print(f"💾 rankings_elo.csv actualizado con ELO post-{len(completados)} partidos")

    # ── 6. Mostrar top-20 ─────────────────────────────────────────────────────
    print("\n🥇 TOP 20 ELO post-Mundial 2026:")
    print(df_nuevo.head(20).to_string(index=False))


if __name__ == "__main__":
    actualizar_elo_mundial()
