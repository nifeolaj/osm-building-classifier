# ============================================================
# BUILDING MAP — building tag → classification
# Format: 'osm_value': ('Level1_Type', 'Level2_Subtype', is_mixed)
# ============================================================

import pandas as pd
import re

"""
BUILDING_MAP — Complete mapping of all OSM building tag values
to (Level1_Type, Level2_Subtype, is_mixed) 

Level 1 categories:
    Residential, Commercial, Industrial, Civic, Agricultural,
    Transportation, Military, Semi_Commercial, Filter

is_mixed: True  = semicolon-compound tag, treat as mixed use
          False = single-use classification

Filter = not a building or too small to classify
   (bus shelters, bicycle stands, toilets etc)

Processing rules:
   1. Normalise raw value: strip, collapse whitespace
      before lookup
   2. Mixed-use compound values are mapped directly here
      because the combination carries meaning
   3. When building:use conflicts with building tag, prefer
      building:use EXCEPT for residential;industrial which
      should be flagged for spatial investigation first
   4. Filter = not a classifiable building for energy purposes

Coverage strategy:
- All values are explicitly mapped with a direct lookup in AMENITY_MAP first
- For unmapped values, apply a series of fallback rules to try to infer the type:
    - Semicolon-combined values -> take first part
    - Others not in map -> return None

Format: 'osm_value': ('Level1_Type', 'Level2_Subtype', 'is_mixed')
"""

BUILDING_MAP = {

    # ================================================================
    # RESIDENTIAL
    # ================================================================

    # Core residential
    'house': ('residential', None),
    'residential': ('residential', None),
    'apartments': ('residential', 'MFH'),
    'detached': ('residential', 'SFH'),
    'semidetached_house': ('residential', 'SFH'),
    'terrace': ('residential', 'TH'),
    'dormitory': ('commercial', 'accommodation'),
    'bungalow': ('residential', 'SFH'),
    'cabin': ('residential', 'SFH'),
    'static_caravan': ('filter', None),

    # Variants & synonyms
    'dwelling_house': ('residential', None),
    'detached_house': ('residential', 'SFH'),
    'terraced_house': ('residential', 'TH'),
    'terrace_house': ('residential', 'TH'),
    'semidetached': ('residential', 'SFH'),
    'semi_detached': ('residential', 'SFH'),
    'semi-detached': ('residential', 'SFH'),
    'double_house': ('residential', None),
    'row_house': ('residential', 'TH'),
    'flat': ('residential', None),
    'flats': ('residential', 'MFH'),
    'lofts': ('residential', 'MFH'),
    'houseboat': ('filter', None),
    'mobile_home': ('filter', None),
    'stilt_house': ('residential', 'SFH'),
    'log_cabin': ('residential', 'SFH'),
    'chalet': ('residential', 'SFH'),
    'villa': ('residential', 'SFH'),
    'cottage': ('residential', 'SFH'),
    'farmhouse': ('residential', 'SFH'),
    'summer_house': ('filter', None),
    'summerhouse': ('filter', None),
    'holiday_home': ('residential', 'SFH'),
    'garden_house': ('filter', None),
    'allotment_house': ('filter',None),
    'single_apartment': ('residential', None),
    'show_house': ('commercial', 'office'),
    'tiny_house': ('residential', 'SFH'),

    # Typos & case variants
    'terraced': ('residential', 'TH'),
    'appartments': ('residential', 'MFH'),
    'appartements': ('residential', 'MFH'),
    'residental': ('residential', None),
    'detatched': ('residential', 'SFH'),
    'deteched': ('residential', 'SFH'),
    'detachedaddr:city=Südheide': ('residential', 'SFH'),
    'semidetatched house': ('residential', 'SFH'),
    'RESIDENTIAL': ('residential', None),
    'residentisl': ('residential', None),
    'reidentisl': ('residential', None),
    'Wohnhaus': ('residential', None),
    'Freistehendes Mehrfamilienhaus': ('residential', 'MFH'),
    'einzelzimmer,_doppelzimmer_und_appartments': ('residential', 'MFH'),

    # Semicolon combos (residential-dominant)
    'house;residential': ('residential', None),
    'residential;apartments': ('residential', 'MFH'),
    'apartments;residential': ('residential', 'MFH'),
    'detached;residential': ('residential', 'SFH'),
    'detached;yes': ('residential', 'SFH'),
    'house;yes': ('residential', None),
    'yes;house': ('residential', None),
    'residential;yes': ('residential', None),
    'yes;residential': ('residential', None),
    'yes;apartments': ('residential', 'MFH'),
    'apartments;yes': ('residential', 'MFH'),
    'yes;terrace': ('residential', 'TH'),
    'terrace;yes': ('residential', 'TH'),
    'terrace;apartments': ('residential', 'MFH'),
    'semidetached_house;house': ('residential', 'SFH'),
    'residential;garage': ('residential', 'SFH'),
    'roof;semidetached_house': ('residential', 'SFH'),
    'roof;residential': ('residential', None),
    'roof;detached': ('residential', 'SFH'),
    'house;garage': ('residential', 'SFH'),
    'garage;house': ('residential', 'SFH'),
    'garage;residential': ('residential', 'SFH'),
    'garage;detached': ('residential', 'SFH'),
    'residential;garages': ('residential', 'SFH'),

    # Dataset-derived residential forms
    'townhouse': ('residential', 'TH'),
    'block_house': ('residential', None),
    'home': ('residential', 'SFH'),
    'residential;house': ('residential', None),
    'house;barn': ('residential', None),
    'house;apartments': ('residential', 'MFH'),
    'house, semi': ('residential', 'SFH'),
    
    # German variants
    'Hütte': ('filter',None),
    'Blockhaus': ('residential', 'SFH'),
    'Doppelhaus': ('residential', 'SFH'),

    # Rare residential-like tags
    'assisted_living': ('civic', 'care_facility'),
    'juvenile_home': ('civic', 'care_facility'),
    'group_home': ('civic', 'care_facility'),
    'old people\'s home': ('civic', 'care_facility'),
    'religious': ('civic', 'religious'),
    'mortuary': ('civic', 'community'),


    # ================================================================
    # COMMERCIAL
    # ================================================================
    
    # Core commercial
    'commercial': ('commercial', None),
    'retail': ('commercial', 'retail'),
    'office': ('commercial', 'office'),
    'supermarket': ('commercial', 'retail'),
    'shop': ('commercial', 'retail'),
    'guardhouse': ('commercial', 'office'),

    # Hospitality
    'hotel': ('commercial', 'accommodation'),
    'motel': ('commercial', 'accommodation'),
    'hostel': ('commercial', 'accommodation'),
    'inn': ('commercial', 'accommodation'),
    'guest_house': ('commercial', 'accommodation'),
    'guesthouse': ('commercial', 'accommodation'),
    'boarding_house': ('commercial', 'accommodation'),
    'workers_housing': ('commercial', 'accommodation'),
    'hall_of_residence': ('commercial', 'accommodation'),
    'mountain_hut': ('commercial', 'accommodation'),
    'refuge_hut': ('commercial', 'accommodation'),
    # Shelters that are actual buildings → accommodation
    'shelter_building': ('commercial', 'accommodation'),
    'refuge': ('commercial', 'accommodation'),
    'emergency_hut': ('commercial', 'accommodation'),
    'lodge': ('commercial', 'accommodation'),
    'hunting_lodge': ('commercial', 'accommodation'),
    'ski_hut': ('commercial', 'accommodation'),
    'tourist_shelter': ('commercial', 'accommodation'),
    'sauna': ('commercial', 'other_service'),
    'marquee': ('filter', None),
    'column': ('filter', None),
    'henhouse': ('agricultural', 'animal_keeping'),


    # Food & beverage
    'restaurant': ('commercial', 'food_drink'),
    'Restaurant': ('commercial', 'food_drink'),
    'fast_food': ('commercial', 'food_drink'),
    'foodservice': ('commercial', 'food_drink'),
    'cafe': ('commercial', 'food_drink'),
    'bakery': ('commercial', 'food_drink'),
    'pub': ('commercial', 'food_drink'),
    'tavern': ('commercial', 'food_drink'),
    'biergarten': ('commercial', 'food_drink'),

    # Retail & shopping
    'mall': ('commercial', 'retail'),
    'shopping_centre': ('commercial', 'retail'),
    'shopping_mall': ('commercial', 'retail'),
    'market_hall': ('commercial', 'retail'),
    'store': ('commercial', 'retail'),
    'kiosk': ('commercial', 'retail'),
    'vending_machine': ('filter', None),
    'vending_machines': ('filter', None),
    'ladengeschäft': ('commercial', 'retail'),

    # Offices (always → commercial.office)
    'central_office': ('commercial', 'office'),
    'research_office': ('commercial', 'office'),
    'administration': ('commercial', 'office'),
    'administrative': ('commercial', 'office'),
    'forwarding_office': ('commercial', 'office'),
    'post_office': ('commercial', 'office'),
    'ticket_office': ('commercial', 'office'),
    'office;yes': ('commercial', 'office'),
    'office;garages': ('commercial', 'office'),

    # Entertainment & culture (commercial side)
    'cinema': ('civic', 'cultural'),
    'theatre': ('civic', 'cultural'),
    'music_venue': ('civic', 'cultural'),
    'nightclub': ('commercial', 'food_drink'),
    'casino': ('civic', 'recreation'),
    'disco': ('commercial', 'food_drink'),

    # Data centers
    'data_center': ('commercial', 'office'),
    'data_centre': ('commercial', 'office'),
    'datacenter': ('commercial', 'office'),

    # Workshops & services
    'car_wash': ('commercial', 'retail'),
    'carwash': ('commercial', 'retail'),
    'car_cleaning': ('commercial', 'retail'),
    'car_repair': ('commercial', 'retail'),
    'laundry': ('commercial', 'other_service'),

    'logistics': ('industrial', 'storage'),
    'logistic': ('industrial', 'storage'),

    # Semicolon combos (commercial-dominant)
    'commercial;yes': ('commercial', None),
    'retail;yes': ('commercial', 'retail'),
    'yes;commercial': ('commercial', None),
    'yes;retail': ('commercial', 'retail'),
    'retail;roof': ('commercial', 'retail'),
    'retail;commercial;office': ('commercial', 'retail'),
    'commercial;office': ('commercial', 'office'),
    'retail;commercial;office;yes': ('commercial', 'retail'),
    'service;retail': ('commercial', 'retail'),
    'retail;office': ('commercial', 'retail'),
    'roof;retail': ('commercial', 'retail'),
    'roof;commercial': ('commercial', None),

    # Dataset-derived commercial
    'event_center': ('civic', 'community'),
    'showroom': ('commercial', 'retail'),
    'bank': ('commercial', 'office'),
    'pharmacy': ('commercial', 'retail'),
    'studio': ('commercial', 'office'),
    'cafeteria': ('commercial', 'food_drink'),
    'canteen': ('commercial', 'food_drink'),


    # Typos & variants
    'yesoutletstores_direct': ('commercial', 'retail'),
    'supermarkt': ('commercial', 'retail'),
    'reteil': ('commercial', 'retail'),
    'reception': ('commercial', 'office'),

    

    # ================================================================
    # INDUSTRIAL
    # ================================================================
    
    # Core industrial
    'industrial': ('industrial', None),  # generic fallback
    'factory': ('industrial', 'manufacturing'),
    'manufacture': ('industrial', 'manufacturing'),
    'works': ('industrial', 'manufacturing'),


    # Energy & utilities
    'power': ('industrial', 'utilities'),
    'power_station': ('industrial', 'utilities'),
    'powerstation': ('industrial', 'utilities'),
    'powerhouse': ('industrial', 'utilities'),
    'power_plant': ('industrial', 'utilities'),
    'electricity': ('industrial', 'utilities'),
    'substation': ('industrial', 'utilities'),
    'sub_station': ('industrial', 'utilities'),
    'power_substation': ('industrial', 'utilities'),
    'transformer': ('industrial', 'utilities'),
    'transformer_tower': ('industrial', 'utilities'),
    'transformer_house': ('industrial', 'utilities'),
    'transformer_kiosk': ('industrial', 'utilities'),
    'tech_cab': ('industrial', 'utilities'),
    'transformer_building': ('industrial', 'utilities'),
    'Umspannwerk': ('industrial', 'utilities'),
    'generator': ('industrial', 'utilities'),
    'digester': ('industrial', 'utilities'),


    # Water & pumping
    'pumping_station': ('industrial', 'utilities'),
    'sewage_pumping_station': ('industrial', 'utilities'),
    'reservoir': ('filter', None),
    'water_tower': ('industrial', 'utilities'),
    'water_tank': ('industrial', 'utilities'),
    'water_storage': ('industrial', 'utilities'),
    'cistern': ('filter', None),
    'passage': ('filter', None),
    'corridor': ('filter', None),
    'prison': ('civic', 'government_office'),

    # Storage (Option C: always → industrial.storage)
    'warehouse': ('industrial', 'storage'),
    'storage_tank': ('industrial', 'utilities'),
    'cold_store': ('industrial', 'storage'),
    'coldstore': ('industrial', 'storage'),
    'granary': ('agricultural', 'farm_auxiliary'),
    'tank': ('industrial', 'utilities'),
    'bunker_silo': ('filter', None),
    'slurry_tank': ('agricultural', 'farm_auxiliary'),
    'storage_room': ('filter', None),
    'storage_dome': ('industrial', 'utilities'),
    
    # Depots (generic → storage)
    'industrial;warehouse': ('industrial', 'storage'),
    'warehouse;garage': ('industrial', 'storage'),

    # Production buildings
    'brewery': ('industrial', 'manufacturing'),
    'slaughterhouse': ('industrial', 'manufacturing'),
    'dairy': ('industrial', 'manufacturing'),
    'sawmill': ('industrial', 'manufacturing'),
    'production_hall': ('industrial', 'manufacturing'),
    'fermenter': ('industrial', 'utilities'),
    'fermentation_plant': ('industrial', 'utilities'),
    'reactor': ('industrial', 'utilities'),

    
    'boathouse': ('filter', None),
    'ship': ('filter', None),
    'boat': ('filter', None),

    

    # Typos & variants
    'industrial;yes': ('industrial', None),
    'yes;industrial': ('industrial', None),
    'roof;industrial': ('industrial', None),
    'industrial;abandoned': ('industrial', None),
    'abandoned:industrial': ('industrial',None),
    'îndustrial': ('industrial', None),

    # Dataset-derived industrial
    'bunker': ('military', 'bunker'),
    'motorradhalle': ('commercial', 'retail'),
    'lagerhalle,autowerksatt': ('commercial', 'retail'),

    # Mixed industrial
    'industrial;office': ('industrial', None),
    'office;industrial': ('industrial', None),

    # ================================================================
    # CIVIC
    # ================================================================

    # Education
    'school': ('civic', 'school'),
    'kindergarten': ('civic', 'kindergarten'),
    'kindergarden': ('civic', 'kindergarten'),
    'Kindergarten': ('civic', 'kindergarten'),
    'madrasa': ('civic', 'school'),
    'sports_school': ('civic', 'school'),
    'school_assembly_hall': ('civic', 'school'),
    'scool': ('civic', 'school'),

    # Higher education & research
    'university': ('civic', 'higher_ed'),
    'college': ('civic', 'higher_ed'),
    'academy': ('civic', 'school'),
    'laboratory': ('civic', 'higher_ed'),
    'research': ('civic', 'research'),

    # Generic (fallback)
    'education': ('civic', 'school'),
    'educational': ('civic', 'school'),

    # Mixed
    'university;college': ('civic', 'higher_ed'),
    'school;yes': ('civic', 'school'),
    'yes;school': ('civic', 'school'),
    'roof;kindergarten': ('civic', 'kindergarten'),
    'kindergarten;apartments': ('semi_commercial', 'residential_kindergarten'),
    'apartments;kindergarten': ('semi_commercial', 'residential_kindergarten'),

    # Healthcare
    'hospital': ('civic', 'hospital'),

    # Clinics (light medical)
    'clinic': ('civic', 'clinic'),
    'doctors': ('civic', 'clinic'),
    'medical': ('civic', 'clinic'),
    'ambulance_station': ('civic', 'emergency_service'),

    # Care facilities
    'nursing_home': ('civic', 'care_facility'),
    'retirement_home': ('civic', 'care_facility'),
    'old people\'s home': ('civic', 'care_facility'),
    'hospice': ('civic', 'care_facility'),
    'social_facility': ('civic', 'care_facility'),
    'rehabilitation': ('civic', 'care_facility'),

    # Emergency
    'rescue_station': ('civic', 'emergency_service'),

    'childcare': ('civic', 'kindergarten'),
    'clinic;yes': ('civic', 'clinic'),

    # Government / public administration
    'government': ('civic', 'government_office'),
    'civic': ('civic', None),
    'public': ('civic', None),
    'townhall': ('civic', 'government_office'),
    'city_hall': ('civic', 'government_office'),
    'courthouse': ('civic', 'government_office'),
    'public_building': ('civic', None),
    'government_office': ('civic', 'government_office'),
    'tax_office': ('civic', 'government_office'),
    'öffentliches_gebäude': ('civic', 'government_office'),
    'civil': ('civic', 'government_office'),

    'public;yes': ('civic', None),
    'yes;public': ('civic', None),
    'civic;retail': ('commercial', 'retail'),
       
    # Police
    'police': ('civic', 'emergency_service'),
    'police_station': ('civic', 'emergency_service'),
    'policestation': ('civic', 'emergency_service'),

    'fire_station': ('civic', 'emergency_service'),
    'fire_department': ('civic', 'emergency_service'),
    'fire_training_house': ('civic', 'emergency_service'),
    'lifeboat_station': ('civic', 'emergency_service'),
    'funeral_hall': ('civic', 'community'),
    'wayside_shrine': ('filter', None),
    'basilica': ('civic', 'religious'),
    'bell_tower': ('filter', None),
    'sheepfold': ('agricultural', 'animal_keeping'),
    'beehive': ('agricultural', 'animal_keeping'),






    # Military
    'military': ('military', None),
    'barracks': ('military', 'barracks'),
    'barrack': ('military', 'barracks'),

    # Religious
    'church': ('civic', 'religious'),
    'chapel': ('civic', 'religious'),
    'cathedral': ('civic', 'religious'),
    'mosque': ('civic', 'religious'),
    'synagogue': ('civic', 'religious'),
    'temple': ('civic', 'religious'),
    'shrine': ('civic', 'religious'),
    'monastery': ('civic', 'religious'),
    'convent': ('civic', 'religious'),
    'friary': ('civic', 'religious'),
    'cloister': ('civic', 'religious'),
    'pfarrhaus': ('civic', 'religious'),
    'ossuary': ('civic', 'religious'),
    'crypts': ('civic', 'religious'),
    'tomb': ('filter', None),
    'hermitage': ('civic', 'religious'),
    'cemetery_chapel': ('civic', 'religious'),
    'yes;chapel': ('civic', 'religious'),
    'chapel;wayside_chapel': ('civic', 'religious'),
    'de:mausoleum': ('civic', 'religious'),
    'vicarage': ('residential', 'SFH'),
    'embassy': ('civic', 'government_office'),
    'sport': ('civic', 'recreation'),
    'rectory': ('residential', 'SFH'),


    # Community / social
    'community_centre': ('civic', 'community'),
    'community_center': ('civic', 'community'),
    'clubhouse': ('civic', 'community'),
    'association': ('civic', 'community'),
    'Vereinsheim': ('civic', 'community'),
    'Veinsheim': ('civic', 'community'),
    'parish_hall': ('civic', 'community'),
    'youth_hostel': ('commercial', 'accommodation'),
    'pavilion': ('civic', 'recreation'),
    'hall': ('civic', None),
    'assembly_hall': ('civic', None),
    'club': ('civic', 'community'),
    'visitor_center': ('civic', 'community'),
    'visitor_centre': ('civic', 'community'),
    'event_hall': ('civic', 'community'),
    'mourning_hall': ('civic', 'community'),


    # Cultural
    'museum': ('civic', 'cultural'),
    'library': ('civic', 'cultural'),
    'exhibition_hall': ('civic', 'cultural'),
    'exhibition_centre': ('civic', 'cultural'),
    'auditorium': ('civic', None),
    'concert_hall': ('civic', 'cultural'),
    'music_hall': ('civic', 'cultural'),
    'festival_hall': ('civic', 'cultural'),
    'opera_house': ('civic', 'cultural'),
    'culture': ('civic', 'cultural'),
    'tree_house': ('filter', None),
    'stairs': ('filter', None),

    # Sports & recreation
    'sports_hall': ('civic', 'recreation'),
    'sports_centre': ('civic', 'recreation'),
    'sports_center': ('civic', 'recreation'),
    'sports_centre;yes': ('civic', 'recreation'),
    'gymnasium': ('civic', 'recreation'),
    'gym': ('civic', 'recreation'),
    'arena': ('civic', 'recreation'),
    'stadium': ('civic', 'recreation'),
    'stadion': ('civic', 'recreation'),
    'bowling_alley': ('civic', 'recreation'),
    'indoor_swimming_pool': ('civic', 'recreation'),
    'swimming_pool': ('civic', 'recreation'),
    'water_park': ('civic', 'recreation'),
    'pitch': ('filter', None),
    'shooting_stand': ('filter', None),
    'roundpen': ('filter', None),
    'grandstand': ('civic', 'recreation'),
    'castle': ('civic', 'cultural'),


    'presbytery': ('residential', 'SFH'),
    # ================================================================
    # AGRICULTURAL
    # ================================================================
 
    'barn': ('agricultural', 'farm_auxiliary'),
    'cowshed': ('agricultural', 'animal_keeping'),
    'cow_shed': ('agricultural', 'animal_keeping'),
    'pigsty': ('agricultural', 'animal_keeping'),
    'sty': ('agricultural', 'animal_keeping'),
    'livestock': ('agricultural', 'animal_keeping'),
    'agricultural': ('agricultural', None),
    'arbour': ('filter', None),


    'chicken_house': ('agricultural', 'animal_keeping'),
    'chickenhouse': ('agricultural', 'animal_keeping'),
    'duck_house': ('agricultural', 'animal_keeping'),
    'rabbit_hutch': ('agricultural', 'animal_keeping'),
    'Kaninchenstall': ('agricultural', 'animal_keeping'),
    'apiary': ('agricultural', 'animal_keeping'),
    'bee_house': ('agricultural', 'animal_keeping'),
    'animal_house': ('agricultural', 'animal_keeping'),
    'dog_kennel': ('agricultural', 'animal_keeping'),
    'kennels': ('agricultural', 'animal_keeping'),
    'hutch': ('agricultural', 'animal_keeping'),
    'cote': ('agricultural', 'animal_keeping'),

    'stable': ('agricultural', 'equestrian'),
    'horse_shelter': ('agricultural', 'equestrian'),

    'greenhouse': ('agricultural', 'greenhouse'),
    'glasshouse': ('agricultural', 'greenhouse'),
    'nursery': ('agricultural', 'greenhouse'),
    'cultivation': ('agricultural', 'greenhouse'),
    'abandoned:greenhouse': ('filter', 'greenhouse'),
    'farmyard': ('filter', None),  
    'Landwirtschaft Neuenhofe': ('filter', None),
    'farm_house': ('residential', 'SFH'),
    'farm_shop': ('commercial', 'retail'),
    'farm_store': ('commercial', 'retail'),

    'shed': ('filter', None),  # safest assumption
    'farm_auxiliary': ('agricultural', 'farm_auxiliary'),
    'farm': ('residential', 'SFH'),
    'hay_barn': ('agricultural', 'farm_auxiliary'),
    'field_shelter': ('filter', None),
    'tool_shed': ('filter', None),
    'storage_shed': ('filter', None),
    'hofgut': ('filter', None),
    'wine_farm': ('filter', None),
    'shed;carport': ('filter', None),
    'farm_auxiliary;farm': ('agricultural', 'farm_auxiliary'),
    'farm_auxiliary;yes': ('agricultural', 'farm_auxiliary'),

    'house;farm_auxiliary': ('residential', 'SFH'),
    'residential;barn': ('residential', None),
    'riding_hall': ('agricultural', 'equestrian'),

    # ================================================================
    # SEMI-COMMERCIAL — residential base + commercial component
    # Stage 1 direct classifications, no ML needed
    # ================================================================
   

    # Residential + Retail
    'residential;retail': ('semi_commercial', 'residential_retail'),
    'retail;residential': ('semi_commercial', 'residential_retail'),
    'house;retail': ('semi_commercial', 'residential_retail'),
    'retail;house': ('semi_commercial', 'residential_retail'),
    'apartments;retail': ('semi_commercial', 'residential_retail'),
    'retail;apartments': ('semi_commercial', 'residential_retail'),

    # Residential + Commercial
    'residential;commercial': ('semi_commercial', 'residential_commercial'),
    'commercial;residential': ('semi_commercial', 'residential_commercial'),
    'house;commercial': ('semi_commercial', 'residential_commercial'),
    'commercial;house': ('semi_commercial', 'residential_commercial'),
    'apartments;commercial': ('semi_commercial', 'residential_commercial'),
    'commercial;apartments': ('semi_commercial', 'residential_commercial'),

    # Residential + Office
    'residential;office': ('semi_commercial', 'residential_office'),
    'office;residential': ('semi_commercial', 'residential_office'),
    'apartments;office': ('semi_commercial', 'residential_office'),
    'office;apartments': ('semi_commercial', 'residential_office'),

    
    # Commercial + Civic
    'commercial;civic': ('commercial', None),
    'civic;commercial': ('commercial', None),
    'public;commercial;retail': ('commercial', 'retail'),

    # Retail + Office + Commercial mixes
    'commercial;office;retail': ('commercial', 'retail'),

    # Dataset‑specific mixed tags
    'retail; apartments': ('semi_commercial', 'residential_retail'),
    'residential; apartments': ('residential', 'MFH'),
    'garage;apartments': ('residential', 'MFH'),  
    'apartments;garage': ('residential', 'MFH'),
    'garage;semidetached_house': ('residential', 'SFH'),
    'garage;house;': ('residential', 'SFH'),

    # Ambiguous multi‑category combos
    'commercial;civic;retail': ('commercial', 'retail'),
    'commercial;carport;roof;house': ('semi_commercial', 'residential_commercial'),

    'chicken_coop': ('agricultural', 'animal_keeping'),
    'greenhouse_horticulture': ('agricultural', 'greenhouse'),
    'gasometer': ('industrial', 'utilities'),
    'aviary': ('agricultural', 'animal_keeping'),


    # ================================================================
    # TRANSPORTATION
    # ================================================================

    # Train stations
    'train_station': ('transportation', 'train_station'),
    'railway_station': ('transportation', 'train_station'),
    'station': ('transportation', 'train_station'),
    'bahnhof': ('transportation', 'train_station'),

    # Airport terminals
    'airport': ('transportation', 'airport'),
    'terminal': ('transportation', 'airport'),

    # Bus passenger
    'bus_station': ('transportation', 'bus_station'),

    # Rail depots / maintenance
    'engine_shed': ('transportation', 'maintenance'),
    'engine shed': ('transportation', 'maintenance'),
    'locomotive_shed': ('transportation', 'maintenance'),
    'roundhouse': ('transportation', 'maintenance'),

    # Rail control / technical
    'railway_auxiliary': ('transportation', 'maintenance'),
    'railway_control_centre': ('transportation', 'maintenance'),
    'signal_box': ('transportation', 'maintenance'),
    'signalbox': ('transportation', 'maintenance'),
    'switch_tower': ('transportation', 'maintenance'),
    'railway_substation': ('transportation', 'maintenance'),

    # Airport control
    'control_tower': ('transportation', 'maintenance'),

    
    'goods_conveyor': ('filter', None),
    'loading_ramp': ('filter', None),

    # Platforms are NOT buildings
    'platform': ('filter', None),
    'railway_platform': ('filter', None),

    'transportation': ('transportation', None),  # generic fallback

    # Hangars 
    'hangar': ('transportation', 'maintenance'),
        
    'railway_station;yes': ('transportation', 'train_station'),
    

    # ================================================================
    # FILTER
    # ================================================================
    
    # Auxiliary / outbuildings → filter (low relevance)
    'outbuilding': ('filter', None),
    'annex': ('filter', None),
    'side_building': ('filter', None),
    'auxiliary_building': ('filter', None),
    'toilets': ('filter', None),
    'toilet': ('filter', None),
    'parking': ('transportation', 'parking'),
    'parking_entrance': ('filter', None),
    'elevator': ('filter', None),
    'annexe': ('filter', None),
    'vehicle_ramp': ('filter', None),
    'balcony': ('filter', None),

    # Common non-descriptive or temporary tags
    'no': ('filter', None),
    'collapsed': ('filter', None),
    'ger': ('filter', None),



    # Ruins / demolished
    'ruins': ('filter', None),
    'ruin': ('filter', None),
    'demolished': ('filter', None),
    'abandoned': ('filter', 'disused'),
    'abandoned:yes': ('filter', 'disused'),
    'abandoned:building': ('filter', 'disused'),
    'disused': ('filter', 'disused'),
    'garbage_shed': ('filter', None),

    # Natural features
    'rock': ('filter', None),
    'cliff': ('filter', None),
    'tree': ('filter', None),
    'tree_row': ('filter', None),
    'boulder': ('filter', None),
    'natural': ('filter', None),

    # Water features
    'pond': ('filter', None),
    'basin': ('filter', None),
    'water': ('filter', None),
    'pool': ('filter', None),

    # Surfaces
    'paved': ('filter', None),
    'unpaved': ('filter', None),
    'surface': ('filter', None),
    'asphalt': ('filter', None),
    'gravel': ('filter', None),
    'grass': ('filter', None),
    'meadow': ('filter', None),

    # Land‑use
    'farmland': ('filter', None),
    'forest': ('filter', None),
    'orchard': ('filter', None),
    'vineyard': ('filter', None),
    'allotments': ('filter', None),
    'cemetery': ('filter', None),
    'park': ('filter', None),
    'garden': ('filter', None),
    'staircase': ('filter', None),
    'chimney': ('filter', None),
    'veranda': ('filter', None),
    'arbor': ('filter', None),
    'gatehouse': ('civic', 'cultural'),
    'weir': ('filter', None),

    # Infrastructure (non‑building)
    'bridge': ('filter', None),
    'tunnel': ('filter', None),
    'culvert': ('filter', None),
    'pier': ('filter', None),
    'dock': ('filter', None),
    'wharf': ('filter', None),
    'harbour': ('filter', None),

    # Fences, walls, gates
    'fence': ('filter', None),
    'wall': ('filter', None),
    'gate': ('filter', None),

    # Towers & masts (non‑building)
    'tower': ('filter', None),
    'mast': ('filter', None),
    'antenna': ('filter', None),
    'flagpole': ('filter', None),

    # Containers / small objects
    'bin': ('filter', None),
    'trash': ('filter', None),
    'waste_basket': ('filter', None),
    'recycling': ('filter', None),

    # Transport objects (not buildings)
    'bus_stop': ('filter', None),
    'tram_stop': ('filter', None),
    'railway_signal': ('filter', None),
    'railway_switch': ('filter', None),
    'railway_crossing': ('filter', None),

    # Carports / garages that are NOT buildings
    'carport': ('filter', None),
    'garage': ('filter', None),
    'garages': ('filter', None),

    # Small shelters
    'shelter': ('filter', None),
    'bus_shelter': ('filter', None),
    'picnic_shelter': ('filter', None),

    # Misc objects
    'container': ('filter', None),
    'containers': ('filter', None),
    'shipping_container': ('filter', None),
    'stall': ('filter', None),
    'booth': ('filter', None),

    # Dataset weird cases
    'roof': ('filter', None),
    'canopy': ('filter', None),
    'awning': ('filter', None),
    'tent': ('filter', None),
    'hut': ('filter', None),  # not a building in OSM
    'lean_to': ('filter', None),
    'conservatory': ('filter', None),

}


# ============================================================  
# BUILDING USE MAP FUNCTION
# ============================================================

# Normalise map once at module load — handles mixed-case keys in BUILDING_MAP
_BUILDING_MAP_NORM: dict = {
    re.sub(r'\s+', ' ', k.strip().lower()): v
    for k, v in BUILDING_MAP.items()
}

# Priority order for resolving mixed-tag conflicts (highest → lowest)
_PRIORITY: list[str] = [
    'industrial',  'civic', 'commercial', 'residential', 'transportation', 
     'agricultural', 'military', 'filter'
]


def _normalize(value) -> str:
    """Lowercase, collapse whitespace, strip trailing semicolons."""
    s = str(value).strip().lower()
    return re.sub(r'\s+', ' ', s).rstrip(';')


def apply_building_map(use_value) -> tuple:
    """
    Map a raw OSM building tag value to (Level1_Type, Level2_Subtype, is_mixed).

    Parameters
    ----------
    use_value : str | float | None
        Raw value from the OSM 'building' tag (e.g. 'residential', 'retail;office').

    Returns
    -------
    tuple : (Level1_Type, Level2_Subtype, is_mixed)
        - Level1_Type  : top-level category string, or None if unmappable
        - Level2_Subtype : subtype string, or None
        - is_mixed     : True if the tag represents a multi-use compound value

    Lookup strategy
    ---------------
    1. Normalise: lowercase, collapse whitespace, strip trailing semicolons.
    2. Direct lookup in _BUILDING_MAP_NORM (covers all explicit map entries,
       including pre-defined semicolon compounds).
    3. Semicolon fallback for unmapped compound tags:
       a. All parts resolve to 'filter'         → return filter
       b. residential + commercial parts present → semi_commercial with
          specific subtype (residential_retail, residential_office, etc.)
          derived from the commercial part's L2; falls back to
          residential_commercial if no L2 available.
       c. Otherwise pick the dominant L1 by _PRIORITY; is_mixed=True
          when multiple distinct L1s are present.
    4. Return (None, None) if unmappable.

    Notes
    -----
    - Map entries that resolve to (None, None) (e.g. invalid mixes
      like residential;industrial) are excluded from semicolon resolution
      so they do not corrupt L1 priority logic.
    - When multiple parts share the same L1 but differ in L2, the first
      matching part wins and the second L2 is silently dropped. This is
      intentional for energy-modelling purposes where L1 is primary.
    - Mixed-case keys in BUILDING_MAP (e.g. 'RESIDENTIAL', 'Wohnhaus')
      are normalised at import time. Where a normalised key collides with
      an existing lowercase key, last-write-wins (the lowercase entry).
    """
    if pd.isna(use_value):
        return (None, None)

    s = _normalize(use_value)

    # Direct lookup
    if s in _BUILDING_MAP_NORM:
        return _BUILDING_MAP_NORM[s]

    # Unmappable
    return (None, None)




# ============================================================
# VALIDATION BLOCK
# ============================================================
if __name__ == '__main__':
    total = len(BUILDING_MAP)
    counts = {}
    
    for v in BUILDING_MAP.values():
        counts[v[0]] = counts.get(v[0], 0) + 1
        
    # Safely handle mixed_c in case a tuple is accidentally too short
    mixed_c = sum(1 for v in BUILDING_MAP.values() if len(v) > 2 and v[2])

    print("BUILDING_MAP SUMMARY")
    print(f"  Total explicit mappings : {total}")
    print("-" * 30)
    
    # The Fix: key=lambda x: str(x) forces Python to sort None as "None"
    for cat in sorted(counts, key=lambda x: str(x)):
        print(f"  {str(cat):<20}: {counts[cat]}")
    print("-" * 30)
    print(f"  Mixed-use entries     : {mixed_c}\n")
    
    all_subtypes = sorted(set(v[1] for v in BUILDING_MAP.values() if len(v) > 1 and v[1] is not None))
    print(f"All Level 2 subtypes ({len(all_subtypes)} total):")
    for s in all_subtypes:
        print(f"  - {s}")
