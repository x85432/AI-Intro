from dataclasses import replace
import os
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import Mock, call

import pytest

from handoff import cli, inputs
from handoff.fakes import FAKE_RESULT
from handoff.models import DraftResult, MockHit, SourceFile


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """Use real file collection, with all unfinished modules replaced."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "code.py").write_text("print('demo')", encoding="utf-8")
    pipeline = Mock()
    pipeline.collect = Mock(wraps=inputs.collect)
    pipeline.split_sensitive.side_effect = lambda files: (files, [])
    pipeline.detect.side_effect = lambda files: [
        MockHit(files[0].path, 1, files[0].text, "boundary")
    ]
    pipeline.draft.return_value = DraftResult(
        items=[replace(FAKE_RESULT.items[0], file="src/code.py", line=1)]
    )
    monkeypatch.setattr(cli.inputs, "collect", pipeline.collect)
    monkeypatch.setattr(cli.filters, "split_sensitive", pipeline.split_sensitive)
    monkeypatch.setattr(cli.detector, "detect", pipeline.detect)
    monkeypatch.setattr(cli.drafter, "draft", pipeline.draft)
    monkeypatch.setattr(cli.writer, "write", pipeline.write)
    monkeypatch.setattr(cli.writer, "mark", pipeline.mark)
    return pipeline


def test_scan_defaults_preserve_pipeline_order_and_paths(pipeline, capsys):
    assert cli.main(["scan", "src"]) is None

    files = [SourceFile("src/code.py", "print('demo')")]
    hits = [MockHit("src/code.py", 1, "print('demo')", "boundary")]
    assert pipeline.mock_calls == [
        call.collect(["src"]),
        call.split_sensitive(files),
        call.detect(files),
        call.draft(files, hits, spec=None, fake=False),
        call.write(pipeline.draft.return_value, "HANDOFF.md", scope=["src/code.py"]),
    ]
    assert pipeline.draft.return_value.items[0].file == files[0].path == hits[0].file
    output = capsys.readouterr()
    assert "Read 1 text file(s)" in output.out
    assert "Wrote 1 item(s) to HANDOFF.md" in output.out
    assert not output.err


def test_scan_fake_still_filters_and_passes_only_kept_files(pipeline, tmp_path, capsys):
    (tmp_path / ".env").write_text("synthetic-test-value", encoding="utf-8")
    pipeline.split_sensitive.side_effect = lambda files: (
        [source for source in files if source.path != ".env"], [".env"]
    )

    cli.main(["scan", ".", "--fake"])

    assert len(pipeline.split_sensitive.call_args.args[0]) == 2
    kept = [SourceFile("src/code.py", "print('demo')")]
    pipeline.detect.assert_called_once_with(kept)
    assert pipeline.draft.call_args.args[0] == kept
    assert pipeline.draft.call_args.kwargs == {"spec": None, "fake": True}
    assert pipeline.write.call_args.kwargs == {"scope": ["src/code.py"]}
    assert "Skipped .env: sensitive file" in capsys.readouterr().err


def test_scan_spec_and_output_arguments(pipeline, tmp_path):
    (tmp_path / "spec.md").write_bytes("規格\n".encode("utf-8"))

    cli.main(["scan", "src", "--spec", "spec.md", "-o", "review.md", "--fake"])

    assert pipeline.collect.call_args_list == [call(["spec.md"]), call(["src"])]
    assert pipeline.draft.call_args.kwargs == {"spec": "規格\n", "fake": True}
    assert pipeline.write.call_args == call(
        pipeline.draft.return_value, "review.md", scope=["src/code.py"]
    )


def test_scan_accepts_empty_spec_in_fake_mode(pipeline, tmp_path):
    (tmp_path / "spec.md").touch()

    cli.main(["scan", "src", "--spec", "spec.md", "--fake"])

    assert pipeline.draft.call_args.kwargs["spec"] == ""


def test_scan_blocks_unvalidated_spec_before_real_drafting(pipeline, tmp_path, capsys):
    (tmp_path / "spec.md").write_text("synthetic spec", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        cli.main(["scan", "src", "--spec", "spec.md"])

    assert error.value.code == 1
    assert pipeline.mock_calls == []
    assert "--spec requires --fake until PR 2" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["missing", "directory", "binary", "oversized"])
def test_scan_rejects_unusable_spec(pipeline, tmp_path, monkeypatch, capsys, kind):
    spec = tmp_path / "spec.md"
    if kind == "directory":
        spec.mkdir()
    elif kind == "binary":
        spec.write_bytes(b"\x00binary")
    elif kind == "oversized":
        monkeypatch.setattr(inputs, "MAX_FILE_SIZE", 8)
        spec.write_bytes(b"x" * 9)

    with pytest.raises(SystemExit) as error:
        cli.main(["scan", "src", "--spec", str(spec), "--fake"])

    assert error.value.code == 1
    pipeline.split_sensitive.assert_not_called()
    pipeline.draft.assert_not_called()
    pipeline.write.assert_not_called()
    assert "--spec" in capsys.readouterr().err


@pytest.mark.parametrize("all_filtered", [False, True])
def test_scan_stops_when_no_files_remain(pipeline, tmp_path, capsys, all_filtered):
    if all_filtered:
        pipeline.split_sensitive.side_effect = lambda files: ([], [files[0].path])
        target = "src"
    else:
        (tmp_path / "empty").mkdir()
        target = "empty"

    with pytest.raises(SystemExit) as error:
        cli.main(["scan", target, "--fake"])

    assert error.value.code == 1
    pipeline.split_sensitive.assert_called_once()
    pipeline.detect.assert_not_called()
    pipeline.draft.assert_not_called()
    pipeline.write.assert_not_called()
    assert "No scannable files" in capsys.readouterr().err


def test_scan_reports_invalid_input_path(pipeline, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["scan", "missing.py", "--fake"])

    assert error.value.code == 1
    pipeline.split_sensitive.assert_not_called()
    pipeline.write.assert_not_called()
    assert "Input path does not exist" in capsys.readouterr().err


@pytest.mark.parametrize("stage", ["split_sensitive", "detect", "draft", "write"])
def test_scan_reports_module_failure_and_stops(pipeline, tmp_path, capsys, stage):
    output = tmp_path / "HANDOFF.md"
    output.write_text("existing handoff", encoding="utf-8")
    getattr(pipeline, stage).side_effect = RuntimeError(f"{stage} failed")

    with pytest.raises(SystemExit) as error:
        cli.main(["scan", "src", "--fake"])

    assert error.value.code == 1
    stages = ["split_sensitive", "detect", "draft", "write"]
    for later_stage in stages[stages.index(stage) + 1:]:
        getattr(pipeline, later_stage).assert_not_called()
    assert output.read_text(encoding="utf-8") == "existing handoff"
    captured = capsys.readouterr()
    assert f"handoff: error: {stage} failed" in captured.err
    assert "Wrote" not in captured.out
    if stage == "draft":
        assert "src/code.py:1 [boundary]" in captured.err


def test_draft_failure_with_no_hits_still_reports_detector_result(pipeline, capsys):
    pipeline.detect.side_effect = None
    pipeline.detect.return_value = []
    pipeline.draft.side_effect = TimeoutError("request timed out")

    with pytest.raises(SystemExit, match="1"):
        cli.main(["scan", "src", "--fake"])

    pipeline.write.assert_not_called()
    assert "None found" in capsys.readouterr().err


@pytest.mark.parametrize("evidence_type", [None, "ask_owner", "inspect_sample", "run_check"])
def test_mark_delegates_human_supplied_arguments(pipeline, capsys, evidence_type):
    argv = ["mark", "A-01", "mismatch", "--evidence", "120 records"]
    if evidence_type is not None:
        argv += ["--type", evidence_type, "-f", "review.md"]

    assert cli.main(argv) is None

    path = "HANDOFF.md" if evidence_type is None else "review.md"
    assert pipeline.mock_calls == [
        call.mark(path, "A-01", "mismatch", "120 records", evidence_type=evidence_type)
    ]
    assert "Marked A-01 as mismatch" in capsys.readouterr().out


def test_mark_reports_writer_errors(pipeline, capsys):
    pipeline.mark.side_effect = ValueError("Unknown item ID: A-99")

    with pytest.raises(SystemExit) as error:
        cli.main(["mark", "A-99", "mismatch", "--evidence", "sample"])

    assert error.value.code == 1
    assert "Unknown item ID" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    [],
    ["unknown"],
    ["scan"],
    ["scan", "src", "--unknown"],
    ["scan", "src", "--spec"],
    ["scan", "src", "-o"],
    ["mark", "A-01", "mismatch"],
    ["mark", "A-01", "invalid", "--evidence", "sample"],
    ["mark", "A-01", "mismatch", "--evidence", "sample", "--type", "invalid"],
])
def test_invalid_arguments_fail_before_pipeline_calls(pipeline, capsys, argv):
    with pytest.raises(SystemExit) as error:
        cli.main(argv)

    assert error.value.code == 2
    assert pipeline.mock_calls == []
    assert "usage:" in capsys.readouterr().err


def test_main_reads_sys_argv_when_not_supplied(pipeline, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["handoff", "scan", "src", "--fake"])

    cli.main()

    pipeline.collect.assert_called_once_with(["src"])
    assert pipeline.draft.call_args.kwargs["fake"] is True


def test_module_entry_calls_cli_main(monkeypatch):
    main = Mock()
    monkeypatch.setattr(cli, "main", main)

    runpy.run_module("handoff", run_name="__main__")

    main.assert_called_once_with()


@pytest.mark.parametrize("args, exit_code", [
    (["--help"], 0),
    (["scan", "--help"], 0),
    (["mark", "--help"], 0),
    ([], 2),
])
def test_python_module_entry(args, exit_code):
    result = subprocess.run(
        [sys.executable, "-m", "handoff", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, encoding="utf-8", check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    assert result.returncode == exit_code
    assert "usage:" in (result.stdout if exit_code == 0 else result.stderr)
    assert "Traceback" not in result.stderr


def test_module_entry_reports_unfinished_filter_without_bypassing(
    pipeline, tmp_path, monkeypatch, capsys
):
    output = tmp_path / "HANDOFF.md"
    pipeline.split_sensitive.side_effect = NotImplementedError("filters.split_sensitive unfinished")
    monkeypatch.setattr(sys, "argv", ["handoff", "scan", "src", "--fake", "-o", str(output)])

    with pytest.raises(SystemExit) as error:
        runpy.run_module("handoff", run_name="__main__")

    assert error.value.code == 1
    pipeline.detect.assert_not_called()
    pipeline.draft.assert_not_called()
    pipeline.write.assert_not_called()
    captured = capsys.readouterr()
    assert "filters.split_sensitive unfinished" in captured.err
    assert "Traceback" not in captured.err
    assert not output.exists()
