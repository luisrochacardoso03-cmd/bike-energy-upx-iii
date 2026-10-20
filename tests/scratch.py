"""Isolated test folders; optional workspace root for restricted Windows runners."""
import os
import shutil
import tempfile
import uuid
from pathlib import Path


class ScratchDirectory:
    def __init__(self):
        self.base = Path(os.environ.get('BIKE_TEST_ROOT', tempfile.gettempdir())).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.path = self.base / ('bike-test-' + uuid.uuid4().hex)
        self.path.mkdir()
        self.name = str(self.path)

    def __enter__(self):
        return self.name

    def __exit__(self, *_):
        self.cleanup()

    def cleanup(self):
        target = self.path.resolve()
        if target.parent != self.base or not target.name.startswith('bike-test-'):
            raise RuntimeError('Refusing cleanup outside the test directory')
        if target.exists():
            shutil.rmtree(target)
