import httpx
import base64
import logging

logger = logging.getLogger(__name__)

PDFSHIFT_URL = "https://api.pdfshift.io/v3/convert/pdf"


def _local_html_to_pdf(html: str) -> bytes:
    """Fallback: generate a simple PDF locally using fpdf2 (no API key needed)."""
    from fpdf import FPDF
    import re

    # Strip HTML tags for plain text extraction
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Normalize unicode to latin-1 safe characters
    text = text.replace('\u2014', '-').replace('\u2013', '-').replace('\u2019', "'") \
               .replace('\u201c', '"').replace('\u201d', '"').replace('\u00b7', '.') \
               .replace('\u2713', '[OK]').replace('\u26a0', '[!]')
    text = text.encode('latin-1', errors='replace').decode('latin-1')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "SERVICE AGREEMENT", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", size=10)
    # Write text in chunks to respect page width
    for line in text.split('. '):
        line = line.strip()
        if line:
            pdf.multi_cell(0, 6, line + '.', align='L')
            pdf.ln(1)

    return pdf.output()


class PDFShiftClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def html_to_pdf(self, html: str) -> bytes:
        """Convert HTML string to PDF bytes via PDFShift API."""
        credentials = base64.b64encode(f"api:{self.api_key}".encode()).decode()
        payload = {
            "source": html,
            "landscape": False,
            "use_print": False,
            "format": "A4",
            "margin": "20px",
        }
        if not self.api_key:
            logger.warning("No PDFShift API key — using local PDF fallback")
            return _local_html_to_pdf(html)

        try:
            resp = httpx.post(
                PDFSHIFT_URL,
                json=payload,
                headers={"Authorization": f"Basic {credentials}"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError as e:
            logger.error("PDFShift error %s — falling back to local PDF", e.response.status_code)
            return _local_html_to_pdf(html)
        except httpx.RequestError as e:
            logger.error("PDFShift request failed — falling back to local PDF: %s", str(e))
            return _local_html_to_pdf(html)
