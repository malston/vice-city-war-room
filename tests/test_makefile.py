"""The Makefile's start and stop targets, run against real processes on a free port."""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["ui", "ui-stop", "ui-restart", "ui-status", "ui-logs"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def is_listening(port: int) -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_until(condition, seconds=10.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def port():
    return free_port()


@pytest.fixture
def make(port, tmp_path):
    def run(*args, env=None):
        return subprocess.run(
            ["make", f"DEMO_UI_PORT={port}", f"PYTHON={sys.executable}", f"LOG={tmp_path / 'ui.log'}", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=60, env=env,
        )

    yield run
    run("ui-stop", "FORCE=1")


@pytest.fixture
def fake_listener(port):
    """Starts a process listening on the port, with `name` in its command line and one child."""
    started = []

    def start(name):
        code = (
            "import socket, subprocess, sys, time\n"
            f"s = socket.socket(); s.bind(('127.0.0.1', {port})); s.listen()\n"
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "time.sleep(60)\n"
        )
        proc = subprocess.Popen([sys.executable, "-c", code, name])
        started.append(proc)
        assert wait_until(lambda: is_listening(port)), "fake listener never started"
        return proc

    yield start
    for proc in started:
        proc.kill()
        proc.wait()


def children_of(pid: int) -> list[int]:
    result = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True)
    return [int(p) for p in result.stdout.split()]


def test_default_target_lists_every_target(port):
    result = subprocess.run(["make"], cwd=ROOT, capture_output=True, text=True)

    assert result.returncode == 0
    for target in TARGETS:
        assert f"make {target}" in result.stdout


def test_status_says_not_running_when_nothing_listens(make):
    result = make("ui-status")

    assert result.returncode == 0
    assert "Not running" in result.stdout


def test_stop_when_nothing_listens_is_not_an_error(make):
    result = make("ui-stop")

    assert result.returncode == 0
    assert "Not running" in result.stdout


def test_start_serves_the_page_and_stop_ends_it(make, port):
    started = make("ui")
    assert started.returncode == 0, started.stdout + started.stderr
    assert f"http://127.0.0.1:{port}" in started.stdout
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as page:
        assert page.status == 200

    again = make("ui")
    assert again.returncode == 0
    assert "Already running" in again.stdout
    assert "Running at" in make("ui-status").stdout

    stopped = make("ui-stop")
    assert stopped.returncode == 0
    assert "Stopped" in stopped.stdout
    assert wait_until(lambda: not is_listening(port))


def test_restart_replaces_the_running_server(make, port):
    make("ui")
    first = subprocess.run(["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()[0]

    restarted = make("ui-restart")

    assert restarted.returncode == 0, restarted.stdout + restarted.stderr
    second = subprocess.run(["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()[0]
    assert second != first


def test_stop_refuses_while_a_step_is_running_unless_forced(make, port, fake_listener):
    server = fake_listener("demo_ui.py")
    assert wait_until(lambda: children_of(server.pid)), "fake listener never started its child"
    (child,) = children_of(server.pid)

    refused = make("ui-stop")

    assert refused.returncode != 0
    assert "step is still running" in refused.stdout
    assert server.poll() is None
    os.kill(child, 0)

    forced = make("ui-stop", "FORCE=1")

    assert forced.returncode == 0
    assert "Stopped" in forced.stdout
    assert wait_until(lambda: server.poll() is not None)
    assert wait_until(lambda: not children_of(server.pid))


def test_stop_leaves_alone_a_process_that_is_not_the_demo_page(make, port, fake_listener):
    other = fake_listener("something_else.py")

    result = make("ui-stop", "FORCE=1")

    assert result.returncode != 0
    assert "not touching it" in result.stdout
    assert other.poll() is None


def page_environment(tmp_path, **extra) -> dict:
    env = {
        name: value for name, value in os.environ.items()
        if not name.startswith("ANTHROPIC_") and name != "WAR_ROOM_ENV_FILE"
    }
    return {**env, **extra}


def start_and_read_log(make, tmp_path, **extra) -> str:
    started = make("ui", env=page_environment(tmp_path, **extra))
    assert started.returncode == 0, started.stdout + started.stderr
    return (tmp_path / "ui.log").read_text()


def test_start_uses_a_key_already_in_the_environment_over_the_env_file(make, tmp_path):
    env_file = tmp_path / "keys.env"
    env_file.write_text("ANTHROPIC_API_KEY=fake-key-from-file\n")

    log = start_and_read_log(make, tmp_path, ANTHROPIC_API_KEY="fake-key-from-shell", WAR_ROOM_ENV_FILE=str(env_file))

    assert "Using ANTHROPIC_API_KEY from the environment" in log
    assert "fake-key" not in log


def test_start_uses_the_env_file_key_when_the_environment_has_none(make, tmp_path):
    env_file = tmp_path / "keys.env"
    env_file.write_text("ANTHROPIC_API_KEY=fake-key-from-file\n")

    log = start_and_read_log(make, tmp_path, WAR_ROOM_ENV_FILE=str(env_file))

    assert "Using ANTHROPIC_API_KEY from keys.env" in log


def test_start_without_a_key_still_serves_the_page_and_the_log_says_the_swarm_step_will_fail(make, tmp_path):
    log = start_and_read_log(make, tmp_path, WAR_ROOM_ENV_FILE=str(tmp_path / "missing.env"))

    assert "No ANTHROPIC_API_KEY found" in log


def test_start_reports_a_page_that_does_not_come_up(make, tmp_path):
    result = make("ui", "PYTHON=false")

    assert result.returncode != 0
    assert "did not come up" in result.stdout
