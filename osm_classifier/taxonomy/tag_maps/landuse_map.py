"""Map OSM landuse values to building taxonomy classes."""

import pandas as pd

LANDUSE_MAP = {
    "residential": ("residential", None),
    "cottage_settlement": ("residential", "SFH"),
    "suburb": ("residential", None),

    "resort": ("commercial", None),
    "offices": ("commercial", "office"),
    "retail": ("commercial", "retail"),
    "commercial": ("commercial", None),
    "car_sale": ("commercial", "retail"),
    "fuel": ("commercial", "retail"),

    "warehouse": ("industrial", "storage"),
    "storage": ("industrial", "storage"),
    "storage_depot": ("industrial", "storage"),
    "storage_tank": ("industrial", "storage"),
    "material_storage": ("industrial", "storage"),
    "tanker_terminal": ("industrial", None),
    "industrial": ("industrial", None),
    "quarry": ("industrial", "manufacturing"),
    "mine": ("industrial", "manufacturing"),
    "peat_cutting": ("industrial", "manufacturing"),
    "wastewater_plant": ("industrial", "utilities"),
    "water_storage": ("industrial", "utilities"),
    "power": ("industrial", "utilities"),
    "hydro": ("industrial", "utilities"),

    "military": ("military", None),

    "farmland": ("agricultural", None),
    "meadow": ("agricultural", None),
    "orchard": ("agricultural", None),
    "farmyard": ("agricultural", None),
    "plant_nursery": ("agricultural", None),
    "allotments": ("agricultural", None),
}


def apply_landuse_map(value) -> tuple[str | None, str | None]:
    """Return zone L1 and L2 for an OSM landuse value."""
    if pd.isna(value):
        return None, None

    value = str(value).strip().lower()
    return LANDUSE_MAP.get(value, (None, None))