import os
import tempfile
import unittest

from core.backtesting import ejecutar_backtesting
from core.database import crear_esquema, guardar_partido, guardar_prediccion, guardar_resultado


class BacktestingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = os.environ.get("SKYNET_DB_PATH")
        self.db_path = os.path.join(self.temp_dir.name, "test_backtesting.db")
        os.environ["SKYNET_DB_PATH"] = self.db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def tearDown(self):
        if self.original_db is None:
            os.environ.pop("SKYNET_DB_PATH", None)
        else:
            os.environ["SKYNET_DB_PATH"] = self.original_db
        self.temp_dir.cleanup()

    def test_ejecutar_backtesting(self):
        crear_esquema()
        partido_id = guardar_partido("2026-07-02", "Alemania", "España", "World Cup")
        guardar_prediccion(partido_id, "poisson", "Victoria Alemania", 0.39, "Media")
        guardar_resultado(partido_id, "Victoria Alemania", 1.0)

        metrics = ejecutar_backtesting(limit=5)
        self.assertEqual(metrics["total"], 1)
        self.assertEqual(metrics["aciertos"], 1)
        self.assertEqual(metrics["fallos"], 0)
        self.assertEqual(metrics["porcentaje"], 100.0)


if __name__ == "__main__":
    unittest.main()
