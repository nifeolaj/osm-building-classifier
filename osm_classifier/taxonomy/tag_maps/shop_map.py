import pandas as pd
import re


"""
SHOP_MAP — Complete mapping of all OSM shop tag values
to (Level1_Type, Level2_Subtype)

Level 1 categories:
    commercial

Filter = not a shop or too small to classify
   (abandoned, vacant, no, etc)

Decision rules applied throughout:
   1. All explicit mappings prioritized
   2. Semicolon-combined values -> construct subtype from first parts
   3. Unmapped -> fallback to ('commercial', 'general_retail')

Format: 'osm_value': ('Level1_Type', 'Level2_Subtype')
"""


SHOP_MAP = {

    # ================================================================
    # FOOD AND DRINK RETAIL
    # ================================================================
    
    'bakery': ('commercial', 'food_drink'),
    'general': ('commercial', None),
    

    # ================================================================
    # VEHICLE RELATED
    # ================================================================
    'car_repair': ('commercial', 'retail'),
    'motorcycle_repair': ('commercial', 'retail'),
    'truck_repair': ('commercial', 'retail'),
    'car_bodyshop': ('commercial', 'retail'),
    'car_service': ('commercial', 'retail'),
    'car_detail': ('commercial', 'retail'),
    'car_recycling': ('commercial', 'retail'),
    'towing': ('commercial', 'retail'),

    # ================================================================
    # CLOTHING AND FASHION
    # ================================================================
    'tailor': ('commercial', 'other_service'),
    
    # ================================================================
    # PERSONAL SERVICES
    # ================================================================
    'hairdresser': ('commercial', 'other_service'),
    'beauty': ('commercial', 'other_service'),
    'optician': ('commercial', 'other_service'),
    'tattoo': ('commercial', 'other_service'),
    'massage': ('commercial', 'other_service'),
    'photo': ('commercial', 'other_service'),
    'laundry': ('commercial', 'other_service'),
    'dry_cleaning': ('commercial', 'other_service'),
    'pet_grooming': ('commercial', 'other_service'),
    'dog_parlour': ('commercial', 'other_service'),
    'locksmith': ('commercial', 'other_service'),
    'shoe_repair': ('commercial', 'other_service'),
    'copyshop': ('commercial', 'other_service'),
    'printing': ('commercial', 'other_service'),
    'printshop': ('commercial', 'other_service'),
    'print': ('commercial', 'other_service'),
    'print_shop': ('commercial', 'other_service'),
    'photo_studio': ('commercial', 'other_service'),
    'ironing': ('commercial', 'other_service'),
    'spa': ('commercial', 'other_service'),
    'sauna': ('commercial', 'other_service'),
    'nursing_service': ('commercial', 'office'),
    'guitar_repair': ('commercial', 'other_service'),
    'bicycle_repair': ('commercial', 'other_service'),
    'computer_repair': ('commercial', 'other_service'),
    'repair': ('commercial', 'other_service'),
    'cleaning': ('commercial', 'office'),

    
    
    'tractor_repair': ('commercial', 'retail'),
    
    'tool_hire': ('commercial', 'office'),
    'plant_hire': ('commercial', 'office'),
    'machinery_rental': ('commercial', 'office'),
    'equipment_rental': ('commercial', 'office'),
    
    
    
    
    'logistics': ('commercial', 'office'),
    'transport':            ('commercial', 'office'),
    'joiner':               ('commercial', 'other_service'),
    'carpenter':            ('commercial', 'other_service'),
    'masonry':              ('commercial', 'other_service'),
    'woodwork':             ('commercial', 'other_service'),    
    
   
  
    'fuel':                 ('commercial', 'retail'),  
    
    'catering':             ('commercial', 'food_drink'),
   


    'ski_rental':           ('commercial', 'office'),
    'boat_repair':          ('commercial', 'retail'),  # same energy profile as car repair

    # ==================================================
    # FINANCIAL AND BUSINESS SERVICES
    # ==================================================
    'travel_agency':        ('commercial', 'office'),
    'insurance':            ('commercial', 'office'),
    'estate_agent':         ('commercial', 'office'),
   
    'shipping':             ('commercial', 'office'),

  
    # ==================================================
    # FUNERAL SERVICES
    # ==================================================
    'funeral_directors':    ('commercial', 'office'),
 

    # ==================================================
    # STORAGE AND RENTAL
    # ==================================================
    'storage_rental':       ('commercial', 'office'),
    'rental':               ('commercial', 'office'),
    'car_rental':           ('commercial', 'office'),
    'trailer_rental':       ('commercial', 'office'),
   
    'house_clearance':      ('commercial', 'retail'),

    # ==================================================
    # AMBIGUOUS BUT COMMERCIAL
    # ==================================================
    'disused':              ('filter', 'disused'),  # same
    'outpost':              ('commercial', 'office'),
    'company':              ('commercial', 'office'),
    

    # ==================================================
    # NOT A SHOP — FILTER
    # ==================================================
    'no':                   (None, None),   
    'disused:garden_centre':('filter', 'disused'), 

    # ==================================================
    # SEMICOLON-COMBINED VALUES
    # These are the most common combinations in the data
    # Take the primary type from the first value
    # ==================================================
    'car;car_repair':           ('commercial', 'retail'),
    'car_repair;tyres':         ('commercial', 'retail'),
    'tyres;car_repair':         ('commercial', 'retail'),
    'car_repair;car':           ('commercial', 'retail'),
    'car_repair;car_parts':     ('commercial', 'retail'),
    'car_repair;motorcycle_repair': ('commercial', 'retail'),
    'car_repair;motorcycle_repair;tyres': ('commercial', 'retail'),
    'bakery;pastry':            ('commercial', 'food_drink'),
    'bakery;pastery':           ('commercial', 'food_drink'),
    
    
    
    'dry_cleaning;laundry':     ('commercial', 'other_service'),
    
    'bicycle;bicycle_repair':   ('commercial', 'retail'),
    'bicycle;car_repair':       ('commercial', 'retail'),
    
    'boat_repair;boat_parts':   ('commercial', 'retail'),
    
    'convenience;car_repair':   ('commercial', 'retail'), 
    
    'confectionery;pastry':     ('commercial', 'food_drink'),

    'coffee;tea':               ('commercial', 'food_drink'),
    
    'gas station':              ('commercial', 'retail'),  # space variant
   
    
    'print office':             ('commercial', 'other_service'),
    'driving school':           ('civic', 'school'),
    'event_service':            ('commercial', 'office'),
}


_SHOP_MAP_NORM: dict = {
    re.sub(r'\s+', ' ', k.strip().lower()): v
    for k, v in SHOP_MAP.items()
}


def apply_shop_map(shop_value) -> tuple:
    """
    Map a raw OSM shop tag value to (Level1_Type, Level2_Subtype).

    Parameters
    ----------
    shop_value : str | float | None
        Raw value from the OSM 'shop' tag (e.g. 'flower', 'convenience;car_repair').

    Returns
    -------
    tuple : (Level1_Type, Level2_Subtype)
        Both elements are None if the value is unmappable.

    Lookup strategy
    ---------------
    1. Normalise: lowercase, collapse whitespace, strip trailing semicolons.
    2. Direct lookup in _SHOP_MAP_NORM.
    3. Semicolon fallback: iterate all parts in order, return the first
       that resolves. Unlike the building map, no priority resolution is
       applied — shop tags are generally single-use so first-match is
       sufficient.
    4. Return ('commercial', 'retail') if unmappable.

    Notes
    -----
    - SHOP_MAP returns 2-tuples (no is_mixed field); use apply_building_map
      or apply_building_use_map for mixed-use resolution.
    - Mixed-case keys in SHOP_MAP are normalised at import time.
    """
    if pd.isna(shop_value):
        return (None, None)  # default fallback for missing values

    s = re.sub(r'\s+', ' ', str(shop_value).strip().lower()).rstrip(';')

    # 1. Direct lookup
    if s in _SHOP_MAP_NORM:
        return _SHOP_MAP_NORM[s]

    # 2. Semicolon fallback — try all parts in order
    if ';' in s:
        for part in [p.strip() for p in s.split(';') if p.strip()]:
            if part in _SHOP_MAP_NORM:
                return _SHOP_MAP_NORM[part]

    # 3. Unmappable
    return ('commercial', 'retail')  # default fallback for unmapped values


# ============================================================
# APPLY AND VALIDATE
# ============================================================


if __name__ == '__main__':
    print(f"Total SHOP_MAP entries: {len(SHOP_MAP)}")

    from collections import Counter
    type_counts = Counter(v[0] if v is not None else None for v in SHOP_MAP.values())
    print(f"\nType breakdown:")
    for type_, count in sorted(type_counts.items(), key=lambda x: (-x[1], str(x[0]))):
        print(f"  {str(type_):<30} {count:>5} tag values mapped to this type")
    subtype_counts = Counter(v[1] if v is not None else None for v in SHOP_MAP.values())
    print(f"\nSubtype breakdown:")
    for subtype, count in sorted(subtype_counts.items(), key=lambda x: (-x[1], str(x[0]))):
        print(f"  {str(subtype):<30} {count:>5} tag values mapped to this subtype")
