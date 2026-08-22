"""Run the OSM download and extraction stage."""

import argparse

from osm_classifier.pipeline import run_extraction


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download or use an existing OSM PBF and extract all required layers."
    )
    parser.add_argument("--country", required=True, help="Country name, e.g. germany")
    parser.add_argument("--continent", help="Geofabrik continent, e.g. europe")
    parser.add_argument("--geofabrik-region", help="Full region, e.g. europe/germany")
    parser.add_argument("--pbf-path", help="Existing local .osm.pbf file")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    outputs = run_extraction(
        country=args.country,
        continent=args.continent,
        geofabrik_region=args.geofabrik_region,
        pbf_path=args.pbf_path,
        overwrite=args.overwrite,
    )

    print("\nExtraction outputs:")
    for layer, path in outputs.items():
        print(f"{layer}: {path}")


if __name__ == "__main__":
    main()