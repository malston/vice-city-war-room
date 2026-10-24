"""make crew-setup, run in a temporary folder with a stand-in interpreter (no cloud calls)."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = [
    "create_specialists.py",
    "create_cleaner.py",
    "create_coordinator.py",
    "upload_skills.py",
    "setup_environment.py",
]
ID_FILES = {
    ".specialist_ids.json": "{}",
    ".coordinator_id": "agent_old",
    ".environment_id": "env_old",
    ".skill_ids.json": "{}",
    ".last_session_id": "sesn_old",
}


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "project"
    folder.mkdir()
    return folder


@pytest.fixture
def stand_in(tmp_path):
    """An interpreter that records what it was asked to run instead of running it."""
    path = tmp_path / "fake-python"
    path.write_text(
        "#!/bin/sh\n"
        'echo "$1 environment_id=$([ -e .environment_id ] && echo present || echo absent)'
        ' key=${ANTHROPIC_API_KEY:-none}" >> "$CALLS_LOG"\n'
        '[ "$1" = "$FAIL_ON" ] && exit 1\n'
        "exit 0\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def crew_setup(project, stand_in, tmp_path):
    log = tmp_path / "calls.log"

    def run(*args, key=None, env_file_key=None, fail_on=""):
        env = {name: value for name, value in os.environ.items() if name != "ANTHROPIC_API_KEY"}
        env.update(CALLS_LOG=str(log), FAIL_ON=fail_on)
        if key:
            env["ANTHROPIC_API_KEY"] = key
        env_file = tmp_path / "env"
        if env_file_key:
            env_file.write_text(f"ANTHROPIC_API_KEY={env_file_key}\n")
        result = subprocess.run(
            ["make", "-f", str(ROOT / "Makefile"), "crew-setup", f"PYTHON={stand_in}", f"ENV_FILE={env_file}", *args],
            cwd=project, capture_output=True, text=True, env=env, timeout=60,
        )
        calls = log.read_text().splitlines() if log.exists() else []
        return result, calls

    return run


def script_names(calls):
    return [call.split()[0] for call in calls]


def test_default_target_lists_crew_setup():
    result = subprocess.run(["make", "-f", str(ROOT / "Makefile")], capture_output=True, text=True)

    assert "make crew-setup" in result.stdout


def test_runs_the_five_setup_scripts_in_order(crew_setup):
    result, calls = crew_setup(key="fake-key")

    assert result.returncode == 0, result.stdout + result.stderr
    assert script_names(calls) == SCRIPTS
    assert "Crew ready" in result.stdout


def test_refuses_when_a_crew_is_already_set_up(crew_setup, project):
    (project / ".coordinator_id").write_text("agent_old")

    result, calls = crew_setup(key="fake-key")

    assert result.returncode != 0
    assert "FORCE=1" in result.stdout
    assert calls == []
    assert (project / ".coordinator_id").read_text() == "agent_old"


def test_force_backs_up_the_old_ids_and_clears_them_before_the_scripts_run(crew_setup, project):
    for name, content in ID_FILES.items():
        (project / name).write_text(content)

    result, calls = crew_setup("FORCE=1", key="fake-key")

    assert result.returncode == 0, result.stdout + result.stderr
    (backup,) = (project / "outputs" / "old-workspace-ids").iterdir()
    assert {path.name: path.read_text() for path in backup.iterdir()} == ID_FILES
    assert not any((project / name).exists() for name in ID_FILES)
    assert "setup_environment.py environment_id=absent" in " ".join(calls)


def test_no_backup_folder_when_there_was_nothing_to_back_up(crew_setup, project):
    crew_setup(key="fake-key")

    assert not (project / "outputs" / "old-workspace-ids").exists()


def test_stops_at_the_first_failing_script(crew_setup):
    result, calls = crew_setup(key="fake-key", fail_on="create_cleaner.py")

    assert result.returncode != 0
    assert script_names(calls) == ["create_specialists.py", "create_cleaner.py"]
    assert "Crew ready" not in result.stdout


def test_refuses_without_a_key_and_changes_nothing(crew_setup, project):
    (project / ".specialist_ids.json").write_text("{}")

    result, calls = crew_setup("FORCE=1")

    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in result.stdout
    assert calls == []
    assert (project / ".specialist_ids.json").exists()


def test_key_in_the_environment_wins_over_the_env_file(crew_setup):
    _, calls = crew_setup(key="shell-key", env_file_key="file-key")

    assert calls and all(call.endswith("key=shell-key") for call in calls)


def test_env_file_key_is_used_when_the_environment_has_none(crew_setup):
    _, calls = crew_setup(env_file_key="file-key")

    assert calls and all(call.endswith("key=file-key") for call in calls)
