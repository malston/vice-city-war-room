"""
Session helpers: run one Managed Agents session and pull down its files.

The streaming loop prints the parallel thread fan-out as it happens, so a
round is watchable. Files the agents write are saved under a name that can
never leave the output folder.
"""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from anthropic import Anthropic


BETA = "managed-agents-2026-04-01"


@dataclass(frozen=True)
class SessionResult:
    session_id: str
    text: str


def safe_output_path(out_dir: Path, filename: str) -> Path:
    """Return out_dir / <last path component of filename>.

    Agent-produced filenames are untrusted: directories, `..`, and absolute
    paths are stripped so a download can only land directly in out_dir.
    """
    name = PurePosixPath(filename.replace("\\", "/")).name
    if name in ("", ".", ".."):
        raise ValueError(f"Unusable output filename: {filename!r}")
    return out_dir / name


def run_session(
    client: Anthropic,
    agent_id: str,
    environment_id: str,
    message: str,
    title: str,
) -> SessionResult:
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=environment_id,
        title=title,
    )
    Path(".last_session_id").write_text(session.id)

    print("\n=== EVENT STREAM ===\n")
    text_parts: list[str] = []

    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": message}],
                }
            ],
        )
        for event in stream:
            t = event.type
            if t == "session.thread_created":
                print(f"  [thread spawned]   {event.agent_name}", flush=True)
            elif t == "session.thread_status_running":
                name = getattr(event, "agent_name", "?")
                print(f"  [thread running]   {name}", flush=True)
            elif t == "agent.thread_message_received":
                print(f"  [reply <-]         {event.from_agent_name}", flush=True)
            elif t == "agent.thread_message_sent":
                print(f"  [delegate ->]      {event.to_agent_name}", flush=True)
            elif t == "agent.message":
                for block in event.content:
                    if getattr(block, "type", None) == "text":
                        text_parts.append(block.text)
                        print(block.text, end="", flush=True)
            elif t == "agent.tool_use":
                print(f"\n  [tool: {getattr(event, 'name', '?')}]", flush=True)
            elif t == "session.status_idle":
                print("\n\n[swarm finished]")
                break

    return SessionResult(session_id=session.id, text="".join(text_parts))


def download_files(client: Anthropic, session_id: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = client.beta.files.list(scope_id=session_id, betas=[BETA])
    saved: list[Path] = []
    for f in files.data:
        out_path = safe_output_path(out_dir, f.filename)
        print(f"  {f.filename}  ->  {out_path}")
        client.beta.files.download(f.id).write_to_file(str(out_path))
        saved.append(out_path)
    return saved
