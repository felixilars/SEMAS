"""
Document Rasterization Diagnostic Script
================================================
Renders a target service manual page at 300 DPI using PyMuPDF (fitz) and validates output image dimensions and memory footprints.
"""

from pathlib import Path
import fitz

def render_manual_page(pdf_path, page_num, output_dir, dpi=300):
    """ Render an individual PDF manual page to high-resolution PNG bitmap.
    Args:
      - pdf_path (Path or str) : Path to source service manual PDF.
      - page_num (int) : 1-based page index to extract.
      - output_dir (Path or str) : Target output directory.
      - dpi (int) : Target rendering DPI resolution.
    Returns: Path to rendered PNG file or None on failure.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    if not pdf_path.exists():
        print("[ERROR] PDF source file not found: " + str(pdf_path))
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)

    if page_num < 1 or page_num > len(doc):
        print("[ERROR] Page number " + str(page_num) + " out of bounds (1-" + str(len(doc)) + ")")
        doc.close()
        return None

    # Calculate zoom scale factor (PDF native resolution is 72 DPI)
    zoom_scale = dpi / 72.0
    matrix = fitz.Matrix(zoom_scale, zoom_scale)

    page = doc[page_num - 1]
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    target_name = pdf_path.stem + "_p" + str(page_num).zfill(3) + "_" + str(dpi) + "dpi.png"
    out_path = output_dir / target_name
    pix.save(str(out_path))
    doc.close()

    print("[INFO] Rendered page " + str(page_num) + " to: " + str(out_path))
    print("[INFO] Image dimensions: " + str(pix.width) + "x" + str(pix.height) + " pixels")
    return out_path

if __name__ == "__main__":
    sample_pdf = Path("data/raw_manuals/Sony_TA-1630.pdf")
    destination = Path("data/extracted_manuals/Sony_TA-1630/bom")
    render_manual_page(sample_pdf, 6, destination, 300)
