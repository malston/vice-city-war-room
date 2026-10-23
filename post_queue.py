"""
Build, approve, and hand out the posts for one round. Nothing is handed out
until the owner approves it.

Usage:
    python post_queue.py build --profiles profiles --out outputs/round-1
    python post_queue.py list --out outputs/round-1
    python post_queue.py approve --out outputs/round-1 person-mara scoreboard
    python post_queue.py approve --out outputs/round-1 --all
    python post_queue.py next --out outputs/round-1
    python post_queue.py mark-posted --out outputs/round-1 scoreboard
"""

import argparse
from pathlib import Path

from war_room.post_queue import (
    QUEUE_FILE,
    approve,
    approve_all,
    build_queue,
    load_queue,
    mark_posted,
    next_post,
    save_queue,
)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build or refresh the queue from the round folder")
    build.add_argument("--profiles", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)

    for name in ("list", "next"):
        commands.add_parser(name).add_argument("--out", type=Path, required=True)

    approve_cmd = commands.add_parser("approve", help="approve posts by id, or all of them")
    approve_cmd.add_argument("--out", type=Path, required=True)
    approve_cmd.add_argument("--all", action="store_true")
    approve_cmd.add_argument("ids", nargs="*")

    posted = commands.add_parser("mark-posted", help="record that an approved post was sent")
    posted.add_argument("--out", type=Path, required=True)
    posted.add_argument("id")

    args = parser.parse_args(argv)
    if args.command == "approve" and not args.all and not args.ids:
        parser.error("give at least one post id, or --all")
    return args


def load_or_exit(out: Path):
    path = out / QUEUE_FILE
    if not path.exists():
        raise SystemExit(f"No {QUEUE_FILE} in {out}. Run `python post_queue.py build` first.")
    return path, load_queue(path)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "build":
            path = args.out / QUEUE_FILE
            existing = load_queue(path) if path.exists() else None
            posts = build_queue(args.profiles, args.out, existing)
            save_queue(path, posts)
            print(f"Wrote {len(posts)} post(s) to {path}")
            return 0

        path, posts = load_or_exit(args.out)
        if args.command == "list":
            for post in posts:
                print(f"{post.id} {post.status}")
        elif args.command == "next":
            post = next_post(posts)
            if post is None:
                return 1
            print(post.text)
        elif args.command == "approve":
            save_queue(path, approve_all(posts) if args.all else approve(posts, args.ids))
        elif args.command == "mark-posted":
            save_queue(path, mark_posted(posts, args.id))
    except ValueError as error:
        raise SystemExit(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
