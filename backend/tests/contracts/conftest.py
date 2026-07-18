import json
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
EXAMPLES_DIR = REPO_ROOT / "contracts" / "examples"
OPENAPI_PATH = REPO_ROOT / "contracts" / "openapi.yaml"
FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "lumbar_mri_prior_auth.json"
POLICY_PATH = REPO_ROOT / "data" / "policies" / "lumbar_mri_policy.md"


@pytest.fixture(scope="session")
def fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text())
