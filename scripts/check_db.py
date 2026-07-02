import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
conn = sqlite3.connect(os.path.join(ROOT, 'data', 'skynet.db'))

print("=== Total registros ===")
print("Partidos:", conn.execute("SELECT COUNT(*) FROM partidos").fetchone()[0])
print("Predicciones:", conn.execute("SELECT COUNT(*) FROM predicciones").fetchone()[0])
print("Resultados:", conn.execute("SELECT COUNT(*) FROM resultados").fetchone()[0])

print("\n=== Rango de fechas ===")
print(conn.execute("SELECT MIN(fecha), MAX(fecha) FROM partidos").fetchone())

print("\n=== Todos los partidos (ORDER BY fecha DESC) ===")
rows = conn.execute("SELECT id, fecha, local, visitante, torneo, estado FROM partidos ORDER BY fecha DESC").fetchall()
for r in rows:
    print(r)

print("\n=== Partidos con resultado ===")
rows2 = conn.execute("""
    SELECT p.fecha, p.local, p.visitante, r.resultado_texto
    FROM partidos p JOIN resultados r ON r.partido_id = p.id
    ORDER BY p.fecha DESC
""").fetchall()
for r in rows2:
    print(r)

conn.close()
