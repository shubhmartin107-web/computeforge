import os
import tempfile

import pytest

from computeforge.observability.storage import StorageBackend


@pytest.fixture
async def storage():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    screenshot_dir = os.path.join(tmpdir, "screenshots")
    s = StorageBackend(db_path=db_path, screenshot_dir=screenshot_dir)
    await s.connect()
    yield s
    await s.close()
