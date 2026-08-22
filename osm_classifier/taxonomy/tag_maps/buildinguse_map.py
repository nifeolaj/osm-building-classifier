
import pandas as pd
import re

"""
BUILDING_USE_MAP — Complete mapping of all OSM building:use tag values
to (Level1_Type, Level2_Subtype) 

Level 1 categories:
    Residential, Commercial, Industrial, Civic, Agricultural,
    Semi_Commercial, Semi_Industrial, Filter

is_mixed: True  = semicolon-compound tag, treat as mixed use
          False = single-use classification

Filter = not a building or too small to classify
   (bus shelters, bicycle stands, toilets etc)

Format: osm_value': ('Level1_Type', 'Level2_Subtype')
"""

BUILDING_USE_MAP = {

    # ================================================================
    # RESIDENTIAL
    # ================================================================
    
    'restential': ('residential', None),  # fallback for typos
    'residential': ('residential', None),

    # Apartments / multi-unit
    'apartments': ('residential', 'MFH'),
    'apartements': ('residential', 'MFH'),
    'appartments': ('residential', 'MFH'),
    'apartment': ('residential', 'MFH'),

    # Single-family
    'house': ('residential', None),
    'detached': ('residential', 'SFH'),
    'model_home': ('commercial', 'office'),
    'Heuhotel': ('commercial', 'accommodation'),

    # Terraced
    'terrace': ('residential', 'TH'),
    'terasse': ('residential', 'TH'),

    # Dormitory → accommodation (commercial)
    'dormitory': ('commercial', 'accommodation'),
    'student_accommodation': ('commercial', 'accommodation'),
    'Studentenwohnheim St. Anno': ('commercial', 'accommodation'),

    # Nursing / senior homes → care_facility (civic)
    'nursing_home': ('civic', 'care_facility'),
    'nursimg_home': ('civic', 'care_facility'),
    'senior_home': ('civic', 'care_facility'),
    "old_people's_home": ('civic', 'care_facility'),
    'immigrant_home': ('civic', 'care_facility'),
    'Behinderten-Wohnstaette': ('civic', 'care_facility'),

    # Generic residential
    'residental': ('residential', None),

    # Mixed residential
    'residential;apartments': ('residential', 'MFH'),
    'residential;garage': ('residential', 'SFH'),
    'garage;residential': ('residential', 'SFH'),

    # ================================================================
    # COMMERCIAL
    # ================================================================
    
    'commercial': ('commercial', None),

    # Offices
    'office': ('commercial', 'office'),
    'Office': ('commercial', 'office'),
    'Office building': ('commercial', 'office'),
    'offices': ('commercial', 'office'),
    'executive': ('commercial', 'office'),
    'administration': ('commercial', 'office'),
    'administrative': ('commercial', 'office'),
    'travel_agency': ('commercial', 'office'),

    # Retail
    'retail': ('commercial', 'retail'),
    'shop': ('commercial', 'retail'),
    'ticket-shop': ('commercial', 'retail'),
    'grocery_store': ('commercial', 'retail'),
    'supermarket': ('commercial', 'retail'),

    # Accommodation
    'hotel': ('commercial', 'accommodation'),
    'hostel': ('commercial', 'accommodation'),
    'guest_house': ('commercial', 'accommodation'),

    # Food & drink
    'restaurant': ('commercial', 'food_drink'),
    'foodservice': ('commercial', 'food_drink'),
    'gastronomy': ('commercial', 'food_drink'),
    'canteen': ('commercial', 'food_drink'),

    # Personal services
    'sauna': ('commercial', 'other_service'),
    'massage_studio': ('commercial', 'other_service'),

    # Vehicle services
    'car_wash': ('commercial', 'retail'),
    'car_repair': ('commercial', 'retail'),
    'fuel_station': ('commercial', 'retail'),

    # Entertainment
    'nightclub': ('commercial', 'food_drink'),
    'bowling alley': ('civic', 'recreation'),
    'wedding venue': ('civic', 'community'),
    'event_location': ('civic', 'community'),
    'event_venue': ('civic', 'community'),
    'events_venue': ('civic', 'community'),

    # Mixed commercial (office + commercial)
    'office;commercial': ('commercial', 'office'),

    # Mixed commercial (restaurant + retail)
    'restaurant;retail': ('commercial', 'food_drink'),
    'restaurant; fast_food;': ('commercial', 'food_drink'),

    # ================================================================
    # INDUSTRIAL
    # ================================================================
    
    # Generic industrial
    'industrial': ('industrial', None),

    # Manufacturing / production
    'factory': ('industrial', 'manufacturing'),
    'manufacture': ('industrial', 'manufacturing'),
    'works': ('industrial', 'manufacturing'),
    'work': ('industrial', 'manufacturing'),
    'bottling': ('industrial', 'manufacturing'),
    'grist mill': ('industrial', 'manufacturing'),

    # Chemical / heavy industry
    'chemical': ('industrial', 'manufacturing'),

    # Utilities / energy / water
    'Gasversorgung': ('industrial', 'utilities'),
    'Sauerstoffanlage': ('industrial', 'utilities'),
    'water treatment': ('industrial', 'utilities'),
    'pumping_station': ('industrial', 'utilities'),
    'electricity': ('industrial', 'utilities'),
    'electrical installationl': ('industrial', 'utilities'),
    'transformer_station': ('industrial', 'utilities'),
    'power transformer': ('industrial', 'utilities'),
    'Wasserhochbehälter': ('industrial', 'utilities'),

    # Logistics / transport
    'logistics': ('industrial', 'storage'),
    'transport company': ('commercial', 'office'),
    'transportation': ('transportation', None),

    # Storage / warehousing
    'warehouse': ('industrial', 'storage'),
    'cold_store': ('industrial', 'storage'),
    'boat_storage': ('filter', None),

    
    # Mixed industrial
    'industrial;storage': ('industrial', 'storage'),

    
    # Industrial + office → commercial (office)
    'office;industrial': ('industrial', None),

    # ================================================================
    # CIVIC
    # ================================================================

    # Government / administration
    'public': ('civic', None),
    'government': ('civic', 'government_office'),
    'gouverment': ('civic', 'government_office'),
    'civic': ('civic', None),
    'civc': ('civic', None),
    'register office': ('civic', 'government_office'),

    # Judicial / legal
    'judicial': ('civic', 'government_office'),
    'courthouse': ('civic', 'government_office'),
    'jail': ('civic', 'government_office'),
    'townhall': ('civic', 'government_office'),

    # Schools / education
    'school': ('civic', 'school'),
    'Kindergarten': ('civic', 'kindergarten'),
    'kindergarten': ('civic', 'kindergarten'),
    'kindergarden': ('civic', 'kindergarten'),
    'kindergarten; school': ('civic', 'kindergarten'),
    'kindergarten;public': ('civic', 'kindergarten'),
    'music_school': ('civic', 'school'),
    'riding_school': ('agricultural', 'equestrian'),
    'education': ('civic', 'school'),
    'Lehrsaalgebäude': ('civic', 'school'),
    'Aula': ('civic', 'school'),

    # Higher education / research
    'university': ('civic', 'higher_ed'),
    'college': ('civic', 'higher_ed'),
    'academy': ('civic', 'school'),
    'research': ('civic', 'research'),
    'laboratory': ('civic', 'higher_ed'),

    # Libraries
    'library': ('civic', 'cultural'),
    'library_stack': ('civic', 'cultural'),

    # Healthcare
    'hospital': ('civic', 'hospital'),
    'medical': ('civic', 'clinic'),
    'medic': ('civic', 'clinic'),
    'clinic': ('civic', 'clinic'),
    'healthcare': ('civic', 'clinic'),
    'doctors': ('civic', 'clinic'),
    'pharmacy': ('commercial', 'retail'),
    'medical vet.': ('civic', 'clinic'),

    # Social facilities
    'social_facility': ('civic', 'care_facility'),
    'social': ('civic', 'community'),
    'Jugendzentrum ev. Gemeinde': ('civic', 'community'),
    'young people club': ('civic', 'community'),
    'community_centre': ('civic', 'community'),
    'club': ('civic', 'community'),
    'club_house': ('civic', 'community'),
    'association': ('civic', 'community'),
    'Vereinsheim': ('civic', 'community'),
    
    # Sports / recreation
    'gymnasium': ('civic', 'recreation'),
    'sport': ('civic', 'recreation'),
    'Sport': ('civic', 'recreation'),
    'sports': ('civic', 'recreation'),
    'sports_centre': ('civic', 'recreation'),
    'swimming': ('civic', 'recreation'),
    'skiing': ('civic', 'recreation'),
    'leisure': ('civic', 'recreation'),

    # Religious
    'religious': ('civic', 'religious'),
    'religigious': ('civic', 'religious'),
    'religion': ('civic', 'religious'),
    'church': ('civic', 'religious'),
    'mosque': ('civic', 'religious'),
    'synagogue': ('civic', 'religious'),
    'temple': ('civic', 'religious'),
    'cathedral': ('civic', 'religious'),
    'place_of_worship': ('civic', 'religious'),
    'parsonage': ('residential', 'SFH'),
    'presbytery': ('residential', 'SFH'),

    # Cultural / arts
    'museum': ('civic', 'cultural'),
    'museum (+ more)': ('civic', 'cultural'),
    'gallery': ('civic', 'cultural'),
    'exhibition': ('civic', 'cultural'),
    'exhibition_hall': ('civic', 'cultural'),
    'theatre': ('civic', 'cultural'),
    'cultural': ('civic', 'cultural'),
    'culture': ('civic', 'cultural'),
    'Kuenstleratelier': ('civic', 'cultural'),
    'arts_centre': ('civic', 'cultural'),

    # Funeral
    'funeral_hall': ('civic', 'community'),
    'funeral_parlor': ('civic', 'community'),
    'parking': ('transportation', 'parking'),
    
    # Transportation (civic context)
    'train_station': ('transportation', 'train_station'),

    # Mixed civic
    'civic;leisure': ('civic', None),
    'office;education': ('civic', 'school'),
    'office;education;research': ('civic', 'research'),
    'education;research': ('civic', 'research'),
    'education;commercial': ('civic', 'school'),
    'religious;gathering': ('civic', 'religious'),
    'service;museum': ('civic', 'cultural'),
    'leisure;sport': ('civic', 'recreation'),

    # Special civic cluster
    'HBG, Bibliothek, Frisoer': ('civic', 'community'),

    # ================================================================
    # AGRICULTURAL
    # ================================================================
 
    # Generic agricultural
    'agricultural': ('agricultural', None),
    'agriculture': ('agricultural', None),

    # Farms
    'farm': ('residential', 'SFH'),

    
    # Barns / auxiliary
    'barn': ('agricultural', 'farm_auxiliary'),
    'auxiliary': ('agricultural', 'farm_auxiliary'),

    # Equestrian
    'stable': ('agricultural', 'equestrian'),
    'stabile': ('agricultural', 'equestrian'),
    'stable;riding_hall': ('agricultural', 'equestrian'),
    'lunge': ('filter', None),
    'equestrian': ('agricultural', 'equestrian'),
    'equastrian': ('agricultural', 'equestrian'),

    # Animal keeping
    'cattle stable': ('agricultural', 'animal_keeping'),
    'cowshed': ('agricultural', 'animal_keeping'),
    'livestock': ('agricultural', 'animal_keeping'),
    'sty': ('agricultural', 'animal_keeping'),
    'henhouse': ('agricultural', 'animal_keeping'),
    'goat_shed': ('agricultural', 'animal_keeping'),

    # Greenhouse
    'greenhouse': ('agricultural', 'greenhouse'),

    # Hunting
    'hunting_lodge': ('commercial', 'accommodation'),

    # Mixed agricultural
    'sport;agriculture': ('agricultural', 'equestrian'),
    'cultural, agricultural': ('agricultural', None),

    # Residential + agricultural → residential (your rule)
    'residential;agricultural': ('residential', 'SFH'),

    # ================================================================
    # SEMI-COMMERCIAL — residential base + commercial component
    # Stage 1 direct classifications, no ML needed
    # ================================================================
   
    # Residential + commercial (generic)
    'residential;commercial': ('semi_commercial', 'residential_commercial'),
    'residential; commercial': ('semi_commercial', 'residential_commercial'),
    'residential, commercial': ('semi_commercial', 'residential_commercial'),
    'residential,commercial': ('semi_commercial', 'residential_commercial'),
    'commercial;residential': ('semi_commercial', 'residential_commercial'),

    # Residential + retail
    'residential;retail': ('semi_commercial', 'residential_retail'),
    'residential; retail': ('semi_commercial', 'residential_retail'),
    'residential, store': ('semi_commercial', 'residential_retail'),
    'retail;residential': ('semi_commercial', 'residential_retail'),

    # Residential + shop
    'residential;shop': ('semi_commercial', 'residential_retail'),

    # Residential + office
    'residential;office': ('semi_commercial', 'residential_office'),
    'residential; office': ('semi_commercial', 'residential_office'),
    'residential, office': ('semi_commercial', 'residential_office'),
    'office;residential': ('semi_commercial', 'residential_office'),
    'office+residential': ('semi_commercial', 'residential_office'),
    'apartments;office': ('semi_commercial', 'residential_office'),

    # Residential + commercial (apartments)
    'apartments;commercial': ('semi_commercial', 'residential_commercial'),

    # Residential + restaurant / gastronomy
    'apartments;gastronomy': ('semi_commercial', 'residential_food_drink'),
    'residential, pub': ('semi_commercial', 'residential_food_drink'),
    'residential, restaurant': ('semi_commercial', 'residential_food_drink'),
    'restaurant,residential': ('semi_commercial', 'residential_food_drink'),

    # Residential + service
    'residential, service': ('semi_commercial', 'residential_commercial'),

    # Residential + hotel → commercial 
    'residential, hotel': ('commercial', 'accommodation'),
    'hotel;residential': ('commercial', 'accommodation'),

    # Hotel + office → commercial
    'hotel;office': ('commercial', 'accommodation'),

    # Office + shop (pure commercial)
    'office;shop': ('commercial', 'retail'),

    # Multi-mixed (retail + residential + commercial)
    'retail;residential;commercial': ('semi_commercial', 'residential_retail'),
    'commercial;residential;retail': ('semi_commercial', 'residential_retail'),

    # Residential + commercial + industrial → still semi-commercial 
    'residential;commercial;industrial': ('semi_commercial', 'residential_commercial'),

    # Residential + office + shop
    'residential, office, shop': ('semi_commercial', 'residential_retail'),

    # Residential + artistic (no commercial subtype)
    'residential, artistically': ('residential', None),

    # Residential + medical
    'commerical;medical;residential': ('semi_commercial', 'residential_clinic'),

    # Toilet + retail → commercial
    'toilet;retail': ('commercial', 'retail'),

    # Residential + offices (plural)
    'residential;offices': ('semi_commercial', 'residential_office'),

    # ================================================================
    # SEMI-INDUSTRIAL — flag for spatial investigation
    # ================================================================
    'residential;industrial':       (None, None),  
    'industrial;residential':       (None, None),
    'residential;industrial;government':(None, None),
    'residential;industrial;retail':(None, None),
    'residential;industrial;office':(None, None),
    'residential;industrial;storage':(None, None),
    'public;residential;industrial':(None, None),

    # ================================================================
    # PUBLIC-RESIDENTIAL 
    # ================================================================

    # Civic + residential → civic
    'public;residential': ('semi_commercial', 'residential_civic'),
    'public; residential': ('semi_commercial', 'residential_civic'),
    'residential;civic': ('semi_commercial', 'residential_civic'),

    'residential;university': ('commercial', 'accommodation'),
    'residential;university;retail': ('semi_commercial', 'residential_retail'),
    'education;residential': ('commercial', 'accommodation'),

    # Residential + medical → semi_commercial.residential_clinic
    'residential;medical': ('semi_commercial', 'residential_clinic'),
    'residential;doctor': ('semi_commercial', 'residential_clinic'),

    # Residential + kindergarten → semi_commercial.residential_kindergarten
    'residential;kindergarten': ('semi_commercial', 'residential_kindergarten'),

    # Residential + education + commercial → semi_commercial.residential_school
    'residential;education;commercial': ('semi_commercial', 'residential_school'),

    # Residential + gathering → residential (no subtype)
    'residential;gathering': ('residential', None),

    # Supermarket + residential + kindergarten → semi_commercial.residential_retail_kindergarten
    'supermarket;residential;kindergarten': ('semi_commercial',  'residential_commercial'),

    # ================================================================
    # FILTER
    # ================================================================
    
    # Garages / car storage
    'garage': ('filter', None),
    'garages': ('filter', None),
    'carport': ('filter', None),
    'car_port': ('filter', None),

    # Small non-habitable structures
    'shed': ('filter', None),
    'roof': ('filter', None),
    'stairway': ('filter', None),
    'chimney': ('filter', None),
    'gate': ('filter', None),
    'sockel': ('filter', None),
    'pavilion': ('civic', 'recreation'),
    'shelter': ('filter', None),
    'utility': ('filter', None),

    # Toilets
    'toilets': ('filter', None),
    'toilet': ('filter', None),

    # Parking / transport micro‑structures
    'bicycle_parking': ('filter', None),
    'bus_stop': ('filter', None),
    'boat': ('filter', None),
    'look-out': ('filter', None),
    'species_protection_tower': ('filter', None),
    'warm-up_room': ('filter', None),
    'decorative': ('filter', None),
    'ventilation': ('filter', None),
    'water_park': ('civic', 'recreation'),

    # Disused / abandoned
    'disused': ('filter', 'disused'),
    'abandoned': ('filter', 'disused'),
    'deserted': ('filter', 'disused'),
    'unused': ('filter', 'disused'),
    'vacant': ('filter', 'disused'),
    'closed': ('filter', 'disused'),

    # Special case: kitchen → commercial.canteen
    'kitchen': ('commercial', 'food_drink'),
}

# ============================================================  
# BUILDING USE MAP FUNCTION
# ============================================================

# Normalise map once at module load — handles mixed-case keys in BUILDING_MAP
_BUILDING_USE_MAP_NORM: dict = {
    re.sub(r'\s+', ' ', k.strip().lower()): v
    for k, v in BUILDING_USE_MAP.items()
}



def _normalize(value) -> str:
    """Lowercase, collapse whitespace, strip trailing semicolons."""
    s = str(value).strip().lower()
    return re.sub(r'\s+', ' ', s).rstrip(';')


def apply_building_use_map(use_value) -> tuple:
    """
    Map a raw OSM building tag value to (Level1_Type, Level2_Subtype, is_mixed).

    Parameters
    ----------
    use_value : str | float | None
        Raw value from the OSM 'building' tag (e.g. 'residential', 'retail;office').

    Returns
    -------
    tuple : (Level1_Type, Level2_Subtype)
        - Level1_Type  : top-level category string, or None if unmappable
        - Level2_Subtype : subtype string, or None
    """
    if pd.isna(use_value):
        return (None, None)

    s = _normalize(use_value)

    # Direct lookup
    if s in _BUILDING_USE_MAP_NORM:
        return _BUILDING_USE_MAP_NORM[s]
    
    # Unmappable
    return (None, None)


# ============================================================
# VALIDATION BLOCK
# ============================================================
if __name__ == '__main__':
    total = len(BUILDING_USE_MAP)
    counts = {}
    
    for v in BUILDING_USE_MAP.values():
        counts[v[0]] = counts.get(v[0], 0) + 1
        
    # Safely handle mixed_c in case a tuple is accidentally too short
    mixed_c = sum(1 for v in BUILDING_USE_MAP.values() if len(v) > 2 and v[2])

    print("BUILDING_USE_MAP SUMMARY")
    print(f"  Total explicit mappings : {total}")
    print("-" * 30)
    
    # The Fix: key=lambda x: str(x) forces Python to sort None as "None"
    for cat in sorted(counts, key=lambda x: str(x)):
        print(f"  {str(cat):<20}: {counts[cat]}")
    print("-" * 30)
    print(f"  Mixed-use entries     : {mixed_c}\n")
    
    all_subtypes = sorted(set(v[1] for v in BUILDING_USE_MAP.values() if len(v) > 1 and v[1] is not None))
    print(f"All Level 2 subtypes ({len(all_subtypes)} total):")
    for s in all_subtypes:
        print(f"  - {s}")
