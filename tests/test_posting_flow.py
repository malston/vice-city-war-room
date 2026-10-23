import json

import movers
import post_queue


def next_text(out, capsys):
    capsys.readouterr()
    code = post_queue.main(["next", "--out", str(out)])
    return code, capsys.readouterr().out.strip()


def post_and_mark(out, capsys, post_id):
    post_queue.main(["mark-posted", "--out", str(out), post_id])
    capsys.readouterr()


def test_full_round_flow_posts_each_approved_post_once(tmp_path, capsys):
    profiles = tmp_path / "profiles"
    out = tmp_path / "round-2"
    profiles.mkdir()
    out.mkdir()
    for handle in ("amy", "zed"):
        (profiles / f"{handle}.json").write_text(json.dumps({"handle": handle}))
        (out / f"{handle}.md").write_text(f"plan for {handle}")
    (out / "scoreboard.md").write_text("1. Amy (A): 80/100\n2. Zed (Z): 61/100\n")
    prev = tmp_path / "prev-scoreboard.md"
    prev.write_text("1. Amy (A): 75/100\n2. Zed (Z): 30/100\n")

    assert (
        movers.main(
            ["--prev", str(prev), "--curr", str(out / "scoreboard.md"), "--out", str(out / "movers.md")]
        )
        == 0
    )
    assert post_queue.main(["build", "--profiles", str(profiles), "--out", str(out)]) == 0

    code, text = next_text(out, capsys)
    assert (code, text) == (1, "")

    post_queue.main(["approve", "--out", str(out), "person-amy"])
    code, text = next_text(out, capsys)
    assert (code, text) == (0, "plan for amy")

    post_and_mark(out, capsys, "person-amy")
    code, text = next_text(out, capsys)
    assert (code, text) == (1, "")

    post_queue.main(["approve", "--out", str(out), "--all"])
    seen = []
    while True:
        code, text = next_text(out, capsys)
        if code != 0:
            break
        seen.append(text)
        post_id = next(
            p.id
            for p in post_queue.load_queue(out / post_queue.QUEUE_FILE)
            if p.status == "approved"
        )
        post_and_mark(out, capsys, post_id)

    assert seen[0] == "plan for zed"
    assert seen[1] == (out / "scoreboard.md").read_text().strip()
    assert "Zed, 30 to 61 (+31)" in seen[2]
    assert len(seen) == 3
