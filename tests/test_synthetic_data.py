import json
import re
from pathlib import Path

import pytest

PROFILES_DIR = Path("synthetic-data/profiles")
BAIT_PATH = Path("synthetic-data/bait.json")
CONTRACT_KEYS = {
    "handle",
    "display_name",
    "console",
    "pto_status",
    "spouse_risk",
    "preordered",
    "weakness",
    "raw_reply",
}
# Copied from docs/contracts.md until slice 1's war_room.profiles.HANDLE_RE lands.
HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
BAIT_HANDLES = ("mara", "otto")


def load_profiles() -> list[dict]:
    paths = sorted(PROFILES_DIR.glob("*.json"))
    assert paths, f"no profiles in {PROFILES_DIR}"
    return [json.loads(p.read_text()) for p in paths]


def test_crew_has_four_or_five_people():
    assert 4 <= len(load_profiles()) <= 5


@pytest.mark.parametrize("profile", load_profiles(), ids=lambda p: p["handle"])
def test_every_synthetic_profile_matches_the_contract_keys(profile):
    assert set(profile) == CONTRACT_KEYS
    assert profile["spouse_risk"] is None or profile["spouse_risk"] in range(1, 6)
    assert profile["preordered"] in (True, False, None)
    assert isinstance(profile["raw_reply"], str) and profile["raw_reply"]


@pytest.mark.parametrize("profile", load_profiles(), ids=lambda p: p["handle"])
def test_every_synthetic_handle_matches_handle_re(profile):
    assert HANDLE_RE.match(profile["handle"])
    assert (PROFILES_DIR / f"{profile['handle']}.json").exists()


def test_bait_file_names_substrings_present_in_the_bait_profiles():
    substrings = json.loads(BAIT_PATH.read_text())["forbidden_substrings"]
    assert substrings
    bait_text = " ".join(
        json.loads((PROFILES_DIR / f"{h}.json").read_text())["raw_reply"]
        for h in BAIT_HANDLES
    ).lower()
    for s in substrings:
        assert s.lower() in bait_text, s
