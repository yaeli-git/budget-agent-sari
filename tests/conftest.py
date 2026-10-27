import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import budget_logic, log  # noqa: E402

log.QUIET = True


@pytest.fixture
def state(tmp_path):
    budget_logic.set_data_dir(str(tmp_path))
    return str(tmp_path)
