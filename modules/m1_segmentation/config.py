"""Database settings for the Module 1 standalone dashboard.

Values come from the repository's .env (falling back to the development
defaults in .env.example) so the dashboard connects to the same PostgreSQL
instance the rest of the system uses.

Note: an over-broad `config.py` rule in .gitignore once swallowed this file,
leaving dashboard.py importing a name nothing defined. Keep this file tracked.
"""

import os
from pathlib import Path


def _load_env() -> None:
    """Populate os.environ from the repo-root .env without overriding."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

DB_CONFIG = {
    "user": os.environ.get("POSTGRES_USER", "mos"),
    "password": os.environ.get("POSTGRES_PASSWORD", "mos_dev_password"),
    "dbname": os.environ.get("POSTGRES_DB", "marketing_os"),
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5434")),
}
