"""
Build the round message the Mastermind receives.

One session covers every profile: the scoreboard needs everyone, and one
coordinator fans the work out to the specialists in parallel.
"""

from pathlib import Path


MAX_PROFILES = 8
DEFAULT_FACTS = Path("synthetic-data/launch-facts.md")


def _document(name: str, text: str) -> str:
    return f"=====  DOCUMENT: {name}  =====\n{text}"


def build_user_message(
    round_n: int,
    profiles_dir: Path,
    facts_path: Path,
    prior_scoreboard: Path | None = None,
    force: bool = False,
) -> str:
    profile_paths = sorted(Path(profiles_dir).glob("*.json"))
    if not profile_paths:
        raise ValueError(f"No profiles found in {profiles_dir}")
    if len(profile_paths) > MAX_PROFILES and not force:
        raise ValueError(
            f"{len(profile_paths)} profiles is more than the limit of "
            f"{MAX_PROFILES}. Pass --force to run anyway."
        )
    facts_path = Path(facts_path)
    if not facts_path.exists():
        raise FileNotFoundError(f"Facts file not found: {facts_path}")

    handles = [p.stem for p in profile_paths]
    files = "\n".join(f"- {h}.md" for h in handles)

    intro = (
        f"Launch plan round {round_n} is starting. Please run the standard "
        "War Room process:\n"
        "1. Give each person a codename.\n"
        "2. Delegate every profile to all four specialists, in parallel.\n"
        "3. Write one file per person, named <handle>.md, plus scoreboard.md "
        "with the team ranking.\n"
        "4. State only facts that appear in launch-facts.md; call anything "
        "else unconfirmed.\n\n"
        f"Write these files:\n{files}\n- scoreboard.md\n"
    )

    blocks = [_document("launch-facts.md", facts_path.read_text())]
    blocks += [_document(p.name, p.read_text()) for p in profile_paths]
    if prior_scoreboard is not None:
        prior = Path(prior_scoreboard)
        blocks.append(_document(f"prior-{prior.name}", prior.read_text()))

    return intro + "\n" + "\n\n".join(blocks)
