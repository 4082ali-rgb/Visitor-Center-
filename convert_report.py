#!/usr/bin/env python3
"""Convert Clover Sales Overview reports to Markdown with MarkItDown.

This is the first step for every report: the Markdown copy is what the day's
figures are read from before they go into the JSON input for build_je.py.

Usage:
    python3 convert_report.py REPORT.pdf [REPORT.pdf ...] [-o OUTPUT_DIR]

Writes OUTPUT_DIR/<report name>.md for each input (default: reports_md).
"""

import argparse
import sys
from pathlib import Path

from markitdown import MarkItDown


def convert(src, out_dir, md=None):
    """Convert one report and return the path of the Markdown written."""
    md = md or MarkItDown()
    result = md.convert(str(src))
    text = result.text_content.strip()
    if not text:
        raise ValueError(f"{src}: no text extracted (scanned image PDF?)")
    dest = Path(out_dir) / f"{Path(src).stem}.md"
    dest.write_text(text + "\n", encoding="utf-8")
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inputs", nargs="+", type=Path, help="Clover report file(s)")
    ap.add_argument("-o", "--out", type=Path, default=Path("reports_md"),
                    help="output directory (default: reports_md)")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()
    failed = False
    for src in args.inputs:
        try:
            print(f"wrote {convert(src, args.out, md)}")
        except Exception as e:
            print(f"FAILED {src}: {e}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
