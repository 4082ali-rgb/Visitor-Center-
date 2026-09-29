import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import convert_report
except ImportError:  # markitdown not installed
    convert_report = None


def tiny_pdf(lines):
    """Build a minimal one-page text PDF without extra libraries."""
    stream = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(
        f"({l}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{off:010d} 00000 n \n" for off in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


@unittest.skipIf(convert_report is None, "markitdown not installed")
class ConvertTests(unittest.TestCase):
    def test_pdf_to_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "SalesOverview_31Aug2026.pdf"
            src.write_bytes(tiny_pdf(["Sales Overview", "Amount Collected 392.56"]))
            self.assertEqual(convert_report.main([str(src), "-o", d]), 0)
            text = (Path(d) / "SalesOverview_31Aug2026.md").read_text()
        self.assertIn("Amount Collected", text)
        self.assertIn("392.56", text)

    def test_bad_file_reported(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(convert_report.main([str(Path(d) / "missing.pdf"), "-o", d]), 1)


if __name__ == "__main__":
    unittest.main()
