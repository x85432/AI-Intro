from handoff.detector import detect
from handoff.fakes import FAKE_FILES, FAKE_HITS
from handoff.models import KINDS, SourceFile


def keys(hits):
    return {(h.file, h.line, h.kind) for h in hits}


def kinds(hits):
    return {h.kind for h in hits}


def test_fake_files_contain_the_expected_hits():
    got = keys(detect(FAKE_FILES))
    for hit in FAKE_HITS:
        assert (hit.file, hit.line, hit.kind) in got


def test_hits_are_well_formed():
    lines = {f.path: f.text.splitlines() for f in FAKE_FILES}
    for hit in detect(FAKE_FILES):
        assert hit.kind in KINDS
        assert 1 <= hit.line <= len(lines[hit.file])
        assert hit.snippet in lines[hit.file][hit.line - 1]


def test_empty_input_and_empty_file():
    assert detect([]) == []
    assert detect([SourceFile(path="a.py", text="")]) == []


def test_syntax_error_falls_back_to_text_matching():
    broken = SourceFile(path="broken.py", text="def f(:\n    time.sleep(1)\n    open('x.json')\n")
    got = keys(detect([broken]))
    assert ("broken.py", 2, "simulation") in got
    assert ("broken.py", 3, "boundary") in got


def test_fixture_file_is_found_by_path():
    hits = detect([SourceFile(path="examples/stream_demo/fixtures/readings.json", text="[]")])
    assert kinds(hits) == {"fixture"}
    assert detect([SourceFile(path="config/settings.json", text="{}")]) == []


def test_non_python_text_is_not_parsed():
    assert detect([SourceFile(path="notes.md", text="time.sleep(1)\nopen('x')")]) == []


def test_mock_and_fixture_decorators():
    text = (
        "import pytest\n"
        "from unittest.mock import patch\n"
        "\n"
        "@pytest.fixture\n"
        "def client():\n"
        "    return object()\n"
        "\n"
        "@patch('app.send')\n"
        "def test_it(send):\n"
        "    assert send\n"
    )
    got = keys(detect([SourceFile(path="test_app.py", text=text)]))
    assert ("test_app.py", 2, "mock") in got
    assert ("test_app.py", 4, "fixture") in got
    assert ("test_app.py", 8, "mock") in got


def test_sample_data_stub_and_yield_simulation():
    text = (
        "ROWS = [{'v': 1}, {'v': 2}]\n"
        "\n"
        "def read():\n"
        "    pass\n"
        "\n"
        "def stream():\n"
        "    for r in ROWS:\n"
        "        yield r\n"
    )
    got = keys(detect([SourceFile(path="m.py", text=text)]))
    assert ("m.py", 1, "sample_data") in got
    assert ("m.py", 3, "stub") in got
    assert ("m.py", 7, "simulation") in got


def test_network_and_socket_boundaries():
    text = (
        "import requests\n"
        "r = requests.get('http://x')\n"
        "data = sock.recv(1024)\n"
    )
    got = keys(detect([SourceFile(path="net.py", text=text)]))
    assert ("net.py", 2, "boundary") in got
    assert ("net.py", 3, "boundary") in got


def test_output_is_sorted_and_deduplicated():
    hits = detect(FAKE_FILES + FAKE_FILES)
    ordered = [(h.file, h.line, h.kind) for h in hits]
    assert ordered == sorted(set(ordered))
