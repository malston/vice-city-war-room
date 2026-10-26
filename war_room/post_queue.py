"""The approved-post queue: nothing is returned for posting until it is approved."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

QUEUE_FILE = "post-queue.json"


@dataclass(frozen=True)
class Post:
    id: str
    kind: str  # person, scoreboard, or movers
    handle: str | None
    text: str
    status: str  # pending, approved, or posted


def _read(out_dir: Path, name: str) -> str:
    path = out_dir / name
    if not path.exists():
        raise ValueError(f"Missing file: {name} (looked in {out_dir})")
    return path.read_text()


def build_queue(profiles_dir: Path, out_dir: Path, existing: list[Post] | None = None) -> list[Post]:
    handles = sorted(path.stem for path in Path(profiles_dir).glob("*.json"))
    fresh = [Post(f"person-{h}", "person", h, _read(out_dir, f"{h}.md"), "pending") for h in handles]
    fresh.append(Post("scoreboard", "scoreboard", None, _read(out_dir, "scoreboard.md"), "pending"))
    if (out_dir / "movers.md").exists():
        fresh.append(Post("movers", "movers", None, _read(out_dir, "movers.md"), "pending"))

    old = {post.id: post for post in existing or []}
    merged = []
    for post in fresh:
        prior = old.get(post.id)
        if prior is not None and prior.status == "posted":
            post = prior
        elif prior is not None and prior.text == post.text:
            post = replace(post, status=prior.status)
        merged.append(post)
    return merged


def load_queue(path: Path) -> list[Post]:
    try:
        return [Post(**item) for item in json.loads(path.read_text())]
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"{path} is not a valid post queue ({error}). Delete it and build again; this forgets which drafts were posted. "
            "On the demo page, click Start clean (button 1), then Review the drafts (button 6)."
        ) from error


def save_queue(path: Path, posts: list[Post]) -> None:
    """Replace the file in one step, so a reader never sees half of it."""
    text = json.dumps([asdict(post) for post in posts], indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "w") as temp:
            temp.write(text)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _require_ids(posts: list[Post], ids: list[str]) -> None:
    known = {post.id for post in posts}
    for post_id in ids:
        if post_id not in known:
            raise ValueError(f"Unknown post id: {post_id}")


def approve(posts: list[Post], ids: list[str]) -> list[Post]:
    _require_ids(posts, ids)
    return [
        replace(post, status="approved") if post.id in ids and post.status == "pending" else post
        for post in posts
    ]


def approve_all(posts: list[Post]) -> list[Post]:
    return approve(posts, [post.id for post in posts])


def next_post(posts: list[Post]) -> Post | None:
    return next((post for post in posts if post.status == "approved"), None)


def mark_posted(posts: list[Post], post_id: str) -> list[Post]:
    _require_ids(posts, [post_id])
    target = next(post for post in posts if post.id == post_id)
    if target.status != "approved":
        raise ValueError(f"Post {post_id} is {target.status}; only approved posts can be marked posted")
    return [replace(post, status="posted") if post.id == post_id else post for post in posts]
