#!/bin/bash
#SBATCH --job-name=osm_full_de_height
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_full_de_height-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_full_de_height-err.%j.txt
#SBATCH --partition=normal
#SBATCH --time=3-00:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=512G
#SBATCH --ntasks=1

source ~/.bashrc
conda activate osm_env

set -euo pipefail

cd /fast/home/o-olajuyigbe/osm_building_classifier
mkdir -p logs
pip install -e .

echo "Started: $(date)"
echo "Host: $(hostname)"

osm-classifier run germany \
    --geofabrik-region europe/germany \
    --projected-crs EPSG:3035 \
    --height-data /fast/home/o-olajuyigbe/data/germany_lod2/final/germany_lod2_buildings.parquet \
    --height-column measured_height_m \
    --small-building-max-area 40 \
    --garage-min-area 40 \
    --garage-max-area 50 \
    --overwrite

echo "Finished: $(date)"