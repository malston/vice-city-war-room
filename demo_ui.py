"""
Browser front end for the demo in docs/demo.md. Needs the anthropic SDK for the crew
panel and otherwise only the standard library.

    python demo_ui.py        # then open http://127.0.0.1:8765

Each button runs the same CLI commands as the walk-through, with fixed
arguments (nothing from the browser reaches a shell). Binds to localhost only.
"""

import functools
import json
import os
import re
import subprocess
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from anthropic import Anthropic

from war_room.env import load_env
from war_room.fake_slack import DEFAULT_CHANNEL, format_message, load_channel
from war_room.post_queue import QUEUE_FILE, load_queue, next_post
from war_room.profiles import HANDLE_RE

CODE_DIR = Path(__file__).parent
ROOT = CODE_DIR  # the folder the steps run in and read drafts from; tests point it at a temporary one
LAST_SESSION = ROOT / ".last_session_id"
CREW_ORDER = (
    "The Mastermind", "The Fixer", "The Smooth Talker",
    "The Wheelman", "The Quartermaster", "The Cleaner",
)
THREAD_STATUS_LANE = {
    "running": "working", "rescheduling": "working", "idle": "done", "terminated": "stopped",
}
PAGE = CODE_DIR / "demo_ui.html"
MESSAGES = "outputs/messages.json"
ROUND_DIR = Path("outputs/round-1")
PY = sys.executable
state = {"kickoff_ts": None}  # ponytail: one in-memory demo session, single presenter
lock = threading.Lock()
STEP_TIMEOUT = 900
live = {"text": "", "running": False}  # output of the step in progress, served at /api/output
live_lock = threading.Lock()


def emit(text: str) -> None:
    with live_lock:
        live["text"] += text


@functools.cache
def crew_client() -> Anthropic:
    return Anthropic()


def summarize_threads(threads) -> list[dict]:
    lanes: dict[str, dict] = {}
    for t in threads:
        name = getattr(t.agent, "name", None) or t.agent.type
        lane = lanes.setdefault(name, {
            "name": name, "threads": 0, "working": 0, "done": 0, "stopped": 0,
            "output_tokens": 0, "active_seconds": 0.0,
        })
        lane["threads"] += 1
        lane[THREAD_STATUS_LANE[t.status]] += 1
        lane["output_tokens"] += t.usage.output_tokens if t.usage else 0
        lane["active_seconds"] += t.stats.active_seconds if t.stats else 0
    known = [lanes[name] for name in CREW_ORDER if name in lanes]
    others = [lane for name, lane in lanes.items() if name not in CREW_ORDER]
    return [{**lane, "active_seconds": round(lane["active_seconds"], 1)} for lane in known + others]


def crew_status() -> dict:
    if not LAST_SESSION.exists():
        return {"session": None, "crew": []}
    session_id = LAST_SESSION.read_text().strip()
    try:
        threads = crew_client().beta.sessions.threads.list(session_id, limit=100).data
    except Exception as error:  # the page shows the message and keeps polling
        return {"session": session_id, "crew": [], "error": str(error)[:200]}
    return {"session": session_id, "crew": summarize_threads(threads)}


def shorten(arg: str, limit: int = 80) -> str:
    return arg if len(arg) <= limit else arg[: limit - 3] + "..."


def run(*cmd: str) -> tuple[int, str]:
    header = f"$ {' '.join(shorten(arg) for arg in cmd)}\n"
    emit(header)
    script = str(CODE_DIR / cmd[0]) if cmd[0].endswith(".py") else cmd[0]
    p = subprocess.Popen(
        [PY, "-u", script, *cmd[1:]], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    timed_out = threading.Event()

    def kill() -> None:
        timed_out.set()
        p.kill()

    timer = threading.Timer(STEP_TIMEOUT, kill)
    timer.start()
    lines = []
    try:
        for line in p.stdout:
            lines.append(line)
            emit(line)
        code = p.wait()
    finally:
        timer.cancel()
    if timed_out.is_set():
        note = f"(timed out after {STEP_TIMEOUT} s)\n"
        lines.append(note)
        emit(note)
        code = code or 1
    return code, header + "".join(lines)


def sequence(*cmds: tuple[str, ...]) -> tuple[bool, str]:
    out = ""
    for cmd in cmds:
        code, text = run(*cmd)
        out += text + "\n"
        if code:
            return False, out
    return True, out


def need_kickoff() -> str:
    if not state["kickoff_ts"]:
        raise ValueError("Post the kickoff first (step 2).")
    return state["kickoff_ts"]


def do_kickoff(_: dict) -> tuple[bool, str]:
    code, out = run("fake_slack.py", "post", "--file", "docs/kickoff-post.md", "--fenced")
    m = re.search(r"ts: (\S+)", out)
    if code or not m:
        return False, out
    state["kickoff_ts"] = m.group(1)
    return True, out


def do_reply(body: dict) -> tuple[bool, str]:
    handle, text = str(body.get("handle", "")), str(body.get("text", "")).strip()
    if not HANDLE_RE.fullmatch(handle) or not text or len(text) > 1000:
        raise ValueError("Need a valid handle and text (max 1000 chars).")
    return sequence(("fake_slack.py", "reply", "--as", handle, "--text", text))


def do_profiles(_: dict) -> tuple[bool, str]:
    ts = need_kickoff()
    return sequence(
        ("fake_slack.py", "read", "--since", ts, "--out", MESSAGES),
        ("parse_profiles.py", "--messages", MESSAGES, "--kickoff-ts", ts),
    )


def read_queue():
    path = ROOT / ROUND_DIR / QUEUE_FILE
    return load_queue(path) if path.exists() else None


def need_queue():
    posts = read_queue()
    if posts is None:
        raise ValueError("Review the drafts first (step 6).")
    return posts


def do_queue(_: dict) -> tuple[bool, str]:
    if not any((ROOT / ROUND_DIR).glob("*.md")):
        raise ValueError("No drafts yet. Run the swarm first (step 5).")
    return sequence(
        ("post_queue.py", "build", "--profiles", "profiles", "--out", str(ROUND_DIR)),
        ("post_queue.py", "list", "--out", str(ROUND_DIR)),
    )


def do_approve(body: dict) -> tuple[bool, str]:
    known = {post.id for post in need_queue()}
    ids = body.get("ids")
    if body.get("all") is True:
        chosen = ("--all",)
    elif isinstance(ids, list) and ids and all(isinstance(post_id, str) for post_id in ids):
        unknown = [post_id for post_id in ids if post_id not in known]
        if unknown:
            raise ValueError("Unknown draft: " + ", ".join(unknown))
        chosen = tuple(ids)
    else:
        raise ValueError("Choose a draft to approve, or approve all.")
    return sequence(
        ("post_queue.py", "approve", "--out", str(ROUND_DIR), *chosen),
        ("post_queue.py", "list", "--out", str(ROUND_DIR)),
    )


def do_post_approved(_: dict) -> tuple[bool, str]:
    """Post each approved draft with the text that was approved, then mark it posted."""
    out = ""
    posted = 0
    while True:
        post = next_post(need_queue())
        if post is None:
            break
        ok, text = sequence(("fake_slack.py", "post", f"--text={post.text}"))
        out += text
        if not ok:
            return False, out + f"Posted {posted} draft(s). Stopped at {post.id}.\n"
        ok, text = sequence(("post_queue.py", "mark-posted", "--out", str(ROUND_DIR), post.id))
        out += text
        if not ok:
            return False, out + (
                f"{post.id} was posted but could not be recorded. Do not click Post again, "
                f"or it goes out twice. Fix the problem above, then run: "
                f"python post_queue.py mark-posted --out {ROUND_DIR} {post.id}\n"
            )
        posted += 1
    if not posted:
        raise ValueError("Nothing is approved yet. Approve a draft in the Drafts panel first.")
    return True, out


def do_reset(_: dict) -> tuple[bool, str]:
    state["kickoff_ts"] = None
    (ROOT / ROUND_DIR / QUEUE_FILE).unlink(missing_ok=True)
    return sequence(("fake_slack.py", "reset"))


STEPS = {
    "reset": do_reset,
    "kickoff": do_kickoff,
    "seed": lambda _: sequence(("fake_slack.py", "seed", "--delay", "1")),
    "reply": do_reply,
    "profiles": do_profiles,
    "swarm": lambda _: sequence(
        ("run_war_room.py", "--round", "1", "--profiles", "profiles"),
        ("check_outputs.py", "--profiles", "profiles", "--out", "outputs/round-1",
         "--facts", "synthetic-data/launch-facts.md"),
    ),
    "queue": do_queue,
    "approve": do_approve,
    "post": do_post_approved,
}


class Handler(BaseHTTPRequestHandler):
    def send(self, status: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def json(self, status: int, data: dict) -> None:
        self.send(status, json.dumps(data).encode())

    def do_GET(self) -> None:
        if self.path == "/":
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/crew":
            self.json(200, crew_status())
        elif self.path == "/api/output":
            with live_lock:
                self.json(200, dict(live))
        elif self.path == "/api/queue":
            try:
                posts = read_queue() or []
            except ValueError as e:
                return self.json(500, {"error": str(e)})
            self.json(200, {"posts": [
                {"id": p.id, "kind": p.kind, "handle": p.handle, "status": p.status, "text": p.text}
                for p in posts
            ]})
        elif self.path == "/api/channel":
            try:
                msgs = load_channel(ROOT / DEFAULT_CHANNEL)
            except ValueError as e:
                return self.json(500, {"error": str(e)})
            self.json(200, {
                "kickoff_ts": state["kickoff_ts"],
                "messages": [
                    {"name": m["author_name"], "handle": m["author_handle"],
                     "text": m["text"], "line": format_message(m).split(" ")[0]}
                    for m in msgs
                ],
            })
        else:
            self.send(404, b"{}")

    def do_POST(self) -> None:
        name = self.path.removeprefix("/api/step/")
        step = STEPS.get(name)
        if not self.path.startswith("/api/step/") or not step:
            return self.send(404, b"{}")
        try:
            size = min(int(self.headers.get("Content-Length") or 0), 10_000)
            body = json.loads(self.rfile.read(size) or b"{}")
            with lock:  # one step at a time
                with live_lock:
                    live.update(text="", running=True)
                try:
                    ok, out = step(body if isinstance(body, dict) else {})
                finally:
                    with live_lock:
                        live["running"] = False
        except (ValueError, subprocess.TimeoutExpired) as e:
            return self.json(400, {"ok": False, "output": str(e)})
        except Exception as e:  # the browser gets an answer; the traceback goes to this terminal
            traceback.print_exc()
            return self.json(500, {"ok": False, "output": f"Server error: {type(e).__name__}: {e}. See the terminal running demo_ui.py."})
        self.json(200, {"ok": ok, "output": out})


if __name__ == "__main__":
    # The page works without a key, but its swarm step and Crew panel need one, and
    # the steps it runs inherit this process's environment.
    source = load_env()
    print(
        f"Using ANTHROPIC_API_KEY from {source}"
        if source
        else "No ANTHROPIC_API_KEY found. The swarm step will fail. Set it in your environment or in .env.",
        flush=True,
    )
    port = int(os.environ.get("DEMO_UI_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Demo UI on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
