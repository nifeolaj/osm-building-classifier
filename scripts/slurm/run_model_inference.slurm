#!/bin/bash
#SBATCH --job-name=osm_ml_germany
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_ml_germany-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_ml_germany-err.%j.txt
#SBATCH --time=24:00:00
#SBATCH --partition=normal
#SBATCH --cpus-per-task=16
#SBATCH --mem=512G
#SBATCH --ntasks=1

source ~/.bashrc
conda activate osm_env

cd /fast/home/o-olajuyigbe/osm_building_classifier

python -u scripts/run_model_inference.py