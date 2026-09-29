import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build_je  # noqa: E402
import parse_report  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


class ParseSep01(unittest.TestCase):
    """Real Clover reports for 1 Sep 2026, converted by MarkItDown (JJ3702)."""

    def setUp(self):
        sales = (FIX / "sales_2026-09-01.md").read_text()
        taxes = (FIX / "taxes_2026-09-01.md").read_text()
        self.day, self.flags = parse_report.parse(sales, taxes)

    def test_figures(self):
        d = self.day
        self.assertEqual(d["date"], "2026-09-01")
        self.assertEqual(d["amount_collected"], "100.90")
        self.assertEqual(d["revenue"], {"Gifts": "75.39", "Snacks": "11.80", "Unclassified": "7.90"})
        self.assertEqual(d["tax"], {"GST": "4.37", "PST": "1.44"})
        self.assertEqual(d["tender_types"], {"Credit Card": "73.08", "Debit Card": "16.82"})
        self.assertEqual(d["card_types"], {"MasterCard": "59.86", "Interac": "16.82", "Visa": "13.22"})
        self.assertEqual(d["cash"], "11.00")
        self.assertEqual(self.flags, [])

    def test_end_to_end(self):
        _, rows, flags = build_je.build({"journal_no": "JJ3702", "journal_no_confirmed": True, **self.day})
        self.assertEqual([(r[3].split()[0], r[4] or r[5]) for r in rows], [
            ("1007", "13.22"), ("1007", "59.86"), ("1007", "16.82"), ("1002", "11.00"),
            ("3014", "11.80"), ("3018", "75.39"), ("3010", "7.90"), ("2029", "4.37"), ("2035", "1.44"),
        ])
        self.assertTrue(any("brand split" in f for f in flags))

    def test_missing_section_blocks(self):
        sales = (FIX / "sales_2026-09-01.md").read_text().replace("Revenue Classes", "Something Else")
        with self.assertRaises(parse_report.ParseError):
            parse_report.parse(sales, (FIX / "taxes_2026-09-01.md").read_text())


if __name__ == "__main__":
    unittest.main()
