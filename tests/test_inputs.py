from io import BytesIO
from pathlib import Path

import pytest

from handoff import inputs
from handoff.models import SourceFile


def test_collect_reads_nested_files_sorted_without_duplicates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "nested").mkdir()
    (tmp_path / "z.py").write_text("print('hello')\n", encoding="utf-8", newline="\n")
    (tmp_path / "nested" / "a.txt").write_text("中文\n", encoding="utf-8", newline="\n")

    result = inputs.collect(["z.py", ".", "nested/a.txt"])

    assert result == [
        SourceFile("nested/a.txt", "中文\n"),
        SourceFile("z.py", "print('hello')\n"),
    ]


def test_collect_accepts_bom_and_empty_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bom.txt").write_bytes(b"\xef\xbb\xbfhello\r\n")
    (tmp_path / "empty.py").touch()

    assert inputs.collect(["."]) == [
        SourceFile("bom.txt", "hello\r\n"),
        SourceFile("empty.py", ""),
    ]


def test_collect_empty_inputs_and_empty_directory(tmp_path):
    assert inputs.collect([]) == []
    assert inputs.collect([str(tmp_path)]) == []


def test_collect_rejects_missing_explicit_path(tmp_path):
    missing = tmp_path / "missing.py"
    with pytest.raises(FileNotFoundError, match="Input path does not exist"):
        inputs.collect([str(missing)])


def test_collect_rejects_empty_path_string():
    with pytest.raises(ValueError, match="empty strings"):
        inputs.collect([""])


@pytest.mark.parametrize("name", [".git", ".venv", "venv", "env", "__pycache__"])
@pytest.mark.parametrize("explicit_file", [False, True])
def test_collect_skips_excluded_directories(
    tmp_path, monkeypatch, capsys, name, explicit_file
):
    monkeypatch.chdir(tmp_path)
    excluded = tmp_path / name
    excluded.mkdir()
    hidden = excluded / "hidden.py"
    hidden.write_text("hidden", encoding="utf-8")
    (tmp_path / "keep.py").write_text("keep", encoding="utf-8")

    paths = [str(hidden)] if explicit_file else ["."]
    assert inputs.collect(paths) == ([] if explicit_file else [SourceFile("keep.py", "keep")])
    assert name in capsys.readouterr().err


@pytest.mark.parametrize("explicit_file", [False, True])
def test_collect_recognizes_custom_virtual_environment(
    tmp_path, monkeypatch, capsys, explicit_file
):
    monkeypatch.chdir(tmp_path)
    environment = tmp_path / "custom-environment"
    environment.mkdir()
    (environment / "pyvenv.cfg").write_text("home = python", encoding="utf-8")
    source = environment / "library.py"
    source.write_text("not project code", encoding="utf-8")

    assert inputs.collect([str(source) if explicit_file else "."]) == []
    assert "virtual environment" in capsys.readouterr().err


def test_collect_skips_git_worktree_marker_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").write_text("gitdir: /other/worktree", encoding="utf-8")

    assert inputs.collect(["."]) == []
    assert ".git" in capsys.readouterr().err


@pytest.mark.parametrize("data", [b"\x89PNG\r\n\x1a\n", b"hello\x00world", b"data\x01", b"\xff"])
def test_collect_skips_binary_and_non_utf8_files(tmp_path, capsys, data):
    source = tmp_path / "binary.bin"
    source.write_bytes(data)

    assert inputs.collect([str(source)]) == []
    assert "binary" in capsys.readouterr().err


def test_collect_size_limit_inclusive_and_adjustable(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(inputs, "MAX_FILE_SIZE", 8)
    (tmp_path / "at-limit.txt").write_bytes(b"a" * 8)
    (tmp_path / "too-large.txt").write_bytes(b"a" * 9)

    assert inputs.collect(["."]) == [SourceFile("at-limit.txt", "a" * 8)]
    assert "too-large.txt" in capsys.readouterr().err


def test_collect_skips_file_that_grows_after_size_check(tmp_path, monkeypatch, capsys):
    source = tmp_path / "growing.txt"
    source.touch()
    monkeypatch.setattr(inputs, "MAX_FILE_SIZE", 8)
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: BytesIO(b"x" * 9))

    assert inputs.collect([str(source)]) == []
    assert "larger than 8 bytes" in capsys.readouterr().err


def test_collect_reports_read_failure_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "blocked.py").write_text("blocked", encoding="utf-8")
    (tmp_path / "readable.py").write_text("readable", encoding="utf-8")
    original_open = Path.open

    def deny_one_file(path, *args, **kwargs):
        if path.name == "blocked.py":
            raise PermissionError("permission denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_one_file)

    assert inputs.collect(["."]) == [SourceFile("readable.py", "readable")]
    assert "permission denied" in capsys.readouterr().err


def test_collect_reports_directory_failure_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "blocked").mkdir()
    (tmp_path / "keep.py").write_text("keep", encoding="utf-8")
    original_iterdir = Path.iterdir

    def deny_one_directory(path):
        if path.name == "blocked":
            raise PermissionError("cannot list directory")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", deny_one_directory)

    assert inputs.collect(["."]) == [SourceFile("keep.py", "keep")]
    assert "cannot list directory" in capsys.readouterr().err


def test_collect_uses_absolute_paths_for_external_files(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    external = tmp_path / "external.py"
    external.write_text("outside", encoding="utf-8")
    monkeypatch.chdir(project)

    assert inputs.collect([str(external)]) == [SourceFile(external.as_posix(), "outside")]


def test_collect_leaves_sensitive_detection_to_filters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Synthetic fixture: this is deliberately not an actual credential.
    (tmp_path / ".env").write_text("API_KEY=synthetic-test-value", encoding="utf-8")

    assert inputs.collect(["."]) == [SourceFile(".env", "API_KEY=synthetic-test-value")]


@pytest.mark.parametrize("directory", [False, True])
def test_collect_skips_symbolic_links(tmp_path, monkeypatch, capsys, directory):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "target"
    if directory:
        target.mkdir()
        (target / "file.py").write_text("target", encoding="utf-8")
    else:
        target.write_text("target", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"Symbolic links unavailable on this system: {error}")

    assert inputs.collect([str(link)]) == []
    assert "symbolic link" in capsys.readouterr().err
