# Visitor Centre daily revenue journal entries

Turns Clover POS daily figures into a QuickBooks Online journal entry import CSV,
following [VISITOR_CENTRE_JE_RULES.md](VISITOR_CENTRE_JE_RULES.md).

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

This installs [MarkItDown](https://github.com/microsoft/markitdown), which converts
the Clover reports to Markdown.

## Usage

Give it the day's two Clover PDFs (Sales Overview and Taxes) and the confirmed
journal number. The Taxes report can be left out on a day with no tax at all; the
script checks the Sales Overview shows $0.00 Taxes & Fees and stops otherwise.

```
.venv/bin/python parse_report.py Sales_Sep_01.pdf Taxes_Sep_01.pdf --journal-no JJ3702 --confirmed -o day.json
.venv/bin/python build_je.py day.json -o out
```

`parse_report.py` runs each PDF through MarkItDown, pulls the figures from the
Markdown (tables per rules §2) and writes the day's JSON. It stops if a table it
needs is missing or laid out differently from what it expects, and flags any
table whose Total row doesn't match its lines. Leave out `--confirmed` if the
journal number is only proposed. It never makes up a journal number.

To keep a readable copy of a report, `convert_report.py REPORT.pdf -o reports_md`
writes the Markdown on its own. You can also hand-write the JSON; see `examples/`.

For each day it writes `out/{JournalNo}_VisitorCentre_{DMonYYYY}.csv` and prints
the flags list (rules §9). An unbalanced entry or an unmapped revenue category
blocks that day: no file is written and the script exits non-zero.

`revenue_classes_tax_total` is optional. Enter the Revenue Classes "Taxes & Fees"
total to have any cent difference from Tax details flagged.

## Tests

```
.venv/bin/python -m unittest discover -s tests
```
