import json
from pathlib import Path

import pytest

import post_queue as queue_cli
from war_room.post_queue import (
    QUEUE_FILE,
    Post,
    approve,
    approve_all,
    build_queue,
    load_queue,
    mark_posted,
    next_post,
    save_queue,
)


def make_round(tmp_path: Path, handles=("zed", "amy"), movers: bool = True):
    profiles = tmp_path / "profiles"
    out = tmp_path / "round-1"
    profiles.mkdir()
    out.mkdir()
    for handle in handles:
        (profiles / f"{handle}.json").write_text(json.dumps({"handle": handle}))
        (out / f"{handle}.md").write_text(f"plan for {handle}")
    (out / "scoreboard.md").write_text("1. Amy (A): 80/100")
    if movers:
        (out / "movers.md").write_text("movers text")
    return profiles, out


def by_id(posts: list[Post]) -> dict[str, Post]:
    return {post.id: post for post in posts}


def test_build_orders_people_by_handle_then_scoreboard_then_movers(tmp_path):
    profiles, out = make_round(tmp_path)
    posts = build_queue(profiles, out)
    assert [p.id for p in posts] == ["person-amy", "person-zed", "scoreboard", "movers"]
    assert [p.kind for p in posts] == ["person", "person", "scoreboard", "movers"]
    assert posts[0].handle == "amy"
    assert posts[2].handle is None


def test_build_without_a_movers_file_has_no_movers_post(tmp_path):
    profiles, out = make_round(tmp_path, movers=False)
    assert "movers" not in [p.id for p in build_queue(profiles, out)]


def test_build_starts_every_post_pending(tmp_path):
    profiles, out = make_round(tmp_path)
    assert {p.status for p in build_queue(profiles, out)} == {"pending"}


def test_missing_person_file_raises_value_error_naming_it(tmp_path):
    profiles, out = make_round(tmp_path)
    (out / "amy.md").unlink()
    with pytest.raises(ValueError, match="amy.md"):
        build_queue(profiles, out)


def test_missing_scoreboard_raises_value_error(tmp_path):
    profiles, out = make_round(tmp_path)
    (out / "scoreboard.md").unlink()
    with pytest.raises(ValueError, match="scoreboard.md"):
        build_queue(profiles, out)


def test_rebuild_keeps_status_when_text_is_unchanged(tmp_path):
    profiles, out = make_round(tmp_path)
    first = approve(build_queue(profiles, out), ["person-amy"])
    again = build_queue(profiles, out, existing=first)
    assert by_id(again)["person-amy"].status == "approved"


def test_rebuild_resets_approved_to_pending_when_text_changes(tmp_path):
    profiles, out = make_round(tmp_path)
    first = approve_all(build_queue(profiles, out))
    (out / "amy.md").write_text("edited plan")
    again = by_id(build_queue(profiles, out, existing=first))
    assert again["person-amy"].status == "pending"
    assert again["person-amy"].text == "edited plan"
    assert again["person-zed"].status == "approved"


def test_rebuild_keeps_posted_even_when_text_changes(tmp_path):
    profiles, out = make_round(tmp_path)
    first = mark_posted(approve(build_queue(profiles, out), ["person-amy"]), "person-amy")
    (out / "amy.md").write_text("edited plan")
    again = by_id(build_queue(profiles, out, existing=first))
    assert again["person-amy"].status == "posted"


def test_approve_marks_only_the_named_posts(tmp_path):
    profiles, out = make_round(tmp_path)
    result = by_id(approve(build_queue(profiles, out), ["person-zed"]))
    assert result["person-zed"].status == "approved"
    assert result["person-amy"].status == "pending"


def test_approve_unknown_id_raises_value_error(tmp_path):
    profiles, out = make_round(tmp_path)
    with pytest.raises(ValueError, match="person-nobody"):
        approve(build_queue(profiles, out), ["person-nobody"])


def test_approve_is_idempotent(tmp_path):
    profiles, out = make_round(tmp_path)
    once = approve(build_queue(profiles, out), ["scoreboard"])
    assert approve(once, ["scoreboard"]) == once


def test_approve_does_not_change_a_posted_post(tmp_path):
    profiles, out = make_round(tmp_path)
    posted = mark_posted(approve(build_queue(profiles, out), ["scoreboard"]), "scoreboard")
    assert by_id(approve(posted, ["scoreboard"]))["scoreboard"].status == "posted"
    assert by_id(approve_all(posted))["scoreboard"].status == "posted"


def test_next_returns_the_first_approved_post_and_never_a_pending_one(tmp_path):
    profiles, out = make_round(tmp_path)
    posts = approve(build_queue(profiles, out), ["person-zed", "movers"])
    assert next_post(posts).id == "person-zed"
    posts = mark_posted(posts, "person-zed")
    assert next_post(posts).id == "movers"


def test_next_is_none_when_nothing_is_approved(tmp_path):
    profiles, out = make_round(tmp_path)
    assert next_post(build_queue(profiles, out)) is None


def test_mark_posted_requires_approved(tmp_path):
    profiles, out = make_round(tmp_path)
    with pytest.raises(ValueError, match="person-amy"):
        mark_posted(build_queue(profiles, out), "person-amy")


def test_mark_posted_twice_raises_value_error(tmp_path):
    profiles, out = make_round(tmp_path)
    posts = mark_posted(approve(build_queue(profiles, out), ["person-amy"]), "person-amy")
    with pytest.raises(ValueError, match="person-amy"):
        mark_posted(posts, "person-amy")


def test_pure_functions_do_not_edit_in_place(tmp_path):
    profiles, out = make_round(tmp_path)
    posts = build_queue(profiles, out)
    approve_all(posts)
    assert {p.status for p in posts} == {"pending"}


def test_save_then_load_round_trips(tmp_path):
    profiles, out = make_round(tmp_path)
    posts = approve(build_queue(profiles, out), ["scoreboard"])
    path = out / QUEUE_FILE
    save_queue(path, posts)
    assert load_queue(path) == posts


@pytest.mark.parametrize(
    "content",
    ["", "{not json", '{"a": 1}', "[1]", '[{"id": "x"}]', '[{"id": "x", "kind": "person", "handle": null, "text": "t", "status": "pending", "extra": 1}]'],
)
def test_a_queue_file_that_is_not_a_queue_raises_a_message_naming_the_file(tmp_path, content):
    path = tmp_path / QUEUE_FILE
    path.write_text(content)

    with pytest.raises(ValueError) as info:
        load_queue(path)

    assert str(path) in str(info.value)
    assert "Delete it" in str(info.value)
    assert "forgets which drafts were posted" in str(info.value)


def test_saving_replaces_the_file_in_one_step_and_leaves_no_temporary_file(tmp_path):
    path = tmp_path / QUEUE_FILE
    path.write_text("old contents")
    inode_before = path.stat().st_ino

    save_queue(path, [Post("scoreboard", "scoreboard", None, "text", "pending")])

    assert [p.name for p in tmp_path.iterdir()] == [QUEUE_FILE]
    assert path.stat().st_ino != inode_before


def test_a_failed_save_leaves_the_old_queue_intact(tmp_path):
    path = tmp_path / QUEUE_FILE
    save_queue(path, [Post("scoreboard", "scoreboard", None, "text", "pending")])
    before = path.read_text()
    tmp_path.chmod(0o555)
    try:
        with pytest.raises(OSError):
            save_queue(path, [Post("scoreboard", "scoreboard", None, "changed", "approved")])
    finally:
        tmp_path.chmod(0o755)

    assert path.read_text() == before


def build_cli(tmp_path: Path):
    profiles, out = make_round(tmp_path)
    code = queue_cli.main(["build", "--profiles", str(profiles), "--out", str(out)])
    assert code == 0
    return profiles, out


def test_cli_build_then_list_prints_one_line_per_post(tmp_path, capsys):
    _, out = build_cli(tmp_path)
    capsys.readouterr()
    assert queue_cli.main(["list", "--out", str(out)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines == [
        "person-amy pending",
        "person-zed pending",
        "scoreboard pending",
        "movers pending",
    ]


def test_cli_next_prints_the_text_of_the_next_approved_post(tmp_path, capsys):
    _, out = build_cli(tmp_path)
    queue_cli.main(["approve", "--out", str(out), "person-zed"])
    capsys.readouterr()
    assert queue_cli.main(["next", "--out", str(out)]) == 0
    assert capsys.readouterr().out.strip() == "plan for zed"


def test_cli_next_prints_nothing_and_exits_1_when_none_is_approved(tmp_path, capsys):
    _, out = build_cli(tmp_path)
    capsys.readouterr()
    assert queue_cli.main(["next", "--out", str(out)]) == 1
    assert capsys.readouterr().out == ""


def test_cli_mark_posted_updates_the_queue_file(tmp_path):
    _, out = build_cli(tmp_path)
    queue_cli.main(["approve", "--out", str(out), "--all"])
    assert queue_cli.main(["mark-posted", "--out", str(out), "person-amy"]) == 0
    saved = by_id(load_queue(out / QUEUE_FILE))
    assert saved["person-amy"].status == "posted"
    assert saved["person-zed"].status == "approved"


def test_cli_missing_queue_file_exits_with_message(tmp_path):
    with pytest.raises(SystemExit) as info:
        queue_cli.main(["list", "--out", str(tmp_path)])
    assert QUEUE_FILE in str(info.value)
