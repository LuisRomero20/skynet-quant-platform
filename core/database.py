import os
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_db_path() -> str:
    return os.getenv("SKYNET_DB_PATH", str(ROOT_DIR / "data" / "skynet.db"))


def get_db_path() -> str:
    return _get_db_path()


def crear_esquema() -> None:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            local TEXT NOT NULL,
            visitante TEXT NOT NULL,
            torneo TEXT,
            estado TEXT DEFAULT 'programado',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS predicciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER,
            modelo TEXT,
            prediccion TEXT,
            probabilidad REAL,
            confianza TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partido_id) REFERENCES partidos(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER,
            resultado REAL,
            resultado_texto TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partido_id) REFERENCES partidos(id)
        )
        """)
        conn.commit()
    finally:
        conn.close()


def guardar_partido(fecha: str, local: str, visitante: str, torneo: str | None = None, estado: str = "programado") -> int:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        cursor = conn.execute(
            """
            INSERT INTO partidos (fecha, local, visitante, torneo, estado)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fecha, local, visitante, torneo, estado),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def guardar_prediccion(partido_id: int, modelo: str, prediccion: str, probabilidad: float, confianza: str) -> int:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        cursor = conn.execute(
            """
            INSERT INTO predicciones (partido_id, modelo, prediccion, probabilidad, confianza)
            VALUES (?, ?, ?, ?, ?)
            """,
            (partido_id, modelo, prediccion, probabilidad, confianza),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def guardar_resultado(partido_id: int, resultado_texto: str, resultado: float | None = None) -> int:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        cursor = conn.execute(
            """
            INSERT INTO resultados (partido_id, resultado, resultado_texto)
            VALUES (?, ?, ?)
            """,
            (partido_id, resultado, resultado_texto),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def actualizar_estado_partido(partido_id: int, estado: str) -> None:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.execute("UPDATE partidos SET estado=? WHERE id=?", (estado, partido_id))
        conn.commit()
    finally:
        conn.close()


def buscar_o_crear_partido(fecha: str, local: str, visitante: str, torneo: str | None = None, estado: str = "programado") -> int:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        row = conn.execute(
            "SELECT id FROM partidos WHERE fecha=? AND local=? AND visitante=?",
            (fecha, local, visitante),
        ).fetchone()
        if row:
            return int(row[0])
        cursor = conn.execute(
            "INSERT INTO partidos (fecha, local, visitante, torneo, estado) VALUES (?, ?, ?, ?, ?)",
            (fecha, local, visitante, torneo, estado),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def buscar_o_crear_prediccion(partido_id: int, modelo: str, prediccion: str, probabilidad: float, confianza: str) -> int:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        row = conn.execute(
            "SELECT id FROM predicciones WHERE partido_id=? AND modelo=?",
            (partido_id, modelo),
        ).fetchone()
        if row:
            return int(row[0])
        cursor = conn.execute(
            "INSERT INTO predicciones (partido_id, modelo, prediccion, probabilidad, confianza) VALUES (?, ?, ?, ?, ?)",
            (partido_id, modelo, prediccion, probabilidad, confianza),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def tiene_resultado(partido_id: int) -> bool:
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        row = conn.execute("SELECT id FROM resultados WHERE partido_id=?", (partido_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def obtener_partidos_sin_resultado() -> list:
    """Devuelve lista de (partido_id, local, visitante) que aun no tienen resultado."""
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        return conn.execute(
            """
            SELECT pm.id, pm.local, pm.visitante
            FROM partidos pm
            LEFT JOIN resultados r ON r.partido_id = pm.id
            WHERE r.id IS NULL
            """
        ).fetchall()
    finally:
        conn.close()


def obtener_predicciones_auditoria() -> list:
    """Devuelve todas las predicciones desde la DB, una por partido, con resultado si está disponible."""
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        rows = conn.execute(
            """
            SELECT
                pm.fecha,
                pm.local || ' vs ' || pm.visitante AS partido,
                p.prediccion,
                r.resultado_texto
            FROM predicciones p
            JOIN partidos pm ON p.partido_id = pm.id
            LEFT JOIN resultados r ON r.partido_id = p.partido_id
            WHERE pm.id = (
                SELECT MAX(pm2.id)
                FROM partidos pm2
                WHERE pm2.local = pm.local AND pm2.visitante = pm.visitante
            )
            ORDER BY pm.fecha DESC, pm.local
            """
        ).fetchall()
        return [
            {
                "Fecha": row[0],
                "Partido": row[1],
                "Prediccion_IA": row[2],
                "Resultado_Real": row[3] if row[3] else "Pendiente",
                "Acierto": ("Sí" if row[2] == row[3] else "No") if row[3] else "Pendiente",
            }
            for row in rows
        ]
    finally:
        conn.close()


def obtener_estadisticas_basicas():
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        total_partidos = conn.execute("SELECT COUNT(*) FROM partidos").fetchone()[0]
        total_predicciones = conn.execute("SELECT COUNT(*) FROM predicciones").fetchone()[0]
        total_resultados = conn.execute("SELECT COUNT(*) FROM resultados").fetchone()[0]
        aciertos = conn.execute(
            """
            SELECT COUNT(*)
            FROM predicciones p
            JOIN resultados r ON r.partido_id = p.partido_id
            WHERE p.prediccion = r.resultado_texto
            """
        ).fetchone()[0]
        fallos = max(total_resultados - aciertos, 0)
        porcentaje_acierto = round((aciertos / total_resultados * 100), 2) if total_resultados else 0.0
        return {
            "total_partidos": total_partidos,
            "total_predicciones": total_predicciones,
            "total_resultados": total_resultados,
            "aciertos": aciertos,
            "fallos": fallos,
            "porcentaje_acierto": porcentaje_acierto,
        }
    finally:
        conn.close()


# Nombres en inglés o traducciones antiguas que no deberían estar en la DB.
# Si algún partido tiene uno de estos nombres, la DB necesita un rebuild.
_NOMBRES_INVALIDOS = {
    'Norway', 'Sweden', 'Mexico', 'Switzerland', 'Algeria', 'Egypt',
    'Scotland', 'Tunisia', 'Turkey', 'Qatar', 'Uzbekistan', 'Iraq',
    'Jordan', 'Haiti', 'Bosnia and Herzegovina', 'Bosnia Herzegovina',
    'Czech Republic', 'República Checa', 'USMNT', 'France', 'Germany',
    'England', 'Spain', 'Brazil', 'Japan', 'Belgium', 'Croatia',
    'Netherlands', 'Morocco', 'Canada', 'South Korea', 'South Africa',
    'Ivory Coast', 'Cape Verde Islands', 'Saudi Arabia', 'New Zealand',
    'Iran', 'Congo DR', 'DR Congo',
}


def necesita_rebuild_db() -> bool:
    """Devuelve True si la DB contiene entradas inválidas que requieren un rebuild completo."""
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        # 1. Entradas fuera del rango del Mundial 2026
        fuera_rango = conn.execute(
            "SELECT COUNT(*) FROM partidos WHERE fecha < '2026-06-01' OR fecha > '2026-07-20'"
        ).fetchone()[0]
        if fuera_rango > 0:
            return True

        # 2. Equipos con nombres no normalizados (inglés o traducciones antiguas)
        for nombre in _NOMBRES_INVALIDOS:
            hay = conn.execute(
                "SELECT 1 FROM partidos WHERE local=? OR visitante=? LIMIT 1",
                (nombre, nombre),
            ).fetchone()
            if hay:
                return True

        # 3. Duplicados: mismo (local, visitante) aparece más de una vez
        duplicados = conn.execute(
            """SELECT COUNT(*) FROM (
                SELECT local, visitante FROM partidos
                GROUP BY local, visitante HAVING COUNT(*) > 1
            )"""
        ).fetchone()[0]
        if duplicados > 0:
            return True

        return False
    finally:
        conn.close()


def limpiar_db_completa() -> None:
    """Borra todos los registros de partidos, predicciones y resultados."""
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.execute("DELETE FROM resultados")
        conn.execute("DELETE FROM predicciones")
        conn.execute("DELETE FROM partidos")
        conn.commit()
    finally:
        conn.close()


def obtener_estadisticas_predicciones():
    crear_esquema()
    conn = sqlite3.connect(_get_db_path())
    try:
        total_predicciones = conn.execute("SELECT COUNT(*) FROM predicciones").fetchone()[0]
        resueltas = conn.execute(
            "SELECT COUNT(*) FROM predicciones p JOIN resultados r ON r.partido_id = p.partido_id"
        ).fetchone()[0]
        aciertos = conn.execute(
            "SELECT COUNT(*) FROM predicciones p JOIN resultados r ON r.partido_id = p.partido_id WHERE p.prediccion = r.resultado_texto"
        ).fetchone()[0]
        fallos = max(resueltas - aciertos, 0)
        pendientes = max(total_predicciones - resueltas, 0)
        porcentaje_acierto = round((aciertos / resueltas * 100), 2) if resueltas else 0.0
        return {
            "total_predicciones": total_predicciones,
            "resueltas": resueltas,
            "pendientes": pendientes,
            "aciertos": aciertos,
            "fallos": fallos,
            "porcentaje_acierto": porcentaje_acierto,
        }
    finally:
        conn.close()
