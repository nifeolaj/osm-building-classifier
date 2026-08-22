"""
Configuration loading and merging for the OSM Building Classifier.

The configuration system has two levels:
1. configs/base.yaml
   Contains shared settings required by the general pipeline.
2. configs/countries/<country>.yaml
   Contains optional country-specific metadata, such as
   the country name, Geofabrik download region, projected CRS, or model
   location.

Country files may override only the top-level sections listed under 'country_pack.overridable_keys'

This prevents country-specific settings from silently changing shared classification logic.

A country configuration file is not required. When no file exists, the
base configuration is used. Country information is then supplied to the
pipeline at runtime.
"""

from __future__ import annotations
import copy
import warnings
from pathlib import Path
from typing import Any
import yaml
from osm_classifier.paths import CONFIGS_DIR, COUNTRY_CONFIGS_DIR


Config = dict[str, Any]


def _read_yaml(path: Path) -> Config:
    """
    Read a YAML configuration file and return a dictionary.

    Parameters
    ----------
    path: path to the YAML configuration file.

    Returns
    -------
    dict: parsed configuration.

    Raises FileNotFoundError if the configuration file does not exist and 
    ValueError if the YAML file does not contain a dictionary.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if not isinstance(config, dict):
        raise ValueError(
            f"Configuration must contain a dictionary at its root: {path}"
        )

    return config

def _normalise_country_name(country: str) -> str:
    """
    Convert a country name into the expected configuration filename.

    Examples
    --------
    Germany -> germany
    United Kingdom -> united_kingdom
    united-kingdom -> united_kingdom
    """
    country_key = country.strip().lower()
    country_key = country_key.replace("-", "_")
    country_key = "_".join(country_key.split())

    if not country_key:
        raise ValueError("Country name cannot be empty.")

    return country_key



def _deep_merge(base: Config, override: Config, allowed_keys: set[str], path: str = "",) -> Config:
    """
    Recursively merge a country configuration into the base configuration.

    Only top-level sections listed in ``allowed_keys`` may be overridden.
    Disallowed settings are ignored with a warning.

    Parameters
    ----------
    base: shared base configuration.
    override: country-specific configuration.
    allowed_keys: top-level configuration sections that country files may override.
    path: internal path used for warning messages during recursive merging.

    Returns
    -------
    dict: merged configuration.
    """
    merged = copy.deepcopy(base)

    for key, value in override.items():
        full_path = f"{path}.{key}" if path else key
        top_level_key = full_path.split(".", maxsplit=1)[0]

        if top_level_key not in allowed_keys:
            warnings.warn(
                (
                    f"Country configuration sets '{full_path}', but "
                    f"'{top_level_key}' is not listed in "
                    "country_pack.overridable_keys. Ignoring this value."
                ),
                stacklevel=2,
            )
            continue

        existing_value = merged.get(key)
        
        if isinstance(existing_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(base=existing_value, override=value,
                allowed_keys=allowed_keys, path=full_path,)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


def load_config(country: str | None = None, *, required: bool = True) -> dict:
    """Load base.yaml and optionally merge a country configuration."""
    base_path = CONFIGS_DIR / "base.yaml"
    base_config = _read_yaml(base_path)

    if country is None:
        return copy.deepcopy(base_config)

    country_key = _normalise_country_name(country)
    country_path = COUNTRY_CONFIGS_DIR / f"{country_key}.yaml"

    if not country_path.exists():
        if required:
            raise FileNotFoundError(
                f"Country config not found: {country_path}"
            )
        return copy.deepcopy(base_config)

    country_config = _read_yaml(country_path)
    allowed_keys = set(
        base_config.get("country_pack", {}).get("overridable_keys", [])
    )

    if not allowed_keys:
        raise ValueError(
            "base.yaml must define at least one section under "
            "country_pack.overridable_keys."
        )

    return _deep_merge(
        base=base_config,
        override=country_config,
        allowed_keys=allowed_keys,
    )