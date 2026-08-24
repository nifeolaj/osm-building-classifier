# OSM Building Classifier

A Python package for classifying OpenStreetMap building footprints by type and subtype and grouping industrial buildings into industrial sites.

The package runs an end-to-end workflow from OSM data acquisition to final GeoParquet export.

## Overview

The workflow performs:

1. OSM PBF download or local-file loading
2. Extraction of buildings and contextual OSM layers
3. Building and context-data cleaning
4. Rule-based building classification
5. Spatial feature engineering and optional building-height integration
6. Hierarchical machine-learning inference
7. Semi-commercial building classification
8. Industrial-site grouping
9. Final database assembly and export

The pretrained machine-learning models were developed using German OSM data and can be transferred to other target countries using the same feature-generation and classification framework.

## Installation

The pretrained model files are stored using Git Large File Storage (Git LFS). Install Git LFS on your system, then initialize it with `git lfs install` before cloning the repository.

```bash
git lfs install
git clone <repository-url>
cd osm_building_classifier
pip install -e .
```

For development and testing:

```bash
pip install -e ".[dev]"
```

Check the installation:

```bash
osm-classifier --help
osm-classifier run --help
```

## Basic Usage

The classifier can download a Geofabrik OSM extract automatically.

### Germany

Germany has default download and projected CRS settings:

```bash
osm-classifier run germany
```

### Other countries

For another country, provide its Geofabrik region and an appropriate metric projected CRS:

```bash
osm-classifier run france \
    --geofabrik-region europe/france \
    --projected-crs EPSG:3035
```

### Local OSM PBF

An existing `.osm.pbf` file can be used instead of downloading data:

```bash
osm-classifier run kenya \
    --pbf /path/to/kenya-latest.osm.pbf \
    --projected-crs EPSG:32737
```

The projected CRS must:

- not be a geographic CRS;
- use metre-based coordinates;
- be suitable for the target country or study region.

### Optional building-height data

An external spatial building dataset containing building footprints and height values can optionally be supplied:

```bash
osm-classifier run germany \
    --height-data /path/to/building_heights.parquet \
    --height-column height_m
```

The external dataset must contain building geometries, a numeric building-height column in metres, and a defined coordinate reference system.

External building footprints are spatially matched to OSM buildings. Successfully matched heights are added as `building_height_m` and used only by the height-enhanced machine-learning models.

When external height data are supplied, the package automatically uses the `with_height` model bundle. Otherwise, it uses the `osm_only` model bundle.

### Recreate existing outputs

```bash
osm-classifier run france \
    --geofabrik-region europe/france \
    --projected-crs EPSG:3035 \
    --overwrite
```

Without `--overwrite`, completed stages are skipped automatically and the workflow resumes from the first missing output.

### Exclude provenance columns

```bash
osm-classifier run france \
    --geofabrik-region europe/france \
    --projected-crs EPSG:3035 \
    --no-provenance
```

## Main Command-line arguments

| Argument | Description |
|---|---|
| `country` | Target-country name or slug |
| `--pbf` | Existing local `.osm.pbf` file |
| `--geofabrik-region` | Geofabrik region, such as `europe/france` |
| `--continent` | Optional Geofabrik continent or top-level region |
| `--projected-crs` | Metric projected CRS for the target country |
| `--height-data` | Optional spatial building dataset containing building heights |
| `--height-column` | Name of the height column in the external dataset |
| `--overwrite` | Recreate outputs that already exist |
| `--no-provenance` | Exclude confidence and source columns from the final output |

Either `--pbf` or `--geofabrik-region` must be supplied when no country download configuration exists.

The `--height-data` and `--height-column` arguments must be supplied together.

## Model transfer

All predictions use the pretrained German model bundles located at:

```text
osm_classifier/resources/model_weights/germany/
```

Two model variants are included:

```text
osm_classifier/resources/model_weights/germany/osm_only/
osm_classifier/resources/model_weights/germany/with_height/
```

The package also uses the German model thresholds and saved feature definitions.

When these models are applied outside Germany, the results represent cross-country model transfer and accuracy may differ. Outputs for new countries should therefore be evaluated before being used for operational applications.

## Final outputs

For an OSM-only run, the completed workflow creates:

```text
data/osm_classifier_data/outputs/<country>/buildings.parquet
data/osm_classifier_data/outputs/<country>/industrial_sites.parquet
```

When external height data are used:

```text
data/osm_classifier_data/outputs/<country>/buildings_height.parquet
data/osm_classifier_data/outputs/<country>/industrial_sites_height.parquet
```

Both outputs are GeoParquet files with geometries exported in WGS 84 (`EPSG:4326`).

## Building database

| Column | Description |
|---|---|
| `osm_building_id` | OpenStreetMap building identifier |
| `geometry` | Building footprint geometry |
| `building_type` | Main building class |
| `building_subtype` | Detailed building class |
| `industrial_site_id` | Linked industrial-site identifier |
| `industrial_site_subtype` | Industrial activity assigned to the linked site |
| `footprint_area_m2` | Building footprint area in square metres |
| `is_abandoned` | Indicates whether the building was identified as abandoned or disused |
| `building_type_confidence` | Confidence for the main building class |
| `building_subtype_confidence` | Confidence for the building subtype |
| `classification_source` | Rule or model responsible for the classification |

Confidence values may be unavailable for classifications assigned directly from OSM tags or deterministic rules.

## Industrial-site database

| Column | Description |
|---|---|
| `industrial_site_id` | Unique industrial-site identifier |
| `geometry` | Industrial-site or standalone-building geometry |
| `industrial_site_subtype` | Assigned industrial activity |
| `site_area_m2` | Site area in square metres |
| `building_count` | Number of buildings linked to the site |
| `industrial_building_count` | Number of linked buildings classified as industrial |
| `grouping_type` | Industrial land-use zone or standalone building |

For land-use-zone parents, `site_area_m2` represents the industrial land-use polygon area. For standalone industrial-building parents, it represents the building footprint area.

## Intermediate outputs

Intermediate datasets are stored under:

```text
data/osm_classifier_data/raw/
data/osm_classifier_data/interim/
data/osm_classifier_data/processed/
```

These include extracted OSM layers, cleaned layers, rule-classification outputs, engineered features, and postprocessed classifications.

Intermediate outputs allow interrupted workflows to resume without repeating completed stages.

## Configuration

Shared rule and feature settings are stored in:

```text
osm_classifier/resources/configs/base.yaml
```

The German configuration contains the default Germany settings and trained-model thresholds:

```text
osm_classifier/resources/configs/countries/germany.yaml
```

A country-specific YAML file is not required for other target countries. Their projected CRS and OSM source can be supplied through the CLI.

## Project structure

```text
osm_building_classifier/
├── notebooks/
│   └── reference/
├── osm_classifier/
│   ├── cleaning/
│   ├── context/
│   ├── export/
│   ├── extraction/
│   ├── features/
│   ├── models/
│   ├── postprocess/
│   ├── resources/
│   │   ├── configs/
│   │   └── model_weights/
│   ├── rules/
│   ├── taxonomy/
│   ├── validation/
│   ├── cli.py
│   ├── config.py
│   ├── paths.py
│   └── pipeline.py
├── scripts/
│   └── slurm/
├── tests/
├── .gitignore
├── README.md
└── pyproject.toml
```

The production implementation is contained in the `osm_classifier/` package. The `notebooks/reference/` directory contains the research notebooks used during development of the classification methodology. Example SLURM scripts for national-scale execution are provided in `scripts/slurm/`.

## Testing

Run the automated test suite:

```bash
pytest -v
```

The tests cover command-line behavior, input validation, optional height matching, packaged model resources, and both OSM-only and height-enhanced pipeline orchestration.


## Runtime

National-scale processing can require substantial memory and processing time. The CLI reports the duration of each pipeline stage and the total runtime.

