import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path], cwd=REPO_ROOT, check=False
    )
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".envrc",
        ".skill_ids.json",
        "profiles/mara.json",
        "outputs/round-1/scoreboard.md",
    ],
)
def test_real_data_and_secrets_are_ignored(path):
    assert is_ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        "synthetic-data/profiles/jules.json",
        "docs/outputs/example.md",
        "docs/contracts.md",
    ],
)
def test_committed_files_are_not_ignored(path):
    assert not is_ignored(path)
