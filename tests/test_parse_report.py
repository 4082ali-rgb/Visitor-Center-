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


class ParseSep02(unittest.TestCase):
    """2 Sep 2026 reports: truncated 'Non-Alcoho…' label, card totals match but splits differ (JJ3703)."""

    def setUp(self):
        sales = (FIX / "sales_2026-09-02.md").read_text()
        taxes = (FIX / "taxes_2026-09-02.md").read_text()
        self.day, self.flags = parse_report.parse(sales, taxes)

    def test_truncated_label_resolved(self):
        self.assertEqual(self.day["revenue"]["Non-Alcoholic"], "21.75")
        self.assertTrue(any("truncated" in f for f in self.flags))

    def test_end_to_end_brand_split(self):
        # Matches the corrected entry posted in QBO for 2 Sep.
        _, rows, flags = build_je.build({"journal_no": "JJ3703", **self.day})
        self.assertEqual([(r[3].split()[0], r[4] or r[5]) for r in rows], [
            ("1007", "13.72"), ("1007", "15.70"), ("1007", "16.90"), ("1002", "90.75"),
            ("3014", "41.60"), ("3018", "38.35"), ("3006", "21.75"), ("3010", "25.75"),
            ("2029", "5.99"), ("2035", "3.63"),
        ])
        self.assertTrue(any("split differs and is not used" in f for f in flags))

    def test_ambiguous_truncation_left_for_build_to_block(self):
        self.assertEqual(parse_report.expand("No…", {"Non-Alcoholic": 1, "Novelty": 1}), "No…")


class ParseSep04(unittest.TestCase):
    """4 Sep 2026 reports: Firewood and Parks Fees (JJ3705)."""

    def test_end_to_end(self):
        day, _ = parse_report.parse((FIX / "sales_2026-09-04.md").read_text(),
                                    (FIX / "taxes_2026-09-04.md").read_text())
        _, rows, _ = build_je.build({"journal_no": "JJ3705", **day})
        self.assertEqual([(r[3].split()[0], r[4] or r[5], r[9]) for r in rows], [
            ("1007", "124.36", build_je.VC), ("1007", "7.84", build_je.VC), ("1007", "3.10", build_je.VC),
            ("1002", "29.34", build_je.VC),
            ("3014", "5.95", build_je.VC), ("3018", "68.10", build_je.VC), ("3006", "7.00", build_je.VC),
            ("3008", "38.10", build_je.VC), ("3010", "14.20", build_je.VC), ("3001", "21.90", build_je.PARKS),
            ("2029", "7.07", build_je.VC), ("2035", "2.32", build_je.VC),
        ])


if __name__ == "__main__":
    unittest.main()
