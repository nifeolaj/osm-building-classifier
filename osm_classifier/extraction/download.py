"""
Locate or download an OpenStreetMap PBF file.

The pipeline accepts OSM data in several ways:

1. An existing local PBF path.
2. An explicit Geofabrik region, such as ``europe/germany``.
3. A continent and country combination.
4. A Geofabrik region stored in an optional country configuration.

This module only obtains the PBF file. Extraction of buildings, land use,
POIs, roads, and other layers is handled separately in osm_extract.py.
"""

from __future__ import annotations
import shutil
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from osm_classifier.paths import RAW_DATA_DIR

Config = dict[str, Any]

DEFAULT_GEOFABRIK_BASE_URL = "https://download.geofabrik.de"


def _normalise_url_slug(value: str) -> str:
    """
    Convert a country or continent name into a URL-friendly slug.

    Examples
    --------
    "Germany" -> "germany"
    "North America" -> "north-america"
    "united_kingdom" -> "united-kingdom"
    """
    slug = value.strip().lower()
    slug = slug.replace("_", "-")
    slug = "-".join(slug.split())

    if not slug:
        raise ValueError("A country or region name cannot be empty.")

    return slug


def normalise_geofabrik_region(region: str) -> str:
    """
    Normalise a Geofabrik region while preserving its path structure.

    Examples
    --------
    "Europe/Germany" -> "europe/germany"
    "north america/canada" -> "north-america/canada"
    """
    parts = [_normalise_url_slug(part) for part in region.strip("/").split("/") if part.strip()]

    if not parts:
        raise ValueError("Geofabrik region cannot be empty.")

    return "/".join(parts)


def resolve_geofabrik_region(*, country: str | None = None, continent: str | None = None,
    geofabrik_region: str | None = None, config: Config | None = None,) -> str:
    """
    Determine the Geofabrik region to use.

    Priority
    --------
    1. Explicit ``geofabrik_region``.
    2. Explicit ``continent`` and ``country``.
    3. ``osm.geofabrik_region`` from the configuration.

    Returns
    -------
    str: Normalised Geofabrik region, such as ``europe/germany``.

    Raises ValueError if the region cannot be determined.
    """
    if geofabrik_region is not None:
        return normalise_geofabrik_region(geofabrik_region)

    if continent is not None and country is not None:
        continent_slug = _normalise_url_slug(continent)
        country_slug = _normalise_url_slug(country)
        return f"{continent_slug}/{country_slug}"

    if config is not None:
        configured_region = (config.get("osm", {}).get("geofabrik_region"))

        if configured_region:
            return normalise_geofabrik_region(configured_region)

    raise ValueError(
        "Unable to determine the Geofabrik region. Provide one of:\n"
        "  - geofabrik_region='europe/germany'\n"
        "  - continent='europe' and country='germany'\n"
        "  - a country configuration containing osm.geofabrik_region\n"
        "Alternatively, provide an existing pbf_path."
    )


def build_geofabrik_url(region: str, *, base_url: str = DEFAULT_GEOFABRIK_BASE_URL,) -> str:
    """
    Construct the Geofabrik download URL for a region.

    Example: europe/germany ->
    https://download.geofabrik.de/europe/germany-latest.osm.pbf
    """
    normalised_region = normalise_geofabrik_region(region)
    clean_base_url = base_url.rstrip("/")

    return (f"{clean_base_url}/{normalised_region}-latest.osm.pbf")


def _default_output_filename(*, country: str | None, region: str,) -> str:
    """
    Create the local PBF filename.

    The supplied country name is preferred. If no country is supplied,
    the final part of the Geofabrik region is used.
    """
    if country is not None:
        name_slug = _normalise_url_slug(country)
    else:
        name_slug = normalise_geofabrik_region(region).split("/")[-1]

    return f"{name_slug}-latest.osm.pbf"


def download_file(url: str, destination: Path, *, overwrite: bool = False,) -> Path:
    """
    Download a file safely.

    The file is first written with a ``.part`` suffix. It is renamed to
    the final destination only after the download succeeds.

    Parameters
    ----------
    url: source URL.
    destination: final local file path.
    overwrite: replace an existing file when True.

    Returns
    -------
    pathlib.Path: path to the downloaded file.
    """
    destination = destination.expanduser().resolve()

    if destination.exists() and not overwrite:
        print(f"Using existing file: {destination}")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(destination.suffix + ".part")

    if temporary_path.exists():
        temporary_path.unlink()

    request = Request(url, headers={
            "User-Agent": (
                "osm-building-classifier/0.1 "
                "(OpenStreetMap research pipeline)")},)

    print(f"Downloading: {url}")
    print(f"Destination: {destination}")

    try:
        with urlopen(request) as response:
            with temporary_path.open("wb") as output_file:
                shutil.copyfileobj(response, output_file, length=1024 * 1024,)
        temporary_path.replace(destination)

    except (HTTPError, URLError, OSError) as error:
        if temporary_path.exists():
            temporary_path.unlink()

        raise RuntimeError(
            f"Failed to download OSM data from '{url}': {error}"
        ) from error

    print(f"Download complete: {destination}")

    return destination


def obtain_osm_pbf(*, country: str | None = None, pbf_path: str | Path | None = None, 
                   continent: str | None = None, geofabrik_region: str | None = None, 
                   config: Config | None = None, output_dir: str | Path | None = None, 
                   overwrite: bool | None = None,) -> Path:
    """
    Return an existing OSM PBF or download one from Geofabrik.

    Input priority
    --------------
    1. Existing ``pbf_path``.
    2. Explicit ``geofabrik_region``.
    3. Explicit ``continent`` and ``country``.
    4. Geofabrik metadata from the configuration.

    Parameters
    ----------
    country: country name used for the output filename.
    pbf_path: existing local OSM PBF file. When supplied, no download occurs.
    continent: geofabrik continent or top-level region, such as ``europe``.
    geofabrik_region: complete Geofabrik path, such as ``europe/germany``.
    config: merged pipeline configuration.
    output_dir: directory for downloaded files. Defaults to ``data/raw``.
    overwrite: replace an existing downloaded PBF.
        If None, the value is read from
        ``config["extraction"]["overwrite_existing"]`` where available.

    Returns
    -------
    pathlib.Path: local path to the OSM PBF.
    """
    if pbf_path is not None:
        local_path = Path(pbf_path).expanduser().resolve()

        if not local_path.exists():
            raise FileNotFoundError(
                f"Provided OSM PBF does not exist: {local_path}"
            )

        if not local_path.is_file():
            raise ValueError(
                f"Provided OSM PBF path is not a file: {local_path}"
            )

        print(f"Using supplied OSM PBF: {local_path}")
        return local_path

    region = resolve_geofabrik_region(country=country, continent=continent,
        geofabrik_region=geofabrik_region, config=config,)
    base_url = DEFAULT_GEOFABRIK_BASE_URL

    if config is not None:
        base_url = (config.get("osm", {}).get("download_base_url", base_url))

    if overwrite is None:
        overwrite = False

        if config is not None:
            overwrite = bool(config.get("extraction", {}).get("overwrite_existing", False))

    destination_directory = (Path(output_dir)
        if output_dir is not None
        else RAW_DATA_DIR
    )

    filename = _default_output_filename(country=country, region=region,)
    destination = destination_directory / filename
    url = build_geofabrik_url(region, base_url=base_url,)

    return download_file(url=url, destination=destination, overwrite=overwrite,)