"""Find the Anthropic API key: the environment first, then the repo's .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

KEY_NAME = "ANTHROPIC_API_KEY"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path | None = None) -> str | None:
    """Make the key available and say where it came from, or None if no source has it.

    A key already in the environment is never replaced, and neither is any other variable
    that is already set. WAR_ROOM_ENV_FILE moves the file.
    """
    path = path or Path(os.environ.get("WAR_ROOM_ENV_FILE") or ENV_FILE)
    had_key = bool(os.environ.get(KEY_NAME))
    if not had_key:
        os.environ.pop(KEY_NAME, None)  # a blank value counts as unset
    load_dotenv(path)
    if had_key:
        return "the environment"
    return path.name if os.environ.get(KEY_NAME) else None


def require_key(path: Path | None = None) -> str:
    source = load_env(path)
    if source is None:
        raise SystemExit(
            f"Set {KEY_NAME} before running. It can be in your environment or in .env."
        )
    print(f"Using {KEY_NAME} from {source}")
    return os.environ[KEY_NAME]
