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
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def post_json(url, body):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
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


@pytest.fixture
def demo_root(tmp_path, monkeypatch):
    """A temporary project folder for the page to work in, so tests never touch real outputs."""
    monkeypatch.setattr(demo_ui, "ROOT", tmp_path)
    round_dir = tmp_path / "outputs" / "round-1"
    round_dir.mkdir(parents=True)
    (tmp_path / "profiles").mkdir()
    for handle in ("jules", "mara"):
        (tmp_path / "profiles" / f"{handle}.json").write_text("{}")
        (round_dir / f"{handle}.md").write_text(f"*The Job: {handle.title()}*\nPlan for {handle}.\n")
    (round_dir / "scoreboard.md").write_text("*Board*\n1. Jules (A): 90/100\n2. Mara (B): 70/100\n")
    return tmp_path


def queue_statuses(server):
    return {post["id"]: post["status"] for post in get_json(f"{server}/api/queue")["posts"]}


def posted_texts(demo_root):
    from war_room.fake_slack import load_channel

    return [message["text"] for message in load_channel(demo_root / "outputs" / "demo" / "channel.json")]


def test_queue_endpoint_is_empty_before_the_queue_is_built(server, demo_root):
    assert get_json(f"{server}/api/queue") == {"posts": []}


def test_review_step_builds_the_queue_with_everything_pending(server, demo_root):
    status, body = post_json(f"{server}/api/step/queue", {})

    assert status == 200 and body["ok"]
    posts = get_json(f"{server}/api/queue")["posts"]
    assert [post["id"] for post in posts] == ["person-jules", "person-mara", "scoreboard"]
    assert {post["status"] for post in posts} == {"pending"}
    assert posts[1]["text"].startswith("*The Job: Mara*")


def test_post_step_refuses_while_nothing_is_approved(server, demo_root):
    post_json(f"{server}/api/step/queue", {})

    status, body = post_json(f"{server}/api/step/post", {})

    assert status == 400
    assert "Nothing is approved" in body["output"]
    assert "Drafts panel" in body["output"]
    assert not (demo_root / "outputs" / "demo" / "channel.json").exists()


def test_post_step_without_a_built_queue_says_to_review_first(server, demo_root):
    status, body = post_json(f"{server}/api/step/post", {})

    assert status == 400
    assert "Review the drafts first" in body["output"]


def test_approve_step_approves_only_the_chosen_posts(server, demo_root):
    post_json(f"{server}/api/step/queue", {})

    status, _ = post_json(f"{server}/api/step/approve", {"ids": ["person-mara"]})

    assert status == 200
    assert queue_statuses(server) == {
        "person-jules": "pending",
        "person-mara": "approved",
        "scoreboard": "pending",
    }


def test_approve_step_can_approve_everything(server, demo_root):
    post_json(f"{server}/api/step/queue", {})

    post_json(f"{server}/api/step/approve", {"all": True})

    assert set(queue_statuses(server).values()) == {"approved"}


@pytest.mark.parametrize("body", [{}, {"ids": []}, {"ids": "person-mara"}])
def test_approve_step_needs_posts_or_all(server, demo_root, body):
    post_json(f"{server}/api/step/queue", {})

    status, response = post_json(f"{server}/api/step/approve", body)

    assert status == 400
    assert "Choose" in response["output"]
    assert set(queue_statuses(server).values()) == {"pending"}


def test_approve_step_rejects_an_unknown_post_and_changes_nothing(server, demo_root):
    post_json(f"{server}/api/step/queue", {})

    status, response = post_json(f"{server}/api/step/approve", {"ids": ["person-mara", "person-nobody"]})

    assert status == 400
    assert "person-nobody" in response["output"]
    assert set(queue_statuses(server).values()) == {"pending"}


def test_approve_step_without_a_built_queue_says_to_review_first(server, demo_root):
    status, body = post_json(f"{server}/api/step/approve", {"all": True})

    assert status == 400
    assert "Review the drafts first" in body["output"]


def test_post_step_posts_only_approved_drafts_in_order_and_marks_them_posted(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"ids": ["scoreboard", "person-mara"]})

    status, body = post_json(f"{server}/api/step/post", {})

    assert status == 200 and body["ok"]
    texts = posted_texts(demo_root)
    assert [text.splitlines()[0] for text in texts] == ["*The Job: Mara*", "*Board*"]
    assert queue_statuses(server) == {
        "person-jules": "pending",
        "person-mara": "posted",
        "scoreboard": "posted",
    }


def test_nothing_is_posted_twice(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"all": True})
    post_json(f"{server}/api/step/post", {})

    status, body = post_json(f"{server}/api/step/post", {})

    assert status == 400
    assert "Nothing is approved" in body["output"]
    assert len(posted_texts(demo_root)) == 3


def test_a_draft_edited_after_approval_is_posted_only_after_it_is_approved_again(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"all": True})
    (demo_root / "outputs" / "round-1" / "mara.md").write_text("*The Job: Mara*\nA different plan.\n")

    post_json(f"{server}/api/step/queue", {})

    assert queue_statuses(server) == {
        "person-jules": "approved",
        "person-mara": "pending",
        "scoreboard": "approved",
    }
    post_json(f"{server}/api/step/post", {})
    assert not any("A different plan." in text or "Plan for mara." in text for text in posted_texts(demo_root))
    assert queue_statuses(server) == {
        "person-jules": "posted",
        "person-mara": "pending",
        "scoreboard": "posted",
    }


def test_the_post_uses_the_approved_text_not_whatever_is_in_the_file_now(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"ids": ["person-mara"]})
    (demo_root / "outputs" / "round-1" / "mara.md").write_text("*The Job: Mara*\nSneaky change.\n")

    post_json(f"{server}/api/step/post", {})

    (text,) = posted_texts(demo_root)
    assert "Plan for mara." in text
    assert "Sneaky change." not in text


def test_a_long_argument_is_shortened_in_the_command_line_shown_but_not_in_the_command():
    long_text = "x" * 400

    code, text = demo_ui.run("-c", "import sys; print(len(sys.argv[1]))", long_text)

    assert code == 0
    assert text.splitlines()[0].endswith("...")
    assert len(text.splitlines()[0]) < 200
    assert text.splitlines()[1] == "400"


def run_whole_round(server):
    for step, body in (("queue", {}), ("approve", {"all": True}), ("post", {})):
        status, _ = post_json(f"{server}/api/step/{step}", body)
        assert status == 200


def test_start_clean_clears_the_post_queue_so_the_next_round_can_be_approved(server, demo_root):
    run_whole_round(server)
    assert set(queue_statuses(server).values()) == {"posted"}
    (demo_root / "outputs" / "round-1" / "mara.md").write_text("*The Job: Mara*\nA second round plan.\n")

    status, _ = post_json(f"{server}/api/step/reset", {})

    assert status == 200
    assert get_json(f"{server}/api/queue") == {"posts": []}
    post_json(f"{server}/api/step/queue", {})
    assert set(queue_statuses(server).values()) == {"pending"}
    post_json(f"{server}/api/step/approve", {"all": True})
    post_json(f"{server}/api/step/post", {})
    assert any("A second round plan." in text for text in posted_texts(demo_root))


def test_review_step_without_drafts_says_to_run_the_swarm(server, demo_root):
    for draft in (demo_root / "outputs" / "round-1").glob("*.md"):
        draft.unlink()

    status, body = post_json(f"{server}/api/step/queue", {})

    assert status == 400
    assert "Run the swarm first" in body["output"]


def test_review_step_without_the_scoreboard_fails_and_builds_no_queue(server, demo_root):
    (demo_root / "outputs" / "round-1" / "scoreboard.md").unlink()

    status, body = post_json(f"{server}/api/step/queue", {})

    assert status == 200 and not body["ok"]
    assert "scoreboard.md" in body["output"]
    assert get_json(f"{server}/api/queue") == {"posts": []}


def test_a_failed_post_leaves_the_draft_approved_and_says_how_far_it_got(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"all": True})
    channel = demo_root / "outputs" / "demo" / "channel.json"
    channel.parent.mkdir(parents=True)
    channel.write_text("not json")

    status, body = post_json(f"{server}/api/step/post", {})

    assert status == 200 and not body["ok"]
    assert "Posted 0 draft(s). Stopped at person-jules." in body["output"]
    assert set(queue_statuses(server).values()) == {"approved"}


def test_a_post_that_could_not_be_recorded_tells_you_not_to_post_it_again(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"ids": ["person-mara"]})
    round_dir = demo_root / "outputs" / "round-1"
    round_dir.chmod(0o555)
    try:
        status, body = post_json(f"{server}/api/step/post", {})
    finally:
        round_dir.chmod(0o755)

    assert status == 200 and not body["ok"]
    assert len(posted_texts(demo_root)) == 1
    assert "person-mara was posted but could not be recorded" in body["output"]
    assert "Do not click Post again" in body["output"]
    assert queue_statuses(server)["person-mara"] == "approved"


def test_two_posts_at_once_post_each_draft_once(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"ids": ["person-mara"]})
    results = []
    clicks = [threading.Thread(target=lambda: results.append(post_json(f"{server}/api/step/post", {}))) for _ in range(2)]

    for click in clicks:
        click.start()
    for click in clicks:
        click.join()

    assert sorted(status for status, _ in results) == [200, 400]
    assert len(posted_texts(demo_root)) == 1


@pytest.mark.parametrize("body", [{"ids": [1]}, {"all": "yes"}, {"ids": ["--all"]}, {"ids": ["person-mara", ["x"]]}])
def test_approve_step_rejects_ids_that_are_not_post_ids(server, demo_root, body):
    post_json(f"{server}/api/step/queue", {})

    status, _ = post_json(f"{server}/api/step/approve", body)

    assert status == 400
    assert set(queue_statuses(server).values()) == {"pending"}


def test_a_posted_draft_cannot_be_approved_again(server, demo_root):
    post_json(f"{server}/api/step/queue", {})
    post_json(f"{server}/api/step/approve", {"ids": ["person-mara"]})
    post_json(f"{server}/api/step/post", {})

    post_json(f"{server}/api/step/approve", {"all": True})

    assert queue_statuses(server)["person-mara"] == "posted"
    post_json(f"{server}/api/step/post", {})
    assert len([text for text in posted_texts(demo_root) if "Plan for mara." in text]) == 1


@pytest.mark.parametrize("content", ["[1]", '[{"id": "x"}]', "{not json"])
def test_an_unreadable_queue_file_is_reported_not_crashed_on(server, demo_root, content):
    queue = demo_root / "outputs" / "round-1" / "post-queue.json"
    queue.write_text(content)

    read = urllib.request.Request(f"{server}/api/queue")
    with pytest.raises(urllib.error.HTTPError) as read_error:
        urllib.request.urlopen(read)
    assert read_error.value.code == 500
    assert "post-queue.json" in json.load(read_error.value)["error"]
    status, body = post_json(f"{server}/api/step/post", {})
    assert status == 400
    assert "post-queue.json" in body["output"]
    assert "build" in body["output"]


def test_an_unexpected_error_in_a_step_gets_an_answer_and_the_server_keeps_working(server, monkeypatch):
    def broken_step(_):
        raise RuntimeError("boom")

    monkeypatch.setitem(demo_ui.STEPS, "broken", broken_step)

    status, body = post_json(f"{server}/api/step/broken", {})

    assert status == 500 and not body["ok"]
    assert "RuntimeError: boom" in body["output"]
    assert get_json(f"{server}/api/output")["running"] is False


def test_the_drafts_panel_never_builds_markup_from_draft_text():
    assert "innerHTML" not in (demo_ui.CODE_DIR / "demo_ui.html").read_text()
