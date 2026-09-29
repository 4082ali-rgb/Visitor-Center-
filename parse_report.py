#!/usr/bin/env python3
"""Extract a day's figures from Clover reports into build_je.py input JSON.

Takes the Sales Overview and Taxes reports for one day, either as PDFs
(converted with MarkItDown first) or as Markdown already produced by
convert_report.py. Report type is detected from content, so order is free.

Usage:
    python3 parse_report.py SALES TAXES --journal-no JJ3702 [--confirmed] [-o day.json]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

MONEY = re.compile(r"-?\$[\d,]+\.\d{2}")
SECTIONS = ["Sales", "Tender Types", "Revenue Classes", "Sales By Card Type",
            "Cash Deposits", "Cash Adjustments", "Tax details"]


class ParseError(Exception):
    pass


def money(cell):
    return cell.replace("$", "").replace(",", "")


def load_text(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from markitdown import MarkItDown
        return MarkItDown().convert(str(path)).text_content
    return path.read_text(encoding="utf-8")


def tables(text):
    """Map section title -> list of rows; each row is (label, [amounts])."""
    out, current = {}, None
    for line in text.splitlines():
        s = line.strip()
        if s in SECTIONS:
            current = s
            out.setdefault(current, [])
            continue
        if current and s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or set(cells[0]) <= set("- "):
                continue  # markdown separator row
            amounts = [money(m) for m in MONEY.findall(s)]
            if amounts:  # rows without amounts are column headers
                out[current].append((cells[0], amounts))
    return out


def rows(t, section):
    if section not in t or not t[section]:
        raise ParseError(f"section {section!r} not found or empty")
    return {label: amts for label, amts in t[section]}


def check_total(section, table, pick, flags):
    """Flag when a table's Total row doesn't equal the sum of its lines."""
    if "Total" not in table:
        return
    parts = sum(Decimal(pick(a)) for k, a in table.items() if k != "Total")
    total = Decimal(pick(table["Total"]))
    if parts != total:
        flags.append(f"{section}: lines sum to {parts} but Total shows {total}")


def parse(sales_text, tax_text):
    flags = []
    m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", sales_text)
    if not m:
        raise ParseError("report date not found in Sales Overview")
    day = datetime.strptime(" ".join(m.groups()), "%b %d %Y").date()

    st, tt = tables(sales_text), tables(tax_text)

    sales = rows(st, "Sales")
    if "Amount Collected" not in sales or not sales["Amount Collected"]:
        raise ParseError("Amount Collected not found in Sales table")
    amount_collected = sales["Amount Collected"][-1]

    tenders = rows(st, "Tender Types")
    check_total("Tender Types", tenders, lambda a: a[-1], flags)
    tender_types = {k: a[-1] for k, a in tenders.items() if k in ("Debit Card", "Credit Card")}
    other = [k for k in tenders if k not in ("Debit Card", "Credit Card", "Cash", "Total")]
    if other:
        raise ParseError(f"unknown tender type(s): {', '.join(other)}")

    cards = rows(st, "Sales By Card Type") if "Sales By Card Type" in st else {}
    check_total("Sales By Card Type", cards, lambda a: a[-1], flags)
    card_types = {k: a[-1] for k, a in cards.items() if k != "Total"}

    # Revenue Classes amounts: Gross, Discounts, Refunds, Net, Taxes & Fees, Non-revenue
    rc = rows(st, "Revenue Classes")
    for k, a in rc.items():
        if len(a) != 6:
            raise ParseError(f"Revenue Classes row {k!r}: expected 6 amounts, got {a}")
    check_total("Revenue Classes", rc, lambda a: a[3], flags)
    revenue = {k: a[3] for k, a in rc.items() if k != "Total"}
    rc_tax = rc["Total"][4] if "Total" in rc else None

    cash = ""
    if "Cash Deposits" in st and st["Cash Deposits"]:
        cd = rows(st, "Cash Deposits")
        cash = (cd.get("Total") or next(iter(cd.values())))[0]
    cash_tender = tenders.get("Cash", [None])[-1]
    if cash_tender and cash and Decimal(cash_tender) != Decimal(cash):
        flags.append(f"Cash Deposits {cash} differs from Tender Types Cash {cash_tender}; used Cash Deposits")

    # Tax details amounts: Applicable sales, Taxes collected, Taxes refunded, Net taxes
    tax = {}
    for k, a in rows(tt, "Tax details").items():
        name = k.split()[0]
        if name in ("GST", "PST") and a:
            tax[name] = a[-1]

    return {
        "date": day.isoformat(),
        "amount_collected": amount_collected,
        "revenue": revenue,
        "tax": tax,
        "revenue_classes_tax_total": rc_tax,
        "tender_types": tender_types,
        "card_types": card_types,
        "cash": cash,
    }, flags


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs=2, type=Path, help="Sales Overview and Taxes reports (PDF or .md)")
    ap.add_argument("--journal-no", required=True, help="confirmed journal number, e.g. JJ3702")
    ap.add_argument("--confirmed", action="store_true", help="journal number is confirmed")
    ap.add_argument("-o", "--out", type=Path, help="write JSON here (default: stdout)")
    args = ap.parse_args(argv)

    texts = [load_text(p) for p in args.reports]
    sales = [t for t in texts if "Sales Overview" in t]
    taxes = [t for t in texts if "Taxes Report" in t or "Tax details" in t]
    if len(sales) != 1 or len(taxes) != 1:
        print("BLOCKED: need exactly one Sales Overview and one Taxes report")
        return 1
    try:
        day, flags = parse(sales[0], taxes[0])
    except ParseError as e:
        print(f"BLOCKED: {e}")
        return 1
    day = {"journal_no": args.journal_no, "journal_no_confirmed": args.confirmed, **day}

    text = json.dumps(day, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    for f in flags:
        print(f"  - {f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
