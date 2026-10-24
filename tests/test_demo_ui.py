import json
import threading
import time
import urllib.error
import urllib.request
from types import SimpleNamespace
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


def thread(agent, status="idle", output_tokens=100, active_seconds=10.0):
    return SimpleNamespace(
        agent=SimpleNamespace(name=agent),
        status=status,
        usage=SimpleNamespace(output_tokens=output_tokens),
        stats=SimpleNamespace(active_seconds=active_seconds),
    )


def test_summarize_threads_groups_by_agent_and_counts_working_and_done():
    lanes = demo_ui.summarize_threads(
        [thread("The Fixer", "running"), thread("The Fixer"), thread("The Wheelman")]
    )

    by_name = {lane["name"]: lane for lane in lanes}
    assert by_name["The Fixer"]["threads"] == 2
    assert by_name["The Fixer"]["working"] == 1
    assert by_name["The Fixer"]["done"] == 1
    assert by_name["The Wheelman"]["working"] == 0
    assert by_name["The Wheelman"]["done"] == 1


def test_summarize_threads_orders_the_crew_mastermind_specialists_cleaner():
    threads = [
        thread("The Cleaner"),
        thread("The Quartermaster"),
        thread("The Mastermind"),
        thread("The Fixer"),
    ]

    names = [lane["name"] for lane in demo_ui.summarize_threads(threads)]

    assert names == ["The Mastermind", "The Fixer", "The Quartermaster", "The Cleaner"]


def test_summarize_threads_keeps_an_unknown_agent_after_the_known_ones():
    names = [lane["name"] for lane in demo_ui.summarize_threads([thread("The Mystery"), thread("The Fixer")])]

    assert names == ["The Fixer", "The Mystery"]


def test_summarize_threads_sums_tokens_and_active_seconds():
    threads = [
        thread("The Fixer", output_tokens=100, active_seconds=1.5),
        thread("The Fixer", output_tokens=50, active_seconds=2.0),
    ]

    (lane,) = demo_ui.summarize_threads(threads)

    assert lane["output_tokens"] == 150
    assert lane["active_seconds"] == 3.5


def test_summarize_threads_tolerates_a_thread_with_no_usage_yet():
    new_thread = SimpleNamespace(
        agent=SimpleNamespace(name="The Fixer"), status="running", usage=None, stats=None
    )

    (lane,) = demo_ui.summarize_threads([new_thread])

    assert (lane["working"], lane["output_tokens"], lane["active_seconds"]) == (1, 0, 0)


def test_crew_endpoint_without_a_session_is_empty(server, tmp_path, monkeypatch):
    monkeypatch.setattr(demo_ui, "LAST_SESSION", tmp_path / "no-session")

    assert get_json(f"{server}/api/crew") == {"session": None, "crew": []}


def test_crew_endpoint_reports_an_api_problem_instead_of_failing(server, tmp_path, monkeypatch):
    last_session = tmp_path / "last-session"
    last_session.write_text("sesn_does_not_exist\n")
    monkeypatch.setattr(demo_ui, "LAST_SESSION", last_session)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    data = get_json(f"{server}/api/crew")

    assert data["session"] == "sesn_does_not_exist"
    assert data["crew"] == []
    assert data["error"]


def test_summarize_threads_counts_a_rescheduling_thread_as_working():
    (lane,) = demo_ui.summarize_threads([thread("The Fixer", "rescheduling")])

    assert (lane["working"], lane["done"], lane["stopped"]) == (1, 0, 0)


def test_summarize_threads_counts_a_terminated_thread_as_stopped_not_done():
    (lane,) = demo_ui.summarize_threads([thread("The Fixer", "terminated"), thread("The Fixer")])

    assert (lane["working"], lane["done"], lane["stopped"]) == (0, 1, 1)


def test_crew_client_is_reused_between_polls(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    demo_ui.crew_client.cache_clear()

    assert demo_ui.crew_client() is demo_ui.crew_client()


def test_summarize_threads_names_an_advisor_thread_by_its_type():
    advisor_thread = SimpleNamespace(
        agent=SimpleNamespace(type="advisor", model="claude-opus-5-5"),
        status="idle",
        usage=None,
        stats=None,
    )

    (lane,) = demo_ui.summarize_threads([advisor_thread])

    assert lane["name"] == "advisor"
