"""
Central filesystem paths for the OSM Building Classifier.

Keeping paths here prevents different modules from using inconsistent
relative paths such as ../data or ../../outputs.
"""

from pathlib import Path


# This file is located at:
# <project_root>/osm_classifier/paths.py
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


# Configuration
RESOURCES_DIR = PACKAGE_DIR / "resources"
CONFIGS_DIR = RESOURCES_DIR / "configs"
COUNTRY_CONFIGS_DIR = CONFIGS_DIR / "countries"
MODEL_WEIGHTS_DIR = RESOURCES_DIR / "model_weights"


# Data
DATA_DIR = PROJECT_ROOT / "data" / "osm_classifier_data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"


# Models and results
OUTPUTS_DIR = DATA_DIR / "outputs"
LOGS_DIR = PROJECT_ROOT / "logs"

