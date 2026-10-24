"""make crew-setup, run in a temporary folder with a stand-in interpreter (no cloud calls)."""

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETUP_STEPS = [
    "check_key.py",
    "create_specialists.py",
    "create_cleaner.py",
    "create_coordinator.py",
    "upload_skills.py",
    "setup_environment.py",
]
SCRIPTS = SETUP_STEPS[1:]
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
    """An interpreter that records what it was asked to run. Only the key check really runs."""
    path = tmp_path / "fake-python"
    path.write_text(
        "#!/bin/sh\n"
        'echo "$1 environment_id=$([ -e .environment_id ] && echo present || echo absent)'
        ' key=${ANTHROPIC_API_KEY:-none}" >> "$CALLS_LOG"\n'
        f'[ "$1" = check_key.py ] && exec "{sys.executable}" "{ROOT}/check_key.py"\n'
        '[ "$1" = "$FAIL_ON" ] && exit 1\n'
        "exit 0\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def crew_setup(project, stand_in, tmp_path):
    log = tmp_path / "calls.log"

    def run(*args, key=None, env_file_text=None, fail_on=""):
        env = {
            name: value for name, value in os.environ.items()
            if not name.startswith("ANTHROPIC_") and name not in ("FORCE", "ID_BACKUP", "WAR_ROOM_ENV_FILE")
        }
        env.update(CALLS_LOG=str(log), FAIL_ON=fail_on, WAR_ROOM_ENV_FILE=str(tmp_path / "env"))
        if key:
            env["ANTHROPIC_API_KEY"] = key
        if env_file_text:
            (tmp_path / "env").write_text(env_file_text)
        result = subprocess.run(
            ["make", "-f", str(ROOT / "Makefile"), "crew-setup", f"PYTHON={stand_in}", *args],
            cwd=project, capture_output=True, text=True, env=env, timeout=60,
        )
        calls = log.read_text().splitlines() if log.exists() else []
        return result, calls

    return run


def script_names(calls):
    return [call.split()[0] for call in calls]


def backups(project):
    folder = project / "outputs" / "old-workspace-ids"
    return sorted(folder.iterdir()) if folder.exists() else []


def test_every_step_the_target_runs_is_a_script_in_the_repo():
    assert [name for name in SETUP_STEPS if not (ROOT / name).exists()] == []
    loop = re.search(r"for script in ([a-z_ ]+); do", (ROOT / "Makefile").read_text()).group(1).split()
    assert [f"{name}.py" for name in loop] == SCRIPTS


def test_default_target_lists_crew_setup():
    result = subprocess.run(["make", "-f", str(ROOT / "Makefile")], capture_output=True, text=True)

    assert "make crew-setup" in result.stdout


def test_checks_for_a_key_then_runs_the_five_setup_scripts_in_order(crew_setup):
    result, calls = crew_setup(key="fake-key")

    assert result.returncode == 0, result.stdout + result.stderr
    assert script_names(calls) == SETUP_STEPS
    assert "Using ANTHROPIC_API_KEY from the environment" in result.stdout
    assert "Crew ready" in result.stdout


@pytest.mark.parametrize("present", [".coordinator_id", ".skill_ids.json"])
def test_refuses_when_crew_ids_already_exist(crew_setup, project, present):
    (project / present).write_text("old")

    result, calls = crew_setup(key="fake-key")

    assert result.returncode != 0
    assert "FORCE=1" in result.stdout
    assert calls == []
    assert (project / present).read_text() == "old"


def test_refusal_says_when_only_some_of_the_ids_exist(crew_setup, project):
    (project / ".environment_id").write_text("env_old")

    result, _ = crew_setup(key="fake-key")

    assert "partial" in result.stdout


@pytest.mark.parametrize("value", ["", "0", "yes"])
def test_only_force_equal_to_one_overrides_the_refusal(crew_setup, project, value):
    (project / ".coordinator_id").write_text("agent_old")

    result, calls = crew_setup(f"FORCE={value}", key="fake-key")

    assert result.returncode != 0
    assert calls == []


def test_force_backs_up_the_old_ids_and_clears_them_before_the_scripts_run(crew_setup, project):
    for name, content in ID_FILES.items():
        (project / name).write_text(content)

    result, calls = crew_setup("FORCE=1", key="fake-key")

    assert result.returncode == 0, result.stdout + result.stderr
    (backup,) = backups(project)
    assert {path.name: path.read_text() for path in backup.iterdir()} == ID_FILES
    assert not any((project / name).exists() for name in ID_FILES)
    assert "setup_environment.py environment_id=absent" in " ".join(calls)
    assert str(backup.relative_to(project)) in result.stdout


def test_two_forced_runs_in_a_row_keep_separate_backups(crew_setup, project):
    for content in ("first", "second"):
        (project / ".coordinator_id").write_text(content)
        result, _ = crew_setup("FORCE=1", key="fake-key")
        assert result.returncode == 0, result.stdout + result.stderr

    assert sorted(path.joinpath(".coordinator_id").read_text() for path in backups(project)) == ["first", "second"]


def test_no_backup_folder_when_there_was_nothing_to_back_up(crew_setup, project):
    crew_setup(key="fake-key")

    assert backups(project) == []


def test_stops_at_the_first_failing_script(crew_setup):
    result, calls = crew_setup(key="fake-key", fail_on="create_cleaner.py")

    assert result.returncode != 0
    assert script_names(calls) == SETUP_STEPS[:3]
    assert "Crew ready" not in result.stdout
    assert "create_cleaner.py failed" in result.stdout


def test_a_failure_after_the_ids_were_moved_says_where_they_went(crew_setup, project):
    (project / ".coordinator_id").write_text("agent_old")

    result, _ = crew_setup("FORCE=1", key="fake-key", fail_on="create_specialists.py")

    assert result.returncode != 0
    (backup,) = backups(project)
    assert str(backup.relative_to(project)) in result.stdout
    assert (backup / ".coordinator_id").read_text() == "agent_old"


def test_a_backup_that_cannot_be_made_stops_before_anything_runs(crew_setup, project):
    (project / ".coordinator_id").write_text("agent_old")
    (project / "not-a-folder").write_text("")

    result, calls = crew_setup("FORCE=1", "ID_BACKUP=not-a-folder/ids", key="fake-key")

    assert result.returncode != 0
    assert "Could not back up" in result.stdout
    assert script_names(calls) == ["check_key.py"]
    assert (project / ".coordinator_id").read_text() == "agent_old"


def test_refuses_without_a_key_and_changes_nothing(crew_setup, project):
    (project / ".specialist_ids.json").write_text("{}")

    result, calls = crew_setup("FORCE=1")

    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in result.stderr
    assert script_names(calls) == ["check_key.py"]
    assert (project / ".specialist_ids.json").exists()


def test_the_key_can_come_from_the_env_file(crew_setup):
    result, calls = crew_setup(env_file_text="ANTHROPIC_API_KEY=fake-file-key\n")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Using ANTHROPIC_API_KEY from env" in result.stdout
    assert script_names(calls) == SETUP_STEPS


def test_the_env_file_is_read_as_data_not_run_as_shell(crew_setup, project):
    result, calls = crew_setup(
        env_file_text="GREETING=hello world\nPATH=/nonexistent\nANTHROPIC_API_KEY=fake-file-key\n"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert script_names(calls) == SETUP_STEPS
