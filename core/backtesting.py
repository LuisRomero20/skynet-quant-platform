import os
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_db_path() -> str:
    return os.getenv("SKYNET_DB_PATH", str(ROOT_DIR / "data" / "skynet.db"))


def _crear_esquema_si_falta(conn: sqlite3.Connection) -> None:
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


def ejecutar_backtesting(limit: int = 20) -> dict:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        _crear_esquema_si_falta(conn)
        rows = conn.execute(
            """
            SELECT p.id, p.prediccion, r.resultado_texto
            FROM predicciones p
            JOIN resultados r ON r.partido_id = p.partido_id
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        total = len(rows)
        aciertos = sum(1 for _, pred, res in rows if pred == res)
        fallos = total - aciertos
        porcentaje = round((aciertos / total * 100), 2) if total else 0.0

        return {
            "total": total,
            "aciertos": aciertos,
            "fallos": fallos,
            "porcentaje": porcentaje,
        }
    finally:
        conn.close()
