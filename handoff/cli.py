"""① Command line entry. Owner: 方騏為 Cactex.

Commands to support (plan §1.1):

    python -m handoff scan PATH... [--spec FILE] [-o HANDOFF.md] [--fake]
    python -m handoff mark A-01 mismatch --evidence "..." [--type inspect_sample] [-f HANDOFF.md]

`scan` runs the pipeline in this order:
    inputs.collect -> filters.split_sensitive -> detector.detect -> drafter.draft -> writer.write
and reports what was read, what was skipped and how many items were written.
`mark` parses its arguments and calls writer.mark (implemented by ④).

PR 1 limitation: --spec content has no sensitive-content validation yet. Until
PR 2 adds that protection, --spec is accepted only with --fake; real drafting
with an unvalidated spec is blocked. Source-file filtering is always delegated
to filters.split_sensitive, including in fake mode. Unfinished modules are
reported as errors, never bypassed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional

from . import detector, drafter, filters, inputs, writer
from .models import STATUSES, VERIFY_TYPES


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handoff", description="Draft a mock-to-real handoff checklist."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="Scan selected files or directories")
    scan.add_argument("paths", nargs="+", metavar="PATH")
    scan.add_argument(
        "--spec", metavar="FILE",
        help="Optional UTF-8 specification; requires --fake until PR 2 adds secret checks",
    )
    scan.add_argument("-o", default="HANDOFF.md", metavar="FILE", help="Output file")
    scan.add_argument("--fake", action="store_true", help="Ask the drafter for fixed data, without an LLM call")

    mark = commands.add_parser("mark", help="Record a human's verification result")
    mark.add_argument("item_id", metavar="ID")
    mark.add_argument("status", choices=STATUSES)
    mark.add_argument("--evidence", required=True, help="Evidence supplied by a human")
    mark.add_argument("--type", dest="evidence_type", choices=VERIFY_TYPES)
    mark.add_argument("-f", dest="path", default="HANDOFF.md", metavar="FILE")
    return parser


def _scan(args: argparse.Namespace) -> None:
    if args.spec is not None and not args.fake:
        raise ValueError(
            "--spec requires --fake until PR 2 implements sensitive-content validation; "
            "unvalidated specification content cannot be sent to a real LLM"
        )

    spec = None
    if args.spec is not None:
        if not Path(args.spec).is_file():
            raise ValueError(f"--spec must name a text file: {args.spec}")
        spec_files = inputs.collect([args.spec])
        if not spec_files:
            raise ValueError(f"--spec could not be read as an eligible text file: {args.spec}")
        spec = spec_files[0].text

    files = inputs.collect(args.paths)
    print(f"Read {len(files)} text file(s).")
    kept, skipped = filters.split_sensitive(files)
    for path in skipped:
        print(f"Skipped {path}: sensitive file", file=sys.stderr)
    if not kept:
        raise ValueError("No scannable files remain after input selection and filtering")

    hits = detector.detect(kept)
    try:
        result = drafter.draft(kept, hits, spec=spec, fake=args.fake)
    except Exception:
        # Preserve the detector's useful output even when drafting fails.
        print("Detected boundaries (for manual handoff):", file=sys.stderr)
        if not hits:
            print("  None found.", file=sys.stderr)
        for hit in hits:
            print(f"  {hit.file}:{hit.line} [{hit.kind}]", file=sys.stderr)
        raise

    writer.write(result, args.o, scope=[source.path for source in kept])
    print(f"Wrote {len(result.items)} item(s) to {args.o}.")


def main(argv: Optional[list[str]] = None) -> None:
    """Parse argv (defaults to sys.argv[1:]) and run `scan` or `mark`."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "scan":
            _scan(args)
        else:
            writer.mark(
                args.path, args.item_id, args.status, args.evidence,
                evidence_type=args.evidence_type,
            )
            print(f"Marked {args.item_id} as {args.status} in {args.path}.")
    except Exception as error:
        # CLI boundary: turn failed module operations into readable errors.
        # SystemExit and KeyboardInterrupt are BaseExceptions and still propagate.
        print(f"handoff: error: {error}", file=sys.stderr)
        raise SystemExit(1) from None
