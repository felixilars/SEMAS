from __future__ import annotations
from pathlib import Path

# Short document names
DEVICE_SHORT_NAMES: dict[str, str] = {
    "Acoustic_Control_450_Lead_Bass_Guitar_Amplifier_Service Manual_1974": "Acoustic_450",
    "Akai_AM-M630_AM-M830_Digital_Integrated_Amplifier_Service_Manual": "Akai_AM_M630_M830",
    "HP 5261A Video Amplifier 05261-9011 Sep. 1972": "HP_5261A",
    "Sony-TA-1630-Service-Manual": "Sony_TA_1630",
    "Toshiba-SY-330-Service-Manual": "Toshiba_SY_330",
    "alpine_pdx-5_pwr_amplifier": "Alpine_PDX_5",
    "hfe_jvc_jp-s7_service_en": "JVC_JP_S7",
    "infinity_kappa_255a_car_amplifier": "Infinity_Kappa_255a",
    "jbl_ms-a1004_rev1_car_amplifier_sm": "JBL_MS_A1004",
    "manualsplus_08649": "TEAC_AR_250SFM",
    "manualsplus_13963": "McIntosh_MC_2100",
}

# 1-based display page numbers
MANUALS_PAGES: dict[str, dict[str, list[int]]] = {
    "Acoustic_Control_450_Lead_Bass_Guitar_Amplifier_Service Manual_1974": {
        "bom": [14,15,16,17],
        "schematic": [6,7,8,9,10],
        "pcb": [11,12,13]   
    },
    "Akai_AM-M630_AM-M830_Digital_Integrated_Amplifier_Service_Manual": {
        "bom": [5,6,7,8],
        "schematic": [13, 14, 15, 16, 17, 18, 19, 20, 21,24,25,26,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,53,54,55,56,57,58,59,60],
        "pcb": [22,23,45,46,47,48,49,50,51,52]
    },
    "HP 5261A Video Amplifier 05261-9011 Sep. 1972": {
        "bom": [31,32],
        "schematic": [25,39,41],
        "pcb": [23,24,37,38,40]
    },
    "Sony-TA-1630-Service-Manual": {
        "bom": [9],
        "schematic": [2,6],
        "pcb": [3,4,5,7,8]
    },
    "Toshiba-SY-330-Service-Manual": {
        "bom": [7,8],
        "schematic": [2,5],
        "pcb": [6]
    },
    "alpine_pdx-5_pwr_amplifier": {
        "bom": [20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39], 
        "schematic": [9,10,11,12,13],
        "pcb": [7,8]
    },
    "hfe_jvc_jp-s7_service_en": {
        "bom": [14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41],
        "schematic": [43, 44, 45, 46],
        "pcb": [13, 20, 22, 23, 24, 25, 26, 29, 32, 34, 36, 39, 40]
    },
    "infinity_kappa_255a_car_amplifier": {
        "bom": [22,23,24,25,26,27,28,29],
        "schematic": [30,31,32,33,34,35,36,37,38,39,40,41],
        "pcb": [14,16,17,19]
    },
    "jbl_ms-a1004_rev1_car_amplifier_sm": {
        "bom": [20,21,22,23,24,25], 
        "schematic": [65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80],
        "pcb": [14]
    },
    "manualsplus_08649": {
        "bom": [65,66,67,68,69], #66 and 68 are white page. we will use it to improve training model (confusing pages)
        "schematic": [57,58,59,60,61,62,63,64],
        "pcb": [71,72]
    },
    "manualsplus_13963": {
        "bom": [10],
        "schematic": [7,8],
        "pcb": [6,8]
    },
}

CATEGORIES = ["bom", "schematic", "pcb"]


def create_directory_structure(output_base_dir, manuals_dict):
    """ Create folder hierarchy for manual pages.
    Args:
      - output_base_dir (Path) : Base destination directory.
      - manuals_dict (dict) : Mapping of manual names to category pages
    """
    output_base_dir.mkdir(parents=True, exist_ok=True)

    for manual_name in manuals_dict.keys():
        manual_folder = output_base_dir / manual_name
        for category in CATEGORIES:
            cat_dir = manual_folder / category
            cat_dir.mkdir(parents=True, exist_ok=True)

    print("Created directory structure at: " + str(output_base_dir))


def find_pdf_file(raw_manuals_dir, manual_name):
    """ Find PDF file recursively in raw_manuals directory matching manual_name stem.

    Args:
      - raw_manuals_dir (Path) : Directory containing raw manual PDFs.
      - manual_name (str) : Name of the target manual.
    Returns: Path to the PDF file or None if not found.
    """
    for file in raw_manuals_dir.rglob("*.pdf"):
        if file.stem == manual_name:
            return file
    return None


def extract_pages_to_images(manuals_dict, raw_manuals_dir, output_base_dir, device_names):
    """ Extract specified pages to PNG images and save to category folders.

    Args:
      - manuals_dict (dict) : Dictionary of manuals and their page numbers.
      - raw_manuals_dir (Path) : Directory of raw manuals.
      - output_base_dir (Path) : Directory of output images.
      - device_names (dict) : Dictionary mapping manual names to short names
    """
    if device_names is None:
        device_names = DEVICE_SHORT_NAMES

    try:
        import pymupdf as fitz 
    except ImportError:
        print("[Error] PyMuPDF (fitz) is not installed.")
        return

    matrix = fitz.Matrix(4.167, 4.167)  # High resolution (~300 DPI)

    for manual_name, categories in manuals_dict.items():
        # Check configured pages
        total_pages_configured = sum(len(pages) for pages in categories.values())
        if total_pages_configured == 0:
            continue

        pdf_path = find_pdf_file(raw_manuals_dir, manual_name)
        if not pdf_path:
            print("[Warning] PDF file not found for: " + str(manual_name) + " in " + str(raw_manuals_dir))
            continue

        device_short_name = device_names.get(manual_name, manual_name)
        print("\nProcessing: " + pdf_path.name + " (Short name: " + device_short_name + ")")
        doc = fitz.open(pdf_path)

        for category, pages in categories.items():
            if not pages:
                continue

            save_dir = output_base_dir / manual_name / category
            save_dir.mkdir(parents=True, exist_ok=True)

            for page_num in pages:
                # Convert to 0-based index
                page_idx = page_num - 1

                if 0 <= page_idx < len(doc):
                    page = doc[page_idx]
                    pix = page.get_pixmap(matrix=matrix)
                    out_img_path = save_dir / (device_short_name + "_page_" + str(page_num).zfill(3) + ".png")
                    pix.save(str(out_img_path))
                    print("[INFO] Saved " + category + ": " + out_img_path.name)
                else:
                    print("[WARN] Page " + str(page_num) + " exceeds total pages (" + str(len(doc)) + " pages)")

        doc.close()

def main():
    """ Run page extraction across all configured service manuals """
    # Resolve paths
    base_dir = Path(__file__).resolve().parent.parent
    raw_manuals_dir = base_dir / "data" / "raw_manuals"
    output_base_dir = base_dir / "data" / "extracted_manuals"

    create_directory_structure(output_base_dir, MANUALS_PAGES)

    if raw_manuals_dir.exists():
        extract_pages_to_images(MANUALS_PAGES, raw_manuals_dir, output_base_dir, DEVICE_SHORT_NAMES)

if __name__ == "__main__":
    main()