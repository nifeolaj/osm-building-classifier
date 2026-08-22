#!/bin/bash
#SBATCH --job-name=osm_stage1_germany
#SBATCH --output=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_stage1_germany-out.%j.txt
#SBATCH --error=/fast/home/o-olajuyigbe/osm_building_classifier/logs/osm_stage1_germany-err.%j.txt
#SBATCH --time=4:00:00
#SBATCH --partition=normal
#SBATCH --cpus-per-task=16
#SBATCH --mem=256G
#SBATCH --ntasks=1

source ~/.bashrc
conda activate osm_env

cd /fast/home/o-olajuyigbe/osm_building_classifier

python -u scripts/run_tag_stage1.py