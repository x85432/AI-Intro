"""② Find where outside data enters the code, and where mocks live. No AI here.
Owner: 鄧皓澤 Daniel."""

from __future__ import annotations

import ast
import re

from .models import MockHit, SourceFile

# A path containing one of these words, with one of these extensions, is a fixture file.
FIXTURE_PATH_WORDS = ("mock", "fake", "fixture", "sample")
FIXTURE_EXTENSIONS = (".json", ".csv")

# Calls that read data from outside the program.
BOUNDARY_CALLS = {
    "open", "json.load", "json.loads", "csv.reader", "csv.DictReader",
    "pd.read_csv", "pandas.read_csv", "pd.read_json", "pandas.read_json",
}
BOUNDARY_PREFIXES = ("requests.", "httpx.", "urllib.", "socket.")
BOUNDARY_METHODS = {"recv", "recvfrom", "recv_into"}

MOCK_CALLS = {"patch", "Mock", "MagicMock", "AsyncMock"}

# Text patterns used when a file cannot be parsed (syntax error).
FALLBACK_PATTERNS = [
    ("simulation", re.compile(r"\bsleep\s*\(|\byield\b")),
    ("mock", re.compile(r"unittest\.mock|\bpatch\s*\(|\bMagicMock\b|\bMock\s*\(")),
    ("fixture", re.compile(r"@\s*(pytest\.)?fixture\b")),
    ("boundary", re.compile(r"\bopen\s*\(|json\.load|csv\.|requests\.|\.recv\s*\(")),
    ("sample_data", re.compile(r"^[A-Za-z_]\w*\s*=\s*[\[{(]")),
]


def detect(files: list[SourceFile]) -> list[MockHit]:
    """Return hints for ③: one MockHit per data boundary or mock found.

    Input:  the kept files from ①.
    Output: MockHit(file, line, snippet, kind) with kind one of models.KINDS.
    Rule-based (Python `ast`; fall back to text matching on syntax errors).
    Prefer finding too much over missing something: ③ also reads the full files.
    Test against handoff.fakes.FAKE_FILES (expected hits: handoff.fakes.FAKE_HITS).
    """
    hits: dict[tuple[str, int, str], MockHit] = {}
    for f in files:
        for hit in _detect_file(f):
            hits.setdefault((hit.file, hit.line, hit.kind), hit)
    return sorted(hits.values(), key=lambda h: (h.file, h.line, h.kind))


def _detect_file(f: SourceFile) -> list[MockHit]:
    lines = f.text.splitlines()
    found: list[MockHit] = []

    def add(line: int, kind: str) -> None:
        snippet = lines[line - 1].strip() if 1 <= line <= len(lines) else ""
        found.append(MockHit(file=f.path, line=line, snippet=snippet, kind=kind))

    lowered = f.path.lower()
    if lowered.endswith(FIXTURE_EXTENSIONS) and any(w in lowered for w in FIXTURE_PATH_WORDS):
        add(1, "fixture")

    if not lowered.endswith(".py"):
        return found

    try:
        tree = ast.parse(f.text)
    except (SyntaxError, ValueError):
        for number, text in enumerate(lines, start=1):
            for kind, pattern in FALLBACK_PATTERNS:
                if pattern.search(text):
                    add(number, kind)
        return found

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)) and _loop_is_simulation(node):
            add(node.lineno, "simulation")
        elif isinstance(node, ast.Call):
            name = _dotted_name(node.func)
            if _is_boundary_call(name):
                add(node.lineno, "boundary")
            if name.split(".")[-1] in MOCK_CALLS:
                add(node.lineno, "mock")
        elif isinstance(node, ast.Import):
            if any(a.name in ("mock", "unittest.mock") for a in node.names):
                add(node.lineno, "mock")
        elif isinstance(node, ast.ImportFrom):
            if node.module in ("mock", "unittest.mock") or (
                    node.module == "unittest" and any(a.name == "mock" for a in node.names)):
                add(node.lineno, "mock")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                last = _dotted_name(target).split(".")[-1]
                if last == "fixture":
                    add(decorator.lineno, "fixture")
                elif last == "patch":
                    add(decorator.lineno, "mock")
            if _is_stub(node):
                add(node.lineno, "stub")

    for node in tree.body:
        if _is_sample_data(node):
            add(node.lineno, "sample_data")

    return found


def _dotted_name(node: ast.AST) -> str:
    """`json.load` -> "json.load", `self.sock.recv` -> "self.sock.recv", else ""."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _is_boundary_call(name: str) -> bool:
    return (name in BOUNDARY_CALLS
            or name.startswith(BOUNDARY_PREFIXES)
            or name.split(".")[-1] in BOUNDARY_METHODS)


def _loop_is_simulation(loop: ast.AST) -> bool:
    for node in ast.walk(loop):
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(node, ast.Call) and _dotted_name(node.func).split(".")[-1] == "sleep":
            return True
    return False


def _is_stub(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = func.body
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]  # skip the docstring
    if len(body) != 1:
        return not body  # a function with only a docstring
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) \
            and stmt.value.value is Ellipsis:
        return True
    if isinstance(stmt, ast.Return) and stmt.value is not None:
        return _is_literal(stmt.value)
    return False


def _is_sample_data(node: ast.stmt) -> bool:
    if isinstance(node, ast.Assign):
        value = node.value
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        value = node.value
    else:
        return False
    return isinstance(value, (ast.List, ast.Dict, ast.Tuple)) and bool(
        getattr(value, "elts", None) or getattr(value, "keys", None)) and _is_literal(value)


def _is_literal(node: ast.AST) -> bool:
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True
