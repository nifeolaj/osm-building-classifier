"""Map OSM tourism values to building classes."""

import re
import pandas as pd

TOURISM_MAP = {
    "hotel": ("commercial", "accommodation"),
    "hostel": ("commercial", "accommodation"),
    "guest_house": ("commercial", "accommodation"),
    "apartment": ("commercial", "accommodation"),
    "chalet": ("commercial", "accommodation"),
    "alpine_hut": ("commercial", "accommodation"),
    "motel": ("commercial", "accommodation"),
    "guest_house;apartment": ("commercial", "accommodation"),
    "apartment;guest_house": ("commercial", "accommodation"),
    "hunting_lodge": ("commercial", "accommodation"),
    "museum": ("civic", "cultural"),
    "gallery": ("civic", "cultural"),
    "zoo": ("civic", "cultural"),
    "theme_park": ("civic", "recreation"),
    "aquarium": ("civic", "cultural"),
}

_TOURISM_MAP = {
    re.sub(r"\s+", " ", key.strip().lower()): value
    for key, value in TOURISM_MAP.items()
}


def apply_tourism_map(value) -> tuple[str | None, str | None]:
    if pd.isna(value):
        return None, None

    value = re.sub(r"\s+", " ", str(value).strip().lower()).rstrip(";")
    return _TOURISM_MAP.get(value, (None, None))