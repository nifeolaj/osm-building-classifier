#!/bin/bash
#SBATCH --job-name=osm_semicomm_de
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_semicomm_de-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_semicomm_de-err.%j.txt
#SBATCH --time=24:00:00
#SBATCH --partition=normal
#SBATCH --cpus-per-task=16
#SBATCH --mem=256G
#SBATCH --ntasks=1

source ~/.bashrc
conda activate osm_env

cd /fast/home/o-olajuyigbe/osm_building_classifier

python -u scripts/run_semi_commercial.py