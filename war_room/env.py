"""Find the Anthropic API key: the environment first, then the repo's .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

KEY_NAME = "ANTHROPIC_API_KEY"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def env_file_path(path: Path | None = None) -> Path:
    return path or Path(os.environ.get("WAR_ROOM_ENV_FILE") or ENV_FILE)


def has_key() -> bool:
    return bool(os.environ.get(KEY_NAME, "").strip())


def load_env(path: Path | None = None) -> str | None:
    """Make the key available and say where it came from, or None if no source has it.

    A key already in the environment is never replaced, and neither is any other variable
    that is already set. A blank key counts as unset. WAR_ROOM_ENV_FILE moves the file.
    """
    path = env_file_path(path)
    had_key = has_key()
    if not had_key:
        os.environ.pop(KEY_NAME, None)
    try:
        load_dotenv(path)
    except OSError as error:
        raise SystemExit(f"Cannot read {path}: {error.strerror}")
    if had_key:
        return "the environment"
    if has_key():
        return path.name
    os.environ.pop(KEY_NAME, None)
    return None


def require_key(path: Path | None = None) -> str:
    """Return the key, or exit with a message saying where to put one."""
    path = env_file_path(path)
    source = load_env(path)
    if source is None:
        raise SystemExit(
            f"Set {KEY_NAME} before running. It can be in your environment or in {path.name}."
        )
    print(f"Using {KEY_NAME} from {source}")
    return os.environ[KEY_NAME]
