#!/bin/bash
#SBATCH --job-name=osm_export_de
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_export_de-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_export_de-err.%j.txt
#SBATCH --time=04:00:00
#SBATCH --partition=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --ntasks=1

source ~/.bashrc
conda activate osm_env

cd /fast/home/o-olajuyigbe/osm_building_classifier

python -u scripts/run_final_export.py