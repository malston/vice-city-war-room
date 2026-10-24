"""The docs people read stay true: links resolve, commands exist, and nothing is left undocumented.

Covers the README and the pages under docs/. The design and the plan under docs/superpowers/
are a record of how the project was built, so they are not checked.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC_PATHS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
DOC_IDS = [path.relative_to(ROOT).as_posix() for path in DOC_PATHS]
ALL_DOCS_TEXT = "\n".join(path.read_text() for path in DOC_PATHS)

MAKEFILE = (ROOT / "Makefile").read_text()
MAKE_TARGETS = set(re.findall(r"^([a-z][a-z-]*):", MAKEFILE, re.MULTILINE))
SCRIPTS = sorted(path.name for path in ROOT.glob("*.py"))

LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
MAKE_COMMAND = re.compile(r"\bmake ([a-z][a-z-]*)\b")
PYTHON_COMMAND = re.compile(r"\bpython3? ((?:[\w./-]+/)?[\w-]+\.py)\b([^\n`]*)")
FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z-]*)")


def code_text(text: str) -> str:
    """Only what is inside code fences and inline code, where commands live."""
    fenced = re.findall(r"```.*?\n(.*?)```", text, re.DOTALL)
    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return "\n".join(fenced + re.findall(r"`([^`\n]+)`", without_fences))


@pytest.mark.parametrize("doc", DOC_PATHS, ids=DOC_IDS)
def test_relative_links_resolve(doc):
    broken = []
    for target in LINK.findall(doc.read_text()):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (doc.parent / target.split("#")[0]).exists():
            broken.append(target)

    assert broken == []


@pytest.mark.parametrize("doc", DOC_PATHS, ids=DOC_IDS)
def test_make_targets_named_in_the_docs_exist(doc):
    named = set(MAKE_COMMAND.findall(code_text(doc.read_text())))

    assert named - MAKE_TARGETS == set()


@pytest.mark.parametrize("doc", DOC_PATHS, ids=DOC_IDS)
def test_scripts_named_in_the_docs_exist(doc):
    named = {script for script, _ in PYTHON_COMMAND.findall(code_text(doc.read_text()))}

    assert [script for script in named if not (ROOT / script).exists()] == []


@pytest.mark.parametrize("doc", DOC_PATHS, ids=DOC_IDS)
def test_flags_used_in_the_docs_are_real(doc):
    unknown = []
    for script, rest in PYTHON_COMMAND.findall(code_text(doc.read_text())):
        path = ROOT / script
        if not path.exists():
            continue
        source = path.read_text()
        unknown += [f"{script} {flag}" for flag in FLAG.findall(rest) if f'"{flag}"' not in source]

    assert unknown == []


def test_the_checks_above_have_something_to_check():
    code = code_text(ALL_DOCS_TEXT)

    assert len(MAKE_TARGETS) >= 6
    assert set(MAKE_COMMAND.findall(code)) >= {"crew-setup", "ui"}
    assert len(PYTHON_COMMAND.findall(code)) >= 10
    assert len(FLAG.findall(code)) >= 10
    assert len(LINK.findall(ALL_DOCS_TEXT)) >= 10


@pytest.mark.parametrize("target", sorted(MAKE_TARGETS - {"help"}))
def test_readme_documents_every_make_target(target):
    assert re.search(rf"make {target}(?![a-z-])", (ROOT / "README.md").read_text())


@pytest.mark.parametrize("script", SCRIPTS)
def test_every_script_is_mentioned_in_the_docs(script):
    assert script in ALL_DOCS_TEXT


def linked_from_readme() -> set[Path]:
    readme = ROOT / "README.md"
    return {
        (readme.parent / target.split("#")[0]).resolve()
        for target in LINK.findall(readme.read_text())
        if not target.startswith(("http://", "https://", "mailto:", "#"))
    }


def test_every_page_under_docs_is_linked_from_the_readme():
    pages = {path.resolve() for path in (ROOT / "docs").rglob("*") if path.suffix in {".md", ".html"}}

    assert sorted(path.relative_to(ROOT).as_posix() for path in pages - linked_from_readme()) == []


def test_the_files_that_shape_what_the_crew_says_are_linked_from_the_readme():
    editable = {
        ROOT / "synthetic-data" / "launch-facts.md",
        ROOT / "demo" / "seed-round-1.json",
        *(ROOT / "skills").glob("*/SKILL.md"),
    }

    missing = {path.resolve() for path in editable} - linked_from_readme()

    assert sorted(path.relative_to(ROOT).as_posix() for path in missing) == []
