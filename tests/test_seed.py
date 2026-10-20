from scratch import ScratchDirectory
import unittest
from pathlib import Path
from unittest.mock import patch
from app import seed
from energy.service import Service


class SeedTests(unittest.TestCase):
    def test_interrupted_seed_rolls_back_and_can_be_retried(self):
        with ScratchDirectory() as directory:
            folder = Path(directory)
            service = Service(folder/'seed.sqlite3')
            with patch.object(Path,'write_text',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    seed(service,folder)
            with service.db.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)
            seed(service,folder)
            credentials = (folder/'ACESSOS_DEMO.txt').read_text(encoding='utf-8')
            seed(service,folder)
            self.assertEqual((folder/'ACESSOS_DEMO.txt').read_text(encoding='utf-8'),credentials)
            with service.db.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM bikes').fetchone()[0],3)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM rides').fetchone()[0],2)
