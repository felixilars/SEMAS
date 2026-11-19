from pathlib import Path

from src.ingestion.manifest import EXTRACTED_MANUALS_DIR, PAGE_ROLES, RAW_MANUALS_DIR, load_manifest, page_image_name

RENDER_DPI = 300
PDF_POINTS_PER_INCH = 72


def registry_tables(manuals):
    """ Page tables and file name prefixes of the registered manuals, keyed by folder name.

    Args:
      - manuals (list) : ManualEntry objects of the registry.
    Returns: Tuple (pages by folder, manual identifier by folder).
    """
    return {m.folder: m.pages for m in manuals}, {m.folder: m.manual_id for m in manuals}


def create_directory_structure(output_base_dir, manuals_dict):
    """ Create folder hierarchy for manual pages.
    Args:
      - output_base_dir (Path) : Base destination directory.
      - manuals_dict (dict) : Mapping of manual names to category pages
    """
    output_base_dir.mkdir(parents=True, exist_ok=True)

    for manual_name in manuals_dict.keys():
        manual_folder = output_base_dir / manual_name
        for category in PAGE_ROLES:
            cat_dir = manual_folder / category
            cat_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] Created directory structure at: " + str(output_base_dir))


def build_pdf_index(raw_manuals_dir):
    """ Build a lookup index mapping manual stem names to PDF paths in a single directory walk.

    Args:
      - raw_manuals_dir (Path) : Directory containing raw manual PDFs.
    Returns: Dict mapping file stem strings to Path instances.
    """
    if not raw_manuals_dir.exists():
        return {}
    return {f.stem: f for f in raw_manuals_dir.rglob("*.pdf")}


def extract_pages_to_images(manuals_dict, raw_manuals_dir, output_base_dir, device_names, force=False):
    """ Extract specified pages to PNG images and save to category folders.

    Args:
      - manuals_dict (dict) : Dictionary of manuals and their page numbers.
      - raw_manuals_dir (Path) : Directory of raw manuals.
      - output_base_dir (Path) : Directory of output images.
      - device_names (dict) : Folder name to manual identifier, the prefix of the page file names.
      - force (bool) : Whether to re-render pages if they already exist on disk.
    """
    try:
        import pymupdf as fitz 
    except ImportError:
        print("[ERROR] PyMuPDF (fitz) is not installed.")
        return

    zoom = RENDER_DPI / PDF_POINTS_PER_INCH
    matrix = fitz.Matrix(zoom, zoom)
    pdf_index = build_pdf_index(raw_manuals_dir)

    for manual_name, categories in manuals_dict.items():
        # Check configured pages
        total_pages_configured = sum(len(pages) for pages in categories.values())
        if total_pages_configured == 0:
            continue

        pdf_path = pdf_index.get(manual_name)
        if not pdf_path:
            print("[WARN] PDF file not found for: " + str(manual_name) + " in " + str(raw_manuals_dir))
            continue

        device_short_name = device_names.get(manual_name, manual_name)
        print("\n[INFO] Processing: " + pdf_path.name + " (Short name: " + device_short_name + ")")
        doc = fitz.open(pdf_path)

        for category, pages in categories.items():
            if not pages:
                continue

            save_dir = output_base_dir / manual_name / category
            save_dir.mkdir(parents=True, exist_ok=True)

            for page_num in pages:
                # Convert to 0-based index
                page_idx = page_num - 1
                out_img_path = save_dir / page_image_name(device_short_name, page_num)

                # Caching check: avoid expensive high-DPI re-rendering if page already exists
                if out_img_path.exists() and not force:
                    print("[INFO] Using cached page: " + out_img_path.name)
                    continue

                if 0 <= page_idx < len(doc):
                    page = doc[page_idx]
                    pix = page.get_pixmap(matrix=matrix)
                    pix.save(str(out_img_path))
                    print("[INFO] Saved " + category + ": " + out_img_path.name)
                else:
                    print("[WARN] Page " + str(page_num) + " exceeds total pages (" + str(len(doc)) + " pages)")

        doc.close()

def main():
    """ Render the hand-sorted pages of every registered manual."""
    pages_table, manual_ids = registry_tables(load_manifest())
    create_directory_structure(EXTRACTED_MANUALS_DIR, pages_table)
    if RAW_MANUALS_DIR.exists():
        extract_pages_to_images(pages_table, RAW_MANUALS_DIR, EXTRACTED_MANUALS_DIR, manual_ids)


if __name__ == "__main__":
    main()
