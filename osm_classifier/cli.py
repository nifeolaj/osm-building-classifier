"""Command-line interface for the OSM Building Classifier."""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_classifier.pipeline import run_full_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="osm-classifier",
        description=(
        "Classify OpenStreetMap building footprints by function and subtype.\n\n"
        "The pipeline extracts buildings and contextual OSM data, applies "
        "rule-based classification, uses machine-learning models trained on "
        "German OSM building data to predict building types and subtypes in the "
        "target country, groups related industrial buildings into sites, and "
        "exports the final building and industrial-site databases."
    ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Run 'osm-classifier run --help' for pipeline options.\n\n"
            "Example:\n"
            "  osm-classifier run netherlands \\\n"
            "      --geofabrik-region europe/netherlands \\\n"
            "      --projected-crs EPSG:3035"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run the complete building-classification pipeline.",
        description=(
            "Run the complete OSM building-classification pipeline.\n\n"
            "The country is a positional argument and must be written directly\n"
            "after 'run'. Supply either a local OSM PBF file or a Geofabrik region.\n"
            "A projected CRS using metres is required for distance and area features."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n\n"
            "  Download the Netherlands from Geofabrik:\n"
            "    osm-classifier run netherlands \\\n"
            "        --geofabrik-region europe/netherlands \\\n"
            "        --projected-crs EPSG:3035\n\n"
            "  Use an existing local PBF file:\n"
            "    osm-classifier run kenya \\\n"
            "        --pbf /data/kenya-latest.osm.pbf \\\n"
            "        --projected-crs EPSG:32737\n\n"
            "  Use optional building-height data:\n"
            "    osm-classifier run germany \\\n"
            "        --pbf /data/germany-latest.osm.pbf \\\n"
            "        --projected-crs EPSG:3035 \\\n"
            "        --height-data /data/building_heights.parquet \\\n"
            "        --height-column height_m\n\n"
            "  Change the small-building threshold from 40 to 25 m²:\n"
            "    osm-classifier run netherlands \\\n"
            "        --geofabrik-region europe/netherlands \\\n"
            "        --projected-crs EPSG:3035 \\\n"
            "        --small-building-max-area 25\n\n"
            "Notes:\n"
            "  • Europe-wide analyses can generally use EPSG:3035.\n"
            "  • Countries outside Europe require an appropriate local metric CRS.\n"
            "  • --height-data and --height-column must be supplied together.\n"
            "  • Area options override the defaults in base.yaml for that run only.\n"
            "  • Existing stage outputs are reused unless --overwrite is supplied."
        ),
    )

    run_parser.add_argument(
        "country",
        metavar="COUNTRY",
        help=(
            "Target country name or output slug, for example 'france', "
            "'netherlands', or 'kenya'. This name is also used in output filenames."
        ),
    )

    input_group = run_parser.add_argument_group("input data")

    input_group.add_argument(
        "--pbf",
        type=Path,
        metavar="PATH",
        help=(
            "Path to an existing local .osm.pbf file. Use this instead of downloading "
            "data from Geofabrik."
        ),
    )
    input_group.add_argument(
        "--geofabrik-region",
        metavar="REGION",
        help=(
            "Full Geofabrik download region, for example 'europe/france' or "
            "'africa/kenya'. The latest .osm.pbf file will be downloaded automatically."
        ),
    )
    input_group.add_argument(
        "--continent",
        metavar="REGION",
        help=(
            "Geofabrik top-level region, for example 'europe', 'africa', or "
            "'asia'. Used when the complete Geofabrik region is not supplied."
        ),
    )

    spatial_group = run_parser.add_argument_group("spatial reference")

    spatial_group.add_argument(
        "--projected-crs",
        metavar="CRS",
        help=(
            "Projected coordinate reference system used for all distance and area "
            "calculations, for example EPSG:3035 for Europe. The CRS must use metres; "
            "a geographic CRS such as EPSG:4326 is not valid."
        ),
    )

    height_group = run_parser.add_argument_group("optional building-height data",
        description=("Optionally provide an external building-footprint dataset containing "
            "building heights. Heights are matched geometrically to OSM buildings and "
            "used only by the height-enhanced machine-learning models."
        ),
    )

    height_group.add_argument("--height-data", type=Path, metavar="PATH",
        help=("Path to an optional spatial dataset containing building geometries and "
            "height values. Supported formats include GeoParquet and formats readable "
            "by GeoPandas."
        ),
    )
    height_group.add_argument("--height-column", metavar="COLUMN",
        help=("Name of the column containing building heights in metres. Must be supplied "
            "together with --height-data."
        ),
    )

    threshold_group = run_parser.add_argument_group(
        "optional Stage 2 area thresholds",
        description=(
            "These options override the default rule thresholds in base.yaml. "
            "All areas are building-footprint areas in square metres."
        ),
    )

    threshold_group.add_argument(
        "--small-building-max-area",
        type=float,
        metavar="M2",
        help=(
            "Maximum area for filtering unaddressed buildings as small auxiliary "
            "structures. Default: 40 m². Lower this where valid houses commonly have "
            "small footprints."
        ),
    )
    threshold_group.add_argument(
        "--garage-min-area",
        type=float,
        metavar="M2",
        help="Minimum area considered by the detached-garage rule. Default: 40 m².",
    )
    threshold_group.add_argument(
        "--garage-max-area",
        type=float,
        metavar="M2",
        help="Maximum area considered by the detached-garage rule. Default: 50 m².",
    )
    threshold_group.add_argument(
        "--residential-zone-min-area",
        type=float,
        metavar="M2",
        help=(
            "Minimum area for assigning an addressed building inside a trusted "
            "residential zone as residential. Default: 80 m²."
        ),
    )
    threshold_group.add_argument(
        "--residential-zone-max-area",
        type=float,
        metavar="M2",
        help=(
            "Maximum area for assigning an addressed building inside a trusted "
            "residential zone as residential. Default: 200 m²."
        ),
    )

    output_group = run_parser.add_argument_group("output behaviour")

    output_group.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Recreate existing intermediate and final outputs. Without this option, "
            "completed stages are skipped and the pipeline resumes from existing files."
        ),
    )
    output_group.add_argument(
        "--no-provenance",
        action="store_true",
        help=(
            "Exclude classification confidence and label-source columns from the final "
            "building database."
        ),
    )

    return parser


def main() -> None:
    """Run the command-line interface."""
    args = build_parser().parse_args()

    if args.command == "run":
        outputs = run_full_pipeline(
            country=args.country,
            continent=args.continent,
            geofabrik_region=args.geofabrik_region,
            pbf_path=args.pbf,
            projected_crs=args.projected_crs,
            height_data=args.height_data,
            height_column=args.height_column,
            small_building_max_area=args.small_building_max_area,
            garage_min_area=args.garage_min_area,
            garage_max_area=args.garage_max_area,
            residential_zone_min_area=args.residential_zone_min_area,
            residential_zone_max_area=args.residential_zone_max_area,
            include_provenance=not args.no_provenance,
            overwrite=args.overwrite,
        )

        print("\nFinal outputs:")
        print(f"  Buildings:        {outputs['final_buildings']}")
        print(f"  Industrial sites: {outputs['final_industrial_sites']}")


if __name__ == "__main__":
    main()