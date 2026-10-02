import os
from pathlib import Path

DEVICE_SHORT_NAMES = {
    "10780-90006 - 10780A Laser Receiver for 5501A [Prefix 1948] (Mar 1980)": "HP_10780A",
    "aiwa_csd_a510_portable_music_center": "Aiwa_CSD_A510",
    "hfe_jvc_jp-s7_service_en": "JVC_JP_S7",
    "tektronix_2205_cro_smanual": "Tektronix_2205",
}

# Note: The page numbers here are the display page numbers in the document (1-based index)
MANUALS_PAGES = {
    "10780-90006 - 10780A Laser Receiver for 5501A [Prefix 1948] (Mar 1980)": {
        "bom": [17],
        "schematic": [24],
        "pcb": [23]
    },
    "aiwa_csd_a510_portable_music_center": {
        "bom": [4, 5, 6],
        "schematic": [9, 10, 13, 14, 17],
        "pcb": [8, 12, 15, 16]
    },
    "hfe_jvc_jp-s7_service_en": {
        "bom": [14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41],
        "schematic": [43, 44, 45, 46],
        "pcb": [13, 20, 22, 23, 24, 25, 26, 29, 32, 34, 36, 39, 40]
    },
    "tektronix_2205_cro_smanual": {
        "bom": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 168, 169, 170],
        "schematic": [134, 141, 144, 147, 149, 153, 157, 158, 174, 175],
        "pcb": [129, 132, 135, 138, 150, 159, 160, 161, 162]
    }
}

CATEGORIES = ["bom", "schematic", "pcb"]


def create_directory_structure(output_base_dir, manuals_dict):
    """
    output_base_dir/
      └── <manual_name>/
          ├── bom/
          ├── schematic/
          └── pcb/
    """
    output_base_dir.mkdir(parents=True, exist_ok=True)

    for manual_name in manuals_dict.keys():
        manual_folder = output_base_dir / manual_name
        for category in CATEGORIES:
            cat_dir = manual_folder / category
            cat_dir.mkdir(parents=True, exist_ok=True)

    print("Create directory structure: " + str(output_base_dir))


def find_pdf_file(raw_manuals_dir, manual_name):
    """
    Find PDF file in raw_manuals directory.
    """
    for file in raw_manuals_dir.rglob("*.pdf"):
        if file.stem == manual_name:
            return file
    return None


def extract_pages_to_images(manuals_dict, raw_manuals_dir, output_base_dir, device_names=None, zoom_x=2.0, zoom_y=2.0):
    """
    Extract pages to images and save them to the corresponding folders.
    """
    if device_names is None:
        device_names = DEVICE_SHORT_NAMES

    import fitz 

    matrix = fitz.Matrix(4.167, 4.167)  # Increase image resolution

    for manual_name, categories in manuals_dict.items():
        pdf_path = find_pdf_file(raw_manuals_dir, manual_name)
        if not pdf_path:
            print("Not found PDF file for: " + manual_name + " in " + raw_manuals_dir)
            continue

        device_short_name = device_names.get(manual_name, manual_name)
        print("\nProcessing: " + pdf_path.name + " (Device short name: " + device_short_name + ")")
        doc = fitz.open(pdf_path)

        for category, pages in categories.items():
            save_dir = output_base_dir / manual_name / category
            save_dir.mkdir(parents=True, exist_ok=True)

            for page_num in pages:
                # Convert 1-based (display page) to 0-based index
                page_idx = page_num - 1

                if 0 <= page_idx < len(doc):
                    page = doc[page_idx]
                    pix = page.get_pixmap(matrix=matrix)
                    out_img_path = save_dir / (device_short_name + "_page_" + str(page_num).zfill(3) + ".png")
                    pix.save(str(out_img_path))
                    print("  -> Save: " + category + ": " + out_img_path.name)
                else:
                    print("  [!] Page " + str(page_num) + " exceeds the number of pages of the document (" + str(len(doc)) + " pages)")

        doc.close()


def main():
    base_dir = Path("../SEMAS")
    raw_manuals_dir = base_dir / "data" / "raw_manuals" / ">300dpi"
    output_base_dir = base_dir / "data" / "extracted_manuals"

    create_directory_structure(output_base_dir, MANUALS_PAGES)

    if raw_manuals_dir.exists():
        extract_pages_to_images(MANUALS_PAGES, raw_manuals_dir, output_base_dir, device_names=DEVICE_SHORT_NAMES)

if __name__ == "__main__":
    main()


