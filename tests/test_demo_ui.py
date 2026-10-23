import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import demo_ui


@pytest.fixture(autouse=True)
def clean_live_output():
    demo_ui.live.update(text="", running=False)
    yield
    demo_ui.live.update(text="", running=False)


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), demo_ui.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def get_json(url):
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def post_json(url, body):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_run_returns_the_exit_code_and_everything_the_command_printed():
    script = "import sys; print('out'); print('err', file=sys.stderr)"

    code, text = demo_ui.run("-c", script)

    assert code == 0
    assert text == f"$ -c {script}\nout\nerr\n"


def test_run_reports_a_nonzero_exit_code():
    code, _ = demo_ui.run("-c", "raise SystemExit(3)")

    assert code == 3


def test_run_shows_lines_while_the_command_is_still_running():
    script = "import time; print('fi' + 'rst'); time.sleep(1.5); print('se' + 'cond')"
    finished = threading.Thread(target=demo_ui.run, args=("-c", script))
    finished.start()
    deadline = time.time() + 1.0
    while "first" not in demo_ui.live["text"] and time.time() < deadline:
        time.sleep(0.05)

    still_running = finished.is_alive()
    seen = demo_ui.live["text"]
    finished.join()

    assert still_running
    assert "first" in seen
    assert "second" not in seen
    assert "second" in demo_ui.live["text"]


def test_run_kills_a_command_that_runs_too_long(monkeypatch):
    monkeypatch.setattr(demo_ui, "STEP_TIMEOUT", 0.5)

    code, text = demo_ui.run("-c", "import time; time.sleep(30)")

    assert code != 0
    assert "timed out" in text


def test_output_endpoint_serves_the_live_text(server):
    demo_ui.live.update(text="hello", running=True)

    assert get_json(f"{server}/api/output") == {"text": "hello", "running": True}


def test_a_step_clears_old_output_and_stops_running_when_it_fails(server):
    demo_ui.live.update(text="old output", running=False)

    status, body = post_json(f"{server}/api/step/reply", {"handle": "Bad", "text": "x"})

    assert status == 400
    assert "valid handle" in body["output"]
    assert get_json(f"{server}/api/output") == {"text": "", "running": False}
