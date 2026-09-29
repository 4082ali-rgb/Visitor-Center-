import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build_je  # noqa: E402


def load(name):
    return json.loads((ROOT / "examples" / name).read_text())


class BuildTests(unittest.TestCase):
    def test_brand_split(self):
        fn, rows, flags = build_je.build(load("brand_split.json"))
        self.assertEqual(fn, "JJ3500_VisitorCentre_1Sep2026.csv")
        descs = [r[6] for r in rows if r[3] == build_je.CARD_ACCOUNT]
        memo = "Visitor Centre Daily Revenue 01 September 2026"
        self.assertEqual(descs, [f"Visa - {memo}", f"MasterCard - {memo}", f"Debit - {memo}"])
        park = [r for r in rows if r[3] == "3001 Revenue"][0]
        self.assertEqual((park[6], park[9]), (f"Park Fee - {memo}", build_je.PARKS))
        self.assertFalse(any(r[3] == "3010 Visitor Centre Retail" for r in rows))
        self.assertTrue(any("PROPOSED" in f for f in flags))
        self.assertTrue(any("used Tax details" in f for f in flags))

    def test_fallback_uses_tender_types_only(self):
        # JJ2938 shape: mixing Debit from Tender Types with Visa/MC from card
        # types would not balance. The fallback must use Tender Types only.
        fn, rows, flags = build_je.build(load("fallback.json"))
        card = [(r[6].split(" - ")[0], r[4]) for r in rows if r[3] == build_je.CARD_ACCOUNT]
        self.assertEqual(card, [("Debit", "189.45"), ("Credit", "153.11")])
        self.assertTrue(any("fallback" in f for f in flags))
        self.assertFalse(any(r[3] == "3001 Revenue" for r in rows))

    def test_grand_totals_match_but_splits_differ(self):
        day = load("brand_split.json")
        day["card_types"] = {"Interac": "80.00", "Visa": "110.00", "MasterCard": "40.00"}
        _, rows, flags = build_je.build(day)
        self.assertTrue(any("grand totals match" in f for f in flags))
        self.assertEqual(sum(1 for r in rows if r[3] == build_je.CARD_ACCOUNT), 2)

    def test_single_card_line_keeps_prefix(self):
        day = load("brand_split.json")
        day.update(amount_collected="110.00", cash="20.00",
                   revenue={"Snacks": "110.00"}, tax={"GST": "0.00", "PST": ""},
                   tender_types={"Debit Card": "0", "Credit Card": "90.00"},
                   card_types={"Visa": "0", "MasterCard": "90.00"})
        _, rows, _ = build_je.build(day)
        card = [r for r in rows if r[3] == build_je.CARD_ACCOUNT]
        self.assertEqual(len(card), 1)
        self.assertTrue(card[0][6].startswith("MasterCard - "))

    def test_unbalanced_blocks(self):
        day = load("brand_split.json")
        day["amount_collected"] = "250.01"
        with self.assertRaisesRegex(build_je.BlockingError, "balance"):
            build_je.build(day)

    def test_unmapped_category_blocks(self):
        day = load("brand_split.json")
        day["revenue"]["Coffee"] = "5.00"
        with self.assertRaisesRegex(build_je.BlockingError, "Unmapped"):
            build_je.build(day)

    def test_missing_journal_number_blocks(self):
        day = load("brand_split.json")
        del day["journal_no"]
        with self.assertRaises(build_je.BlockingError):
            build_je.build(day)

    def test_csv_format(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(build_je.main([str(ROOT / "examples" / "brand_split.json"), "-o", out]), 0)
            raw = (Path(out) / "JJ3500_VisitorCentre_1Sep2026.csv").read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        rows = list(csv.reader(io.StringIO(raw.decode())))
        self.assertEqual(rows[0], build_je.HEADER)
        for r in rows[1:]:
            self.assertEqual(r[:3], ["JJ3500", "01-09-2026", "Visitor Centre Daily Revenue 01 September 2026"])
            self.assertTrue(bool(r[4]) != bool(r[5]))
            self.assertEqual(r[7:9], ["", ""])

    def test_blocked_day_writes_nothing(self):
        day = load("brand_split.json")
        day["amount_collected"] = "1.00"
        with tempfile.TemporaryDirectory() as out:
            p = Path(out) / "bad.json"
            p.write_text(json.dumps(day))
            self.assertEqual(build_je.main([str(p), "-o", out]), 1)
            self.assertEqual(list(Path(out).glob("*.csv")), [])


if __name__ == "__main__":
    unittest.main()
