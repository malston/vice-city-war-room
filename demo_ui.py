"""
Browser front end for the demo in docs/demo.md. Standard library only.

    python demo_ui.py        # then open http://127.0.0.1:8765

Each button runs the same CLI commands as the walk-through, with fixed
arguments (nothing from the browser reaches a shell). Binds to localhost only.
"""

import json
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from war_room.fake_slack import DEFAULT_CHANNEL, format_message, load_channel
from war_room.profiles import HANDLE_RE

ROOT = Path(__file__).parent
PAGE = ROOT / "demo_ui.html"
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


def run(*cmd: str) -> tuple[int, str]:
    header = f"$ {' '.join(cmd)}\n"
    emit(header)
    p = subprocess.Popen(
        [PY, "-u", *cmd], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
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


def do_post_plans(_: dict) -> tuple[bool, str]:
    files = sorted(ROUND_DIR.glob("*.md"), key=lambda f: f.name == "scoreboard.md")
    if not files:
        raise ValueError("No plans yet. Run the swarm first (step 5).")
    return sequence(*[("fake_slack.py", "post", "--file", str(f)) for f in files])


def do_reset(_: dict) -> tuple[bool, str]:
    state["kickoff_ts"] = None
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
    "post": do_post_plans,
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
        elif self.path == "/api/output":
            with live_lock:
                self.json(200, dict(live))
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
        self.json(200, {"ok": ok, "output": out})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Demo UI on http://127.0.0.1:8765")
    server.serve_forever()
