import os
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_db_path() -> str:
    return os.getenv("SKYNET_DB_PATH", str(ROOT_DIR / "data" / "skynet.db"))


def ejecutar_backtesting(limit: int = 20) -> dict:
    conn = sqlite3.connect(_get_db_path())
    try:
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
