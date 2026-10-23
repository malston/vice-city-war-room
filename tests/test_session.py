from pathlib import Path

import pytest

from war_room.session import safe_output_path


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
