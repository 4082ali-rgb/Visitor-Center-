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

1. Convert the Clover Sales Overview PDF to Markdown first:

   ```
   .venv/bin/python convert_report.py SalesOverview.pdf -o reports_md
   ```

   Read the day's figures from the `.md` file it writes.
2. Copy `examples/brand_split.json` and fill in the day's figures from the Clover
   Sales Overview report (tables named per rules §2). Leave a category out or blank
   if it had no activity.
3. Set `journal_no` to the number you've confirmed. The script never makes one up.
   Set `journal_no_confirmed` to `true` once it's confirmed; otherwise the output
   flags it as proposed.
4. Run:

   ```
   python3 build_je.py day.json [more.json ...] -o out
   ```

For each day it writes `out/{JournalNo}_VisitorCentre_{DMonYYYY}.csv` and prints
the flags list (rules §9). An unbalanced entry or an unmapped revenue category
blocks that day: no file is written and the script exits non-zero.

`revenue_classes_tax_total` is optional. Enter the Revenue Classes "Taxes & Fees"
total to have any cent difference from Tax details flagged.

## Tests

```
python3 -m unittest discover -s tests   # or .venv/bin/python to include the converter tests
```
