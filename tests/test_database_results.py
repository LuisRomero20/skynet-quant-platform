import os
import tempfile
import unittest

from core.database import (
    crear_esquema,
    get_db_path,
    guardar_partido,
    guardar_prediccion,
    guardar_resultado,
    actualizar_estado_partido,
    obtener_estadisticas_basicas,
    obtener_estadisticas_predicciones,
)


class DatabaseResultsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = os.environ.get("SKYNET_DB_PATH")
        self.db_path = os.path.join(self.temp_dir.name, "test_skynet_results.db")
        os.environ["SKYNET_DB_PATH"] = self.db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def tearDown(self):
        if self.original_db is None:
            os.environ.pop("SKYNET_DB_PATH", None)
        else:
            os.environ["SKYNET_DB_PATH"] = self.original_db
        self.temp_dir.cleanup()

    def test_guardar_resultado_y_actualizar_estado(self):
        crear_esquema()
        partido_id = guardar_partido("2026-07-01", "Argentina", "Brasil", "World Cup")
        guardar_prediccion(partido_id, "poisson", "Victoria Argentina", 0.41, "Alta")
        guardar_resultado(partido_id, "Victoria Argentina", 1.0)
        actualizar_estado_partido(partido_id, "jugado")

        stats = obtener_estadisticas_basicas()
        self.assertEqual(stats["total_partidos"], 1)
        self.assertEqual(stats["total_predicciones"], 1)
        self.assertEqual(stats["total_resultados"], 1)

    def test_obtener_estadisticas_predicciones(self):
        crear_esquema()
        partido_id = guardar_partido("2026-07-01", "Argentina", "Brasil", "World Cup")
        guardar_prediccion(partido_id, "poisson", "Victoria Argentina", 0.41, "Alta")
        guardar_resultado(partido_id, "Victoria Argentina", 1.0)
        stats = obtener_estadisticas_predicciones()
        self.assertEqual(stats["total_predicciones"], 1)
        self.assertEqual(stats["resueltas"], 1)
        self.assertEqual(stats["pendientes"], 0)
        self.assertEqual(stats["aciertos"], 1)
        self.assertEqual(stats["porcentaje_acierto"], 100.0)


if __name__ == "__main__":
    unittest.main()
