#!/bin/bash
#SBATCH --job-name=osm_context_germany
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_context_germany-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_context_germany-err.%j.txt
#SBATCH --time=8:00:00
#SBATCH --partition=normal
#SBATCH --cpus-per-task=16
#SBATCH --mem=256G
#SBATCH --ntasks=1

source ~/.bashrc
conda activate osm_env

cd /fast/home/o-olajuyigbe/osm_building_classifier

python -u scripts/run_context_mapping.py