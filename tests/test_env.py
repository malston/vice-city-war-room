"""Finding the API key: the environment first, then the repo's .env file."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from war_room.env import ENV_FILE, KEY_NAME, load_env, require_key

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_THAT_NEED_A_KEY = [
    ("create_specialists.py", []),
    ("create_cleaner.py", []),
    ("create_coordinator.py", []),
    ("upload_skills.py", []),
    ("setup_environment.py", []),
    ("run_war_room.py", ["--round", "1"]),
]
FILE_KEY = "fake-key-from-file"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Start with no key, and make sure whatever a test sets is removed afterwards."""
    for name in (KEY_NAME, "WAR_ROOM_ENV_FILE", "WAR_ROOM_TEST_VAR"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)


@pytest.fixture
def env_file(tmp_path):
    def write(text: str) -> Path:
        path = tmp_path / "keys.env"
        path.write_text(text)
        return path

    return write


def child_environment(**extra) -> dict:
    env = {name: value for name, value in os.environ.items() if name != KEY_NAME}
    env.update(extra)
    return env


def test_a_key_already_in_the_environment_wins_over_the_env_file(env_file, monkeypatch):
    monkeypatch.setenv(KEY_NAME, "fake-key-from-shell")

    source = load_env(env_file(f"{KEY_NAME}={FILE_KEY}\n"))

    assert source == "the environment"
    assert os.environ[KEY_NAME] == "fake-key-from-shell"


def test_the_env_file_key_is_used_when_the_environment_has_none(env_file):
    source = load_env(env_file(f"{KEY_NAME}={FILE_KEY}\n"))

    assert source == "keys.env"
    assert os.environ[KEY_NAME] == FILE_KEY


def test_a_blank_environment_key_counts_as_unset(env_file, monkeypatch):
    monkeypatch.setenv(KEY_NAME, "")

    source = load_env(env_file(f"{KEY_NAME}={FILE_KEY}\n"))

    assert source == "keys.env"
    assert os.environ[KEY_NAME] == FILE_KEY


def test_no_key_anywhere_gives_none(env_file, tmp_path):
    assert load_env(env_file("SOMETHING_ELSE=1\n")) is None
    assert load_env(tmp_path / "does-not-exist.env") is None
    assert KEY_NAME not in os.environ


def test_export_prefix_and_quotes_in_the_env_file_are_understood(env_file):
    load_env(env_file(f'export {KEY_NAME}="{FILE_KEY}"\n'))

    assert os.environ[KEY_NAME] == FILE_KEY


def test_other_variables_load_but_never_override_the_environment(env_file, monkeypatch):
    monkeypatch.setenv("WAR_ROOM_TEST_VAR", "from-shell")

    load_env(env_file(f"{KEY_NAME}={FILE_KEY}\nWAR_ROOM_TEST_VAR=from-file\n"))

    assert os.environ["WAR_ROOM_TEST_VAR"] == "from-shell"


def test_the_env_file_can_be_moved_with_an_environment_variable(env_file, monkeypatch):
    monkeypatch.setenv("WAR_ROOM_ENV_FILE", str(env_file(f"{KEY_NAME}={FILE_KEY}\n")))

    assert load_env() == "keys.env"


def test_the_default_env_file_is_in_the_repo_root_whatever_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert ENV_FILE == ROOT / ".env"


def test_require_key_returns_the_key_and_says_where_it_came_from(env_file, capsys):
    key = require_key(env_file(f"{KEY_NAME}={FILE_KEY}\n"))

    assert key == FILE_KEY
    assert capsys.readouterr().out == "Using ANTHROPIC_API_KEY from keys.env\n"


def test_require_key_exits_with_a_message_when_there_is_no_key(tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        require_key(tmp_path / "does-not-exist.env")

    assert str(exit_info.value).startswith("Set ANTHROPIC_API_KEY before running.")
    assert ".env" in str(exit_info.value)


@pytest.mark.parametrize("script, args", SCRIPTS_THAT_NEED_A_KEY)
def test_every_script_that_needs_a_key_says_how_to_provide_one(script, args, tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=tmp_path, capture_output=True, text=True, timeout=60,
        env=child_environment(WAR_ROOM_ENV_FILE=str(tmp_path / "does-not-exist.env")),
    )

    assert result.returncode != 0
    assert "Set ANTHROPIC_API_KEY before running." in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "script, args, id_files",
    [
        ("run_war_room.py", ["--round", "1"], []),
        ("create_coordinator.py", [], []),
        ("setup_environment.py", [], [".environment_id"]),
    ],
)
def test_scripts_read_the_key_from_the_env_file(script, args, id_files, env_file, tmp_path):
    for name in id_files:
        (tmp_path / name).write_text("env_existing")
    keys = env_file(f"{KEY_NAME}={FILE_KEY}\n")

    result = subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=tmp_path, capture_output=True, text=True, timeout=60,
        env=child_environment(WAR_ROOM_ENV_FILE=str(keys)),
    )

    assert "Using ANTHROPIC_API_KEY from keys.env" in result.stdout
    assert "Set ANTHROPIC_API_KEY" not in result.stdout + result.stderr
    assert FILE_KEY not in result.stdout + result.stderr


def test_the_demo_page_loads_the_key_so_its_steps_inherit_it(env_file):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    keys = env_file(f"{KEY_NAME}={FILE_KEY}\n")
    page = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "demo_ui.py")],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env=child_environment(WAR_ROOM_ENV_FILE=str(keys), DEMO_UI_PORT=str(port)),
    )
    try:
        seen = ""
        deadline = time.time() + 15
        while time.time() < deadline and "Demo UI on" not in seen:
            seen += page.stdout.readline()
    finally:
        page.kill()
        page.wait()

    assert "Using ANTHROPIC_API_KEY from keys.env" in seen
