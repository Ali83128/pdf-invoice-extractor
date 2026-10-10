import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SAMPLES = ROOT / "samples"


@pytest.fixture(scope="session")
def truth():
    return json.loads((SAMPLES / "ground_truth.json").read_text())
