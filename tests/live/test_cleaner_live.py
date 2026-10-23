import json
from pathlib import Path

import pytest

from create_cleaner import ask_cleaner, make_client

pytestmark = pytest.mark.live

# The channel FAQ facts, used until slice 3's launch-facts.md lands.
FAQ_FACTS = """\
- Release date: November 19, 2026 (source: channel FAQ)
- Platforms at launch: PlayStation 5 and Xbox Series X|S; no PC date announced (source: channel FAQ)
- Pre-orders opened June 25, 2026 (source: channel FAQ)
- Digital editions: PlayStation Store and Microsoft Store (source: channel FAQ)
- Price, special editions, and pre-order bonuses: UNCONFIRMED as of August (source: channel FAQ)
- Thanksgiving is one week after launch (source: channel FAQ)
"""


def facts_text() -> str:
    path = Path("synthetic-data/launch-facts.md")
    return path.read_text() if path.exists() else FAQ_FACTS


@pytest.fixture(scope="module")
def cleaner():
    ids_path, env_path = Path(".specialist_ids.json"), Path(".environment_id")
    if not env_path.exists():
        pytest.fail("Missing .environment_id. Run setup_environment.py first.")
    if not ids_path.exists() or "cleaner" not in json.loads(ids_path.read_text()):
        pytest.fail("No cleaner id in .specialist_ids.json. Run create_cleaner.py first.")
    return (
        make_client(),
        json.loads(ids_path.read_text())["cleaner"],
        env_path.read_text().strip(),
    )


def test_bad_draft_gets_fix_verdict(cleaner):
    reply = ask_cleaner(*cleaner, Path("synthetic-data/bad-draft.md").read_text(), facts_text())
    assert reply.startswith("VERDICT: FIX"), reply


def test_good_draft_gets_pass_verdict(cleaner):
    reply = ask_cleaner(*cleaner, Path("synthetic-data/good-draft.md").read_text(), facts_text())
    assert reply.startswith("VERDICT: PASS"), reply
