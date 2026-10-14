"""
Generate synthetic PDF and DOCX sample documents for testing.

Usage:
    python data/sample_docs/generate_samples.py

This creates sample_hr_policy.pdf and sample_it_guidelines.docx
from the existing .txt versions, providing format diversity for testing.
"""

from pathlib import Path
import sys


def generate_pdf(txt_path: Path, pdf_path: Path) -> None:
    """Create a multi-page PDF from a text file using pypdf."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        print("reportlab not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

    text = txt_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                            topMargin=1 * inch, bottomMargin=1 * inch)
    styles = getSampleStyleSheet()
    story = []

    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 12))
        elif line.startswith("SECTION") or line.startswith("ACME"):
            story.append(Paragraph(line, styles["Heading1"]))
        elif line[0:2] in ("1.", "2.", "3.", "4."):
            story.append(Paragraph(line, styles["Heading2"]))
        else:
            story.append(Paragraph(line, styles["BodyText"]))

    doc.build(story)
    print(f"[OK] Created {pdf_path}")


def generate_docx(txt_path: Path, docx_path: Path) -> None:
    """Create a DOCX from a text file using python-docx."""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        print("python-docx not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
        from docx import Document
        from docx.shared import Pt

    text = txt_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    doc = Document()
    for line in lines:
        line = line.strip()
        if not line:
            doc.add_paragraph("")
        elif line.startswith("SECTION") or line.startswith("ACME"):
            doc.add_heading(line, level=1)
        elif line[0:2] in ("1.", "2.", "3.", "4."):
            doc.add_heading(line, level=2)
        else:
            doc.add_paragraph(line)

    doc.save(str(docx_path))
    print(f"[OK] Created {docx_path}")



if __name__ == "__main__":
    script_dir = Path(__file__).parent

    hr_txt = script_dir / "sample_hr_policy.txt"
    it_txt = script_dir / "sample_it_guidelines.txt"

    if hr_txt.exists():
        generate_pdf(hr_txt, script_dir / "sample_hr_policy.pdf")

    if it_txt.exists():
        generate_docx(it_txt, script_dir / "sample_it_guidelines.docx")

    print("\nDone! Sample documents generated.")
