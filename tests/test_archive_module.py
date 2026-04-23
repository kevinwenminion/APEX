import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from apex.archive import archive2db, archive_workdir, connect_database
from apex.config import Config


class TestArchiveModule(unittest.TestCase):
    def test_connect_database_rejects_unsupported_type(self):
        cfg = Config(database_type="local")
        with self.assertRaises(RuntimeError):
            connect_database(cfg)

    def test_archive2db_routes_to_sync_and_record(self):
        db = Mock()
        data = {"k": "v"}

        with patch("apex.archive.connect_database", return_value=db):
            cfg = Config(database_type="mongodb", archive_method="sync")
            archive2db(cfg, data, "id-sync")
            db.sync.assert_called_once_with(data, "id-sync", depth=2)

        db.reset_mock()
        with patch("apex.archive.connect_database", return_value=db):
            cfg = Config(database_type="mongodb", archive_method="record")
            archive2db(cfg, data, "id-record")
            db.record.assert_called_once_with(data, "id-record")

    def test_archive2db_rejects_unknown_method(self):
        db = Mock()
        with patch("apex.archive.connect_database", return_value=db):
            cfg = Config(database_type="mongodb", archive_method="unknown")
            with self.assertRaises(TypeError):
                archive2db(cfg, {"k": "v"}, "id")

    def test_archive_workdir_writes_all_result_for_local_mode(self):
        cfg = Config(database_type="local")
        with tempfile.TemporaryDirectory(prefix="apex-archive-") as td:
            archive_workdir(
                relax_param=None,
                props_param=None,
                config=cfg,
                work_dir=td,
                flow_type="props",
            )

            target = os.path.join(td, "all_result.json")
            self.assertTrue(os.path.isfile(target))
            with open(target, "r") as fp:
                payload = json.load(fp)

            self.assertIn("archive_key", payload)
            self.assertEqual(payload["work_path"], os.path.abspath(td))


if __name__ == "__main__":
    unittest.main()
