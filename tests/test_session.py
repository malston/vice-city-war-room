from pathlib import Path
from types import SimpleNamespace

import pytest

from war_room.session import EventPrinter, safe_output_path


def text_event(text):
    return SimpleNamespace(
        type="agent.message", content=[SimpleNamespace(type="text", text=text)]
    )


def test_event_line_starts_on_a_new_line_after_agent_text(capsys):
    printer = EventPrinter()
    printer.handle(text_event("Waiting on their reports."))
    printer.handle(SimpleNamespace(type="agent.thread_message_received", from_agent_name="The Fixer"))
    out = capsys.readouterr().out
    assert out == "Waiting on their reports.\n  [reply <-]         The Fixer\n"


def test_event_line_after_text_ending_in_newline_adds_no_blank_line(capsys):
    printer = EventPrinter()
    printer.handle(text_event("Done.\n"))
    printer.handle(SimpleNamespace(type="session.thread_created", agent_name="The Wheelman"))
    assert capsys.readouterr().out == "Done.\n  [thread spawned]   The Wheelman\n"


def test_consecutive_event_lines_have_no_blank_lines_between(capsys):
    printer = EventPrinter()
    printer.handle(SimpleNamespace(type="session.thread_created", agent_name="The Fixer"))
    printer.handle(SimpleNamespace(type="agent.thread_message_sent", to_agent_name="The Fixer"))
    assert capsys.readouterr().out == (
        "  [thread spawned]   The Fixer\n  [delegate ->]      The Fixer\n"
    )


def test_agent_text_is_collected_for_the_transcript(capsys):
    printer = EventPrinter()
    printer.handle(text_event("one "))
    printer.handle(text_event("two"))
    assert "".join(printer.parts) == "one two"


def test_idle_event_finishes_and_other_events_do_not(capsys):
    printer = EventPrinter()
    assert printer.handle(text_event("hi")) is False
    assert printer.handle(SimpleNamespace(type="session.status_idle")) is True
    assert "[swarm finished]" in capsys.readouterr().out


def test_tool_use_label_names_the_tool(capsys):
    printer = EventPrinter()
    printer.handle(SimpleNamespace(type="agent.tool_use", name="bash"))
    assert capsys.readouterr().out == "  [tool: bash]\n"


def test_strips_directories_from_filename(tmp_path):
    assert safe_output_path(tmp_path, "../../x.md") == tmp_path / "x.md"


def test_plain_filename_unchanged(tmp_path):
    assert safe_output_path(tmp_path, "mara.md") == tmp_path / "mara.md"


def test_empty_filename_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        safe_output_path(tmp_path, "")


@pytest.mark.parametrize("name", [".", "..", "../", "a/.."])
def test_dot_names_raise_value_error(tmp_path, name):
    with pytest.raises(ValueError):
        safe_output_path(tmp_path, name)


def test_backslash_traversal_is_stripped(tmp_path):
    assert safe_output_path(tmp_path, "..\\..\\x.md") == tmp_path / "x.md"


def test_absolute_path_is_stripped(tmp_path):
    assert safe_output_path(tmp_path, "/etc/passwd") == tmp_path / "passwd"
