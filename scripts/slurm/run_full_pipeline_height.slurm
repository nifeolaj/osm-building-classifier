#!/bin/bash
#SBATCH --job-name=osm_classifier
#SBATCH --output=logs/osm_classifier-out.%j.txt
#SBATCH --error=logs/osm_classifier-err.%j.txt
#SBATCH --partition=normal
#SBATCH --time=2-00:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=512G
#SBATCH --ntasks=1

set -euo pipefail

source ~/.bashrc
conda activate osm_env

PROJECT_DIR=/path/to/osm_building_classifier
HEIGHT_DATA=/path/to/building_heights.parquet

cd "$PROJECT_DIR"
mkdir -p logs

echo "Started: $(date)"
echo "Host: $(hostname)"

osm-classifier run germany \
    --geofabrik-region europe/germany \
    --projected-crs EPSG:3035 \
    --height-data "$HEIGHT_DATA" \
    --height-column height_m \
    --overwrite

echo "Finished: $(date)"