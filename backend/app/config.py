"""Application configuration.

All runtime configuration is read from environment variables (prefix
``AUTHLENS_``) or a local ``.env`` file. No secrets are ever committed.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTHLENS_", env_file=".env", extra="ignore"
    )

    # --- Service ---
    app_name: str = "authlens"
    app_version: str = "0.1.0"
    environment: str = "dev"

    # --- LLM (Anthropic) ---
    # API key resolves from ANTHROPIC_API_KEY via the SDK default chain;
    # this override exists only for explicit injection in tests/CI.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"
    anthropic_max_tokens: int = 16000

    # --- Demo data (synthetic, hackathon-authored) ---
    demo_fixture_path: Path = REPO_ROOT / "data" / "fixtures" / "lumbar_mri_prior_auth.json"
    demo_policy_path: Path = REPO_ROOT / "data" / "policies" / "lumbar_mri_policy.md"

    # --- Safety rails (do not weaken; see docs/SAFETY_AND_HUMAN_REVIEW.md) ---
    # AuthLens never submits to a payer. There is no submission endpoint,
    # no submitted case state, and no configuration flag to enable one.
    terminal_case_state: str = "ready_for_review"


def get_settings() -> Settings:
    return Settings()
