"""Extract all OSM layers required by the building-classification pipeline."""

from __future__ import annotations

import gc
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable
import pyrosm
from osm_classifier.paths import INTERIM_DATA_DIR

Config = dict[str, Any]

LAYER_ORDER = ("buildings", "landuse", "pois", "roads", "railways", "waterways", "manmade",)


def _country_slug(country: str) -> str:
    """Convert a country name to a filename-safe slug."""
    slug = country.strip().lower().replace("-", "_")
    slug = "_".join(slug.split())
    if not slug:
        raise ValueError("Country name cannot be empty.")
    return slug


def _clean_object_cols(gdf):
    """Convert mixed object columns to strings to prevent Arrow errors."""
    for column in gdf.select_dtypes(include="object").columns:
        gdf[column] = gdf[column].astype(str)
    return gdf


def _get_extractors(osm: pyrosm.OSM) -> dict[str, Callable]:
    """Return the extraction function for each required OSM layer."""
    return {
        "buildings": osm.get_buildings,
        "landuse": osm.get_landuse,
        "pois": osm.get_pois,
        "roads": lambda: osm.get_network(network_type="driving"),
        "railways": lambda: osm.get_data_by_custom_criteria(
            custom_filter={"railway": ["rail", "light_rail", "narrow_gauge", "tram", "subway",]}),
        "waterways": lambda: osm.get_data_by_custom_criteria(
            custom_filter={"waterway": ["river", "canal", "stream", "drain", "ditch",]}),
        "manmade": lambda: osm.get_data_by_custom_criteria(
            custom_filter={"man_made": True}, filter_type="keep",
            keep_nodes=False, keep_ways=True, keep_relations=True,),}


def extract_osm_layers(pbf_path: str | Path, country: str, config: Config, *,
    output_dir: str | Path | None = None, overwrite: bool | None = None,) -> dict[str, Path]:
    """
    Extract OSM layers and save them as GeoParquet files.

    Parameters
    ----------
    pbf_path: path to an existing OSM PBF file.
    country: country name used in output filenames.
    config: configuration returned by load_config().
    output_dir: poutput directory. Defaults to data/interim.
    overwrite: whether existing layer files should be replaced.

    Returns
    -------
    dict: layer names and their saved file paths.
    """
    pbf_path = Path(pbf_path).expanduser().resolve()
    if not pbf_path.is_file():
        raise FileNotFoundError(f"OSM PBF not found: {pbf_path}")

    country_slug = _country_slug(country)
    output_dir = Path(output_dir or INTERIM_DATA_DIR).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    layers = list(LAYER_ORDER)

    if overwrite is None:
        overwrite = bool(config.get("extraction", {}).get("overwrite_existing", False))

    osm = pyrosm.OSM(str(pbf_path))
    extractors = _get_extractors(osm)
    outputs: dict[str, Path] = {}
    total_start = time.time()

    for layer in layers:
        output_path = output_dir / f"{country_slug}_{layer}.parquet"
        outputs[layer] = output_path

        if output_path.exists() and not overwrite:
            print(f"[skip] {layer}: {output_path}")
            continue

        print(f"[extract] {layer}")
        layer_start = time.time()
        gdf = extractors[layer]()

        if gdf is None:
            raise RuntimeError(f"Pyrosm returned no data for '{layer}'.")

        gdf = _clean_object_cols(gdf)
        gdf.to_parquet(output_path, index=False)

        elapsed = timedelta(seconds=round(time.time() - layer_start))
        print(f"[saved] {len(gdf):,} rows: {output_path}")
        print(f"[time] {elapsed}")

        del gdf
        gc.collect()

    total_elapsed = timedelta(seconds=round(time.time() - total_start))
    print(f"[complete] Total extraction time: {total_elapsed}")
    return outputs