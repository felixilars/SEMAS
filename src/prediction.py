import cv2
import numpy as np
import os
from pathlib import Path
from pdf2image import convert_from_path

class SchemaFinder:
    """
    Pipe extracting from a PDF every component of interest.
    """

    def __init__(self, model, **kwargs):
        """
        Args:
            - model : The model used for recognizing components from a PDF.
            - **kwargs : Keyword arguments passed to the model.predict method.
        """
        self.model = model
        self.params = kwargs

    def find(self, pdf_path: str, output_dir: str):
        """
        Args:
            - pdf_path: The path of the PDF to extract from.
            - output_dir: The directory to save the extracted PDFs.
        """
        print(f"Extracting components from {pdf_path}...")
        # Conversion du PDF en image
        pages = convert_from_path(pdf_path, dpi=300)

        for p_id, page in enumerate(pages):
            page_array = np.array(page)
            # Prédit les classes présentes dans le document
            result = self.model.predict(source=page, **self.params)
            for box in result[0].boxes:
                # Récupération des coordonnées de la zone
                x,y,y1,x1 = map(int, box.xyxy[0])
                margin = 10 # Ajout d'une marge
                y1_m = max(0, y-margin)
                y2_m = min(page_array.shape[0], y1 + margin)
                x1_m = max(0, x-margin)
                x2_m = min(page_array.shape[1], x1 + margin)
                crop = page_array[y1_m:y2_m, x1_m:x2_m]
                if crop is not None and crop.size > 0:
                    # Récupération de la classe de la zone
                    cls = result[0].names[int(box.cls[0])]
                    # Sauvegarde de l'image découpée dans output_dir
                    filename = f"{Path(pdf_path).stem}_{p_id}_{cls}.png"
                    cv2.imwrite(os.path.join(output_dir, filename), crop)
        print("Extraction completed.")