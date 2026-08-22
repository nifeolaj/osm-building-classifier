#!/bin/bash
#SBATCH --job-name=osm_full_nl
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_nl_pipeline-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_nl_pipeline-err.%j.txt
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

osm-classifier run netherlands \
    --geofabrik-region europe/netherlands \
    --projected-crs EPSG:3035 \
    --overwrite

echo "Finished: $(date)"