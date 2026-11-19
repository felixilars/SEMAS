# SEMAS (Service Electronic Manual Analysis System)

> **Étude Pratique 2026-2027 (INSA Rennes)**

## Équipe de projet (Team Members)

| Nom & Prénom | Adresse e-mail |
| :--- | :--- |
| **Chahd MOKAHLI-RATBI** | [Chahd.Mokahli-Ratbi@insa-rennes.fr](mailto:Chahd.Mokahli-Ratbi@insa-rennes.fr) |
| **Duc-Nam NGUYEN** | [Duc-Nam.Nguyen@insa-rennes.fr](mailto:Duc-Nam.Nguyen@insa-rennes.fr) |
| **Céleste PIERRE** | [arpierre@insa-rennes.fr](mailto:arpierre@insa-rennes.fr) |
| **Juliette RABREAU** | [Juliette.rabreau@insa-rennes.fr](mailto:Juliette.rabreau@insa-rennes.fr) |

## Installation

Python 3.10.

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

## Données

Les PDF de manuels et les pages rendues ne sont pas versionnés (droits d'auteur, taille).
Placer les PDF dans `data/raw_manuals/`, puis :

```bash
.venv/bin/python -m src.ingestion.extract_pages
```

Vérité terrain : `data/ground_truth/` (Toshiba SY-330 = développement, McIntosh MC-2100 = test).
Les résultats d'évaluation sont écrits en JSON dans `results/`.

## Structure

| Dossier | Rôle |
| :--- | :--- |
| `src/ingestion/` | Rendu PDF vers images 300 DPI |
| `src/layout/` | Analyse des tableaux BOM (gouttières, fusion de jetons, expansion de plages) |
| `src/ocr_engine/` | Moteurs OCR, rotations, post-correction, extraction schéma |
| `src/graph/` | Modèle de données |
| `src/evaluation/` | Vérité terrain, métriques, scripts d'évaluation |
| `tools/` | Diagnostics visuels |
