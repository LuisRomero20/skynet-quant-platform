import os
import sqlite3
import tempfile
import unittest

from core.database import crear_esquema, get_db_path, guardar_partido


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = os.environ.get("SKYNET_DB_PATH")
        os.environ["SKYNET_DB_PATH"] = os.path.join(self.temp_dir.name, "test_skynet.db")

    def tearDown(self):
        if self.original_db is None:
            os.environ.pop("SKYNET_DB_PATH", None)
        else:
            os.environ["SKYNET_DB_PATH"] = self.original_db
        self.temp_dir.cleanup()

    def test_crear_esquema_y_guardar_partido(self):
        crear_esquema()
        guardar_partido(
            fecha="2026-06-30",
            local="Argentina",
            visitante="Francia",
            torneo="World Cup",
            estado="programado",
        )

        conn = sqlite3.connect(get_db_path())
        try:
            row = conn.execute(
                "SELECT local, visitante, torneo, estado FROM partidos WHERE local=? AND visitante=?",
                ("Argentina", "Francia"),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Argentina")
        self.assertEqual(row[1], "Francia")
        self.assertEqual(row[2], "World Cup")
        self.assertEqual(row[3], "programado")


if __name__ == "__main__":
    unittest.main()
