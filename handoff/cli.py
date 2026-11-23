"""① Command line entry. Owner: 方騏為 Cactex.

Commands to support (plan §1.1):

    python -m handoff scan PATH... [--spec FILE] [-o HANDOFF.md] [--fake]
    python -m handoff mark A-01 mismatch --evidence "..." [--type inspect_sample] [-f HANDOFF.md]

`scan` runs the pipeline in this order:
    inputs.collect -> filters.split_sensitive -> detector.detect -> drafter.draft -> writer.write
and reports what was read, what was skipped and how many items were written.
`mark` parses its arguments and calls writer.mark (implemented by ④).
"""

from __future__ import annotations

from typing import Optional


def main(argv: Optional[list[str]] = None) -> None:
    """Parse argv (defaults to sys.argv[1:]) and run `scan` or `mark`."""
    raise NotImplementedError("① cli.main: to be implemented by Cactex")
