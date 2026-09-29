#!/usr/bin/env python3
"""Build a QBO journal entry import CSV for one Visitor Centre day.

Implements VISITOR_CENTRE_JE_RULES.md. Input is a JSON file of figures read
off the Clover Sales Overview report; see examples/ for the shape.

Usage:
    python3 build_je.py DAY.json [DAY.json ...] [-o OUTPUT_DIR]

Exits non-zero, writing nothing for that day, if the entry does not balance
or a revenue category is unmapped. Everything else is written and flagged.
"""

import argparse
import csv
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

VC = "0051-VISITOR CENTER"
PARKS = "0050-MANNING PARKS"

# Clover revenue class -> (QBO account, class, description label or None)
REVENUE_MAP = {
    "Snacks": ("3014 Revenue - Snacks", VC, None),
    "Gifts": ("3018 Revenue - Souvenir", VC, None),
    "Non-Alcoholic": ("3006 Revenue - Non-Alcoholic", VC, None),
    "Unclassified": ("3010 Visitor Centre Retail", VC, "Unclassified"),
    "Parks Fees": ("3001 Revenue", PARKS, "Park Fee"),
}
CARD_ACCOUNT = "1007 Visa / Mstrcrd / Debit Receivable"
CASH_ACCOUNT = "1002 Petty Cash in safe"
GST_ACCOUNT = "2029 GST Charged on Sales"
PST_ACCOUNT = "2035 PST 7% Charged on Sales"

HEADER = ["*JournalNo", "*JournalDate", "Memo", "*AccountName", "Debits",
          "Credits", "Description", "Name", "Location", "Class"]


class BlockingError(Exception):
    """A condition under which the entry must not be delivered."""


def cents(value, field):
    """Parse a money figure into integer cents. Never goes through float."""
    if value is None or value == "":
        return 0
    try:
        d = Decimal(str(value).replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        raise BlockingError(f"{field}: not a number: {value!r}")
    if d != d.quantize(Decimal("0.01")):
        raise BlockingError(f"{field}: more than two decimals: {value!r}")
    return int(d * 100)


def fmt(c):
    return f"{c // 100}.{c % 100:02d}"


def card_lines(day, flags):
    """Apply the §5 card split rule. Returns [(label, cents)]."""
    tt = {k: cents(v, f"tender_types.{k}") for k, v in day.get("tender_types", {}).items()}
    ct = {k: cents(v, f"card_types.{k}") for k, v in day.get("card_types", {}).items()}
    for k in tt:
        if k not in ("Debit Card", "Credit Card"):
            raise BlockingError(f"tender_types: unknown tender {k!r}")
    debit, credit = tt.get("Debit Card", 0), tt.get("Credit Card", 0)
    interac, visa, mc = ct.get("Interac", 0), ct.get("Visa", 0), ct.get("MasterCard", 0)
    other_brands = sorted(k for k in ct if k not in ("Interac", "Visa", "MasterCard") and ct[k])

    figures = (f"Tender Types Debit {fmt(debit)} / Credit {fmt(credit)}; "
               f"Card Types Interac {fmt(interac)} / Visa {fmt(visa)} / MasterCard {fmt(mc)}")
    if other_brands:
        figures += "; other brands " + ", ".join(f"{b} {fmt(ct[b])}" for b in other_brands)

    if not other_brands and interac + visa + mc == debit + credit:
        if interac == debit and visa + mc == credit:
            flags.append(f"Card path: brand split (splits match). {figures}")
        else:
            flags.append(f"Card path: brand split (card totals match; Tender Types "
                         f"debit/credit split differs and is not used). {figures}")
        lines = [("Visa", visa), ("MasterCard", mc), ("Debit", interac)]
    else:
        why = "unmapped card brand present" if other_brands else "card totals differ"
        flags.append(f"Card path: Tender Types fallback ({why}). {figures}")
        lines = [("Debit", debit), ("Credit", credit)]
    return [(label, amt) for label, amt in lines if amt]


def build(day):
    """Return (filename, rows, flags) or raise BlockingError."""
    flags = []
    jno = str(day.get("journal_no", "")).strip()
    if not re.fullmatch(r"JJ\d+", jno):
        raise BlockingError(f"journal_no missing or malformed: {jno!r} (never auto-increment; confirm with the sequence owner)")
    if not day.get("journal_no_confirmed"):
        flags.append(f"Journal number {jno} is PROPOSED, not confirmed.")

    d = date.fromisoformat(day["date"])
    memo = f"Visitor Centre Daily Revenue {d.day:02d} {d:%B %Y}"
    jdate = f"{d:%d-%m-%Y}"
    filename = f"{jno}_VisitorCentre_{d.day}{d:%b%Y}.csv"

    debits, credits = [], []  # (account, cents, description, class)

    for label, amt in card_lines(day, flags):
        debits.append((CARD_ACCOUNT, amt, f"{label} - {memo}", VC))
    cash = cents(day.get("cash"), "cash")
    if cash:
        debits.append((CASH_ACCOUNT, cash, memo, VC))
    else:
        flags.append("No cash: 1002 line omitted.")

    revenue = day.get("revenue", {})
    unmapped = [k for k in revenue if k not in REVENUE_MAP and cents(revenue[k], f"revenue.{k}")]
    if unmapped:
        raise BlockingError(f"Unmapped revenue category: {', '.join(unmapped)}")
    for cat, (acct, cls, label) in REVENUE_MAP.items():
        amt = cents(revenue.get(cat), f"revenue.{cat}")
        if amt:
            credits.append((acct, amt, f"{label} - {memo}" if label else memo, cls))
            if cat == "Gifts":
                flags.append("Gifts -> 3018 Revenue - Souvenir mapping still unconfirmed (rules §10).")
        else:
            flags.append(f"No {cat}: {acct.split()[0]} line omitted.")

    tax = day.get("tax", {})
    gst, pst = cents(tax.get("GST"), "tax.GST"), cents(tax.get("PST"), "tax.PST")
    if gst:
        credits.append((GST_ACCOUNT, gst, memo, VC))
    else:
        flags.append("No GST: 2029 line omitted.")
    if pst:
        credits.append((PST_ACCOUNT, pst, memo, VC))
    else:
        flags.append("No PST: 2035 line omitted.")

    rc_tax = day.get("revenue_classes_tax_total")
    if rc_tax not in (None, ""):
        rc = cents(rc_tax, "revenue_classes_tax_total")
        if rc != gst + pst:
            flags.append(f"Revenue Classes tax column {fmt(rc)} differs from Tax details "
                         f"{fmt(gst + pst)}; used Tax details.")

    rows = [[jno, jdate, memo, a, fmt(c), "", desc, "", "", cls] for a, c, desc, cls in debits]
    rows += [[jno, jdate, memo, a, "", fmt(c), desc, "", "", cls] for a, c, desc, cls in credits]

    # §7: recompute from the rows actually being written, in integer cents.
    total_dr = sum(cents(r[4], "row debit") for r in rows)
    total_cr = sum(cents(r[5], "row credit") for r in rows)
    collected = cents(day.get("amount_collected"), "amount_collected")
    if not (total_dr == total_cr == collected):
        raise BlockingError(f"Does not balance: debits {fmt(total_dr)}, credits {fmt(total_cr)}, "
                            f"Amount Collected {fmt(collected)}. Find the mismatched source table.")

    for r in rows:
        if any("," in field for field in r):
            raise BlockingError(f"Comma in row: {r}")
    return filename, rows, flags


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inputs", nargs="+", type=Path, help="day JSON file(s)")
    ap.add_argument("-o", "--out", type=Path, default=Path("out"), help="output directory (default: out)")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    failed = False
    for path in args.inputs:
        print(f"== {path}")
        try:
            filename, rows, flags = build(json.loads(path.read_text()))
        except (BlockingError, KeyError, ValueError) as e:
            print(f"  BLOCKED: {e}  (nothing written)")
            failed = True
            continue
        dest = args.out / filename
        with open(dest, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\r\n")
            w.writerow(HEADER)
            w.writerows(rows)
        print(f"  wrote {dest}  ({len(rows)} lines, balanced)")
        for flag in flags:
            print(f"  - {flag}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
