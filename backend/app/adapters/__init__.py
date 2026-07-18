"""Agent A — adapters that turn on-disk synthetic data into frozen contracts."""

from app.adapters.fixture_loader import DemoFixture, load_demo_fixture
from app.adapters.fixture_provider import (
    ABRIDGE_FIXTURE_PREFIX,
    DEMO_FIXTURE_ID,
    FixtureProvider,
)

__all__ = [
    "ABRIDGE_FIXTURE_PREFIX",
    "DEMO_FIXTURE_ID",
    "DemoFixture",
    "FixtureProvider",
    "load_demo_fixture",
]
