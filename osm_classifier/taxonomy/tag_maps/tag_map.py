import pandas as pd
import re

"""
TAG_MAP — Complete mapping of all OSM building tag values
to (Level1_Type, Level2_Subtype) 

Level 1 categories:
    Residential, Commercial, Industrial, Civic, Agricultural,
    Transportation, Military, Semi_Commercial, Filter


Filter = not a building or too small to classify
   (bus shelters, bicycle stands, toilets etc)

L2 subtypes by L1:
  residential  : SFH, TH, MFH
  commercial   : accommodation, office, food_drink, retail,
                 other_service, retail,
  civic        : government_office, school, higher_ed, research, hospital, clinic,
                 sport, cultural, community, care_facility, religious,
                 emergency_service, kindergarten
  industrial   : storage, manufacturing, utilities, utilities
  agricultural : equestrian, animal_keeping, greenhouse, farm_auxillary
  transportation: train_station, bus_station, parking_facility, airport, maintenance
  military     : barracks, bunker
  filter       : filter  (buildings with no or low energy demand and non-building structures )


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

Format: 'osm_value': ('Level1_Type', 'Level2_Subtype')
"""

TAG_MAP = {

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
    'garage;terrace': ('residential', 'TH'),
    'einzelnes_reihenhausmm': ('residential', 'TH'),
    'resideuntial': ('residential', None),
    'maisonette': ('residential', 'MFH'),

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
    'mobile_home': ('residential', 'SFH'),
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
    'semi': ('residential', 'SFH'),

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
    'column': ('filter', None),

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
    'ger': ('filter', None),

    # Rare residential-like tags
    'assisted_living': ('civic', 'care_facility'),
    'juvenile_home': ('civic', 'care_facility'),
    'group_home': ('civic', 'care_facility'),
    'old people\'s home': ('civic', 'care_facility'),
    'religious': ('civic', 'religious'),


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
    'marquee': ('filter', None),

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
    'administration': ('civic', 'government_office'),
    'administrative': ('civic', 'government_office'),
    'forwarding_office': ('commercial', 'office'),
    'post_office': ('commercial', 'office'),
    'ticket_office': ('commercial', 'office'),
    'office;yes': ('commercial', 'office'),
    'office;garages': ('commercial', 'office'),
    'ministry': ('civic', 'government_office'),

    # Entertainment & culture (commercial side)
    'cinema': ('civic', 'cultural'),
    'theatre': ('civic', 'cultural'),
    'music_venue': ('civic', 'cultural'),
    'nightclub': ('commercial', 'food_drink'),
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

    # Logistics (but storage → industrial.storage)
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
    'village': ('civic', 'community'),

    # High-rise commercial
    'skyscraper': ('commercial', 'office'),
    'highrise': ('commercial', 'office'),

    # Typos & variants
    'yesoutletstores_direct': ('commercial', 'retail'),
    'supermarkt': ('commercial', 'retail'),
    'reteil': ('commercial', 'retail'),
    'Reihenhaus': ('residential', 'TH'),
    'Reihenendhaus': ('residential', 'TH'),
    'Doppelhaushälfte': ('residential', 'SFH'),
    'Einfamilienhaus': ('residential', 'SFH'),
    'freistehendes Einfamilienhaus': ('residential', 'SFH'),
    'Mehrfamilienhaus': ('residential', 'MFH'),
    'Mehrfamilenhaus': ('residential', 'MFH'),
    'Zweifamilienhaus': ('residential', 'SFH'),
    'Hochhaus': ('residential', 'MFH'), 
    'Wohn- und Geschäftshaus': ('semi_commercial', 'residential_commercial', True),
    'Bürogebäude': ('commercial', 'office'),
    'Turnhalle': ('civic', 'recreation'),
    'Tiefgarage': ('filter', None),
    'Gewächshaus': ('agricultural', 'greenhouse'),
    'Gartenlaube': ('filter', None),
    'Standard PKW-Reihengarage mit Pultdach': ('filter', None),
    

    # ================================================================
    # INDUSTRIAL
    # ================================================================
    
    # Core industrial
    'industrial': ('industrial', 'manufacturing'),  
    'factory': ('industrial', 'manufacturing'),
    'manufacture': ('industrial', 'manufacturing'),
    'plant': ('industrial', 'utilities'),


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
    'digester': ('industrial', 'utilities'),


    # Water & pumping
    'pumping_station': ('industrial', 'utilities'),
    'sewage_pumping_station': ('industrial', 'utilities'),
    'reservoir': ('filter', None),
    'water_tower': ('industrial', 'utilities'),
    'wastewater_plant': ('industrial', 'utilities'),
    'water_tank': ('industrial', 'utilities'),
    'water_storage': ('industrial', 'utilities'),
    'cistern': ('filter', None),

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
    'industrial;yes': ('industrial', 'manufacturing'),
    'yes;industrial': ('industrial', 'manufacturing'),
    'roof;industrial': ('industrial', 'manufacturing'),
    'industrial;abandoned': ('industrial', 'manufacturing'),
    'abandoned:industrial': ('industrial', 'manufacturing'),
    'îndustrial': ('industrial', 'manufacturing'),

    # Dataset-derived industrial
    'bunker': ('military', 'bunker'),
    'communications_tower': ('filter', None),
    'motorradhalle': ('commercial', 'retail'),
    'lagerhalle,autowerksatt': ('commercial', 'retail'),

    # Mixed industrial
    'industrial;office': ('industrial', None),

    'passage': ('filter', None, False),
    'corridor': ('filter', None, False),
    # ================================================================
    # CIVIC
    # ================================================================

    # Education
    'school': ('civic', 'school'),
    'kindergarten': ('civic', 'kindergarten'),
    'kindergarden': ('civic', 'kindergarten'),
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
    'tax': ('civic', 'government_office'),

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
    'wayside_shrine': ('filter', None),
    'basilica': ('civic', 'religious'),
    'bell_tower': ('filter', None),






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
    'hermitage': ('civic', 'religious'),
    'cemetery_chapel': ('civic', 'religious'),
    'yes;chapel': ('civic', 'religious'),
    'chapel;wayside_chapel': ('civic', 'religious'),
    'de:mausoleum': ('civic', 'religious'),
    'vicarage': ('residential', 'SFH'),
    'embassy': ('civic', 'government_office'),
    'sport': ('civic', 'recreation'),

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

    # Sports & recreation
    'sports_hall': ('civic', 'recreation'),
    'sports_centre': ('civic', 'recreation'),
    'sports_center': ('civic', 'recreation'),
    'sports_centre;yes': ('civic', 'recreation'),
    'gymnasium': ('civic', 'recreation'),
    'arena': ('civic', 'recreation'),
    'stadium': ('civic', 'recreation'),
    'stadion': ('civic', 'recreation'),
    'bowling_alley': ('civic', 'recreation'),
    'indoor_swimming_pool': ('civic', 'recreation'),
    'swimming_pool': ('civic', 'recreation'),
    'ice_rink': ('civic', 'recreation'),
    'indoor_play': ('civic', 'recreation'),
    'amusement_arcade': ('civic', 'recreation'),
    'water_park': ('civic', 'recreation'),
    'pitch': ('filter', None),
    'shooting_stand': ('filter', None),
    'roundpen': ('filter', None),
    'grandstand': ('civic', 'recreation'),
    'castle': ('civic', 'cultural'),
    'guest_house;apartments': ('commercial', 'accommodation'),
    'apartment;guest_house': ('commercial', 'accommodation'),


    'presbytery': ('residential', 'SFH'),
    'manor': ('residential', 'SFH'),
    'palace': ('civic', 'cultural'),
    'palais': ('civic', 'cultural'),
    # ================================================================
    # AGRICULTURAL
    # ================================================================
 
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
    'abandoned:greenhouse': ('agricultural', 'greenhouse'),
    'farmyard': ('filter', None),  
    'Landwirtschaft Neuenhofe': ('filter', None),
    'farm_house': ('residential', 'SFH'),
    'farm_shop': ('commercial', 'retail'),
    'farm_store': ('commercial', 'retail'),

    'shed': ('filter', None),  # safest assumption
    'farm_auxiliary': ('agricultural', 'farm_auxiliary'),
    'farm': ('residential', 'SFH'),
    'hay_barn': ('filter', None),
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
   
    'apartment_building': ('residential', 'MFH'),

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
    'cadaster': ('civic', 'government_office'),

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
    'control_center': ('transportation', 'maintenance'),

    
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
    # RESIDENTIAL
    # ================================================================
    
    'restential': ('residential', None),  # fallback for typos
    'residential': ('residential', None),
    'town_house': ('residential', 'TH'),
    'row': ('residential', 'TH'),
    'rterraced': ('residential', 'TH'),

    # Apartments / multi-unit
    'apartements': ('residential', 'MFH'),
    'apartment': ('residential', 'MFH'),

    # Single-family
    'model_home': ('commercial', 'office'),
    'Heuhotel': ('commercial', 'accommodation'),
    'link-detached': ('residential', 'SFH'),
    'duplex': ('residential', 'SFH'),

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
    
    # Offices
    'office': ('commercial', 'office'),
    'Office': ('commercial', 'office'),
    'Office building': ('commercial', 'office'),
    'offices': ('commercial', 'office'),
    'executive': ('commercial', 'office'),
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
    
    

    # Manufacturing / production
    'factory': ('industrial', 'manufacturing'),
    'manufacture': ('industrial', 'manufacturing'),
    'work': ('industrial', 'manufacturing'),
    'bottling': ('industrial', 'manufacturing'),
    'grist mill': ('industrial', 'manufacturing'),

    # Chemical / heavy industry
    'chemical': ('industrial', 'manufacturing'),

    # Utilities / energy / water
    'Gasversorgung': ('industrial', 'utilities'),
    'Sauerstoffanlage': ('industrial', 'utilities'),
    'water treatment': ('industrial', 'utilities'),
    'electricity': ('industrial', 'utilities'),
    'electrical installationl': ('industrial', 'utilities'),
    'transformer_station': ('industrial', 'utilities'),
    'power transformer': ('industrial', 'utilities'),
    'Wasserhochbehälter': ('industrial', 'utilities'),

    # Logistics / transport
    'transport company': ('commercial', 'office'),

    # Storage / warehousing
    'warehouse': ('industrial', 'storage'),
    'cold_store': ('industrial', 'storage'),
    'boat_storage': ('filter', None),

    # Waste management

    
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

   

    'kindergarten; school': ('civic', 'kindergarten'),
    'kindergarten;public': ('civic', 'kindergarten'),
    'music_school': ('civic', 'school'),
    'riding_school': ('agricultural', 'equestrian'),
    'education': ('civic', 'school'),
    'Lehrsaalgebäude': ('civic', 'school'),
    'Aula': ('civic', 'school'),

    # Higher education / research
   
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
    'agriculture': ('agricultural', None),

   
    # Barns / auxiliary
    'barn': ('agricultural', 'animal_keeping'),
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
    # CIVIC: EDUCATION
    # ================================================================
    
    'university/college': ('civic', 'higher_ed'),
    'childcare': ('civic', 'kindergarten'),
    'kindergarten;childcare': ('civic', 'kindergarten'),
    'prep_school': ('civic', 'school'),
    'language_school': ('civic', 'school'),
    'music_school': ('civic', 'school'),
    'driving_school': ('civic', 'school'),
    'dancing_school': ('civic', 'school'),
    'cooking_school': ('civic', 'school'),
    'hunting_school': ('civic', 'school'),
    'ski_school': ('civic', 'school'),
    'dance': ('civic', 'recreation'),
    'sailing_school': ('civic', 'school'),
    'surf_school': ('civic', 'school'),
    'flight_school': ('civic', 'school'),
    'training': ('civic', 'school'),
    'education': ('civic', 'school'),
    'education_centre': ('civic', 'school'),
    'education_center': ('civic', 'school'),
    'religious_education': ('civic', 'school'),
    'research': ('civic', 'research'),
    'research_institute': ('civic', 'research'),
    'laboratory': ('civic', 'higher_ed'),
    'library': ('civic', 'cultural'),
    'toy_library': ('civic', 'cultural'),
    'student_accommodation': ('commercial', 'accommodation'),
    'student_accomodation': ('commercial', 'accommodation'),
    'dormitory': ('commercial', 'accommodation'),
    'hall_of_residence': ('commercial', 'accommodation'),
    'dog_school': ('civic', 'school'),
    'boat_school': ('civic', 'school'),
    'sport_school': ('civic', 'school'),
    'art_school': ('civic', 'school'),
    'first_aid_school': ('civic', 'school'),
    'school_club': ('civic', 'school'),
    'school;driving_school': ('civic', 'school'),
    'lecture_hall': ('civic', 'higher_ed'),
    'community_college': ('civic', 'higher_ed'),
    'adult_education_centre': ('civic', 'school'),
    'environmental_education': ('civic', 'school'),
    'educational_facility': ('civic', 'school'),
    'reseach_institute': ('civic', 'research'),
    'science_park': ('civic', 'research'),
    'institute': ('civic', 'research'),
    'schul-Aula': ('civic', 'school'),
    'mobile_library': ('filter', None),  
    'library;archive': ('civic', 'cultural'),
    'library;place_of_worship': ('civic', 'cultural'),
    'library service center': ('civic', 'cultural'),
    'community_centre; library': ('civic', 'community'),
    'public_building; college': ('civic', 'higher_ed'),
    'archive': ('civic', 'government_office'),

    # ================================================================
    # CIVIC: HEALTHCARE
    # ================================================================
    'hospital': ('civic', 'hospital'),
    'clinic': ('civic', 'clinic'),
    'health_centre': ('civic', 'clinic'),
    'health_resort': ('civic', 'clinic'),
    'sanatorium': ('civic', 'clinic'),
    'naturopathy': ('civic', 'clinic'),
    'salt_inhalation_therapy': ('civic', 'clinic'),
    'medical_centre': ('civic', 'clinic'),
    'doctors': ('civic', 'clinic'),
    'dentist': ('civic', 'clinic'),
    'oculist;dentist': ('civic', 'clinic'),
    'pharmacy': ('commercial', 'retail'),
    'veterinary': ('civic', 'clinic'),
    'animal_training': ('civic', 'clinic'),
    'nursing_home': ('civic', 'care_facility'),
    'retirement_home': ('civic', 'care_facility'),
    'rest_home': ('civic', 'care_facility'),
    'social_facility': ('civic', 'care_facility'),
    'social_services': ('civic', 'care_facility'),
    'rehabilitation': ('civic', 'care_facility'),
    'blood_donation': ('civic', 'clinic'),
    'red_cross': ('civic', 'care_facility'),
    'first_aid': ('civic', 'clinic'),
    'rescue_service': ('civic', 'emergency_service'),
    'mountain_rescue': ('civic', 'emergency_service'),
    'lifeboat_station': ('civic', 'emergency_service'),
    'coast_guard': ('civic', 'emergency_service'),
    'emergency_service': ('civic', 'emergency_service'),
    'firefighting_technical_center': ('civic', 'emergency_service'),
    'health_care': ('civic', 'clinic'),
    'midwife': ('civic', 'clinic'),
    'therapist': ('civic', 'clinic'),
    'chiropody': ('civic', 'clinic'),
    'dog_physiotherapist': ('civic', 'clinic'),
    'healer': ('civic', 'clinic'),
    'meditation_centre': ('commercial', 'other_service'),
    'Meditation': ('commercial', 'other_service'),
    'spa_resort': ('commercial', 'other_service'),
    'nursing_home;nursing_service': ('civic', 'care_facility'),
    'nursing_home;social_facility': ('civic', 'care_facility'),
    'nursing_home;retirement_home': ('civic', 'care_facility'),
    'nursing_house': ('civic', 'care_facility'),
    'rest_house': ('civic', 'care_facility'),
    'sheltered_housing': ('civic', 'care_facility'),
    'rescue_center': ('civic', 'emergency_service'),
    'rescue_station': ('civic', 'emergency_service'),
    'marine_rescue': ('civic', 'emergency_service'),


    # ================================================================
    # CIVIC: GOVERNMENT AND EMERGENCY
    # ================================================================
    'townhall': ('civic', 'government_office'),
    'courthouse': ('civic', 'government_office'),
    'police': ('civic', 'emergency_service'),
    'fire_station': ('civic', 'emergency_service'),
    'prison': ('civic', 'government_office'),
    'synagogue': ('civic', 'religious'),
    'embassy': ('civic', 'government_office'),
    'post_office': ('commercial', 'office'),
    'post_depot': ('commercial', 'office'),
    'register_office': ('civic', 'government_office'),
    'public_service': ('civic', 'government_office'),
    'public_building': ('civic', None),
    'government': ('civic', 'government_office'),
    'public': ('civic', 'government_office'),
    'immigration': ('civic', 'government_office'),
    'job_centre': ('civic', 'government_office'),
    'ranger_station': ('civic', 'government_office'),
    'forestry_office': ('civic', 'government_office'),
    'forester': ('commercial', 'office'),
    'customs': ('civic', 'government_office'),
    'prosecution': ('civic', 'government_office'),
    'harbourmaster': ('civic', 'government_office'),
    'refugee_housing': ('civic', 'care_facility'),
    'refugee_site': ('civic', 'care_facility'),
    'public_facility': ('civic', None),
    'public_utility': ('civic', None),
    'lost_property_office': ('civic', 'government_office'),
    'tax_advisor': ('commercial', 'office'),
    'stock_exchange': ('commercial', 'office'),
    'translation_services': ('commercial', 'office'),
    'translator': ('commercial', 'office'),
    'communication_centre': ('commercial', 'office'),
    'broadcasting_station': ('commercial', 'office'),
    'post_point': ('commercial', 'office'),
    'mailroom': ('commercial', 'office'),
    'lettershop': ('commercial', 'office'),
    'railway_control_centre': ('transportation', 'maintenance'),
    'orphanage': ('civic', 'care_facility'),
    'baby_hatch': ('civic', 'care_facility'),
    'fire:station': ('civic', 'emergency_service'),
    'fire_substation': ('civic', 'emergency_service'),
    'civic': ('civic', None),

    # ================================================================
    # CIVIC: RELIGIOUS
    # ================================================================
    'place_of_worship': ('civic', 'religious'),
    'monastery': ('civic', 'religious'),
    'convent': ('civic', 'religious'),
    'seminary': ('civic', 'religious'),
    'rectory': ('residential', 'SFH'),
    'vicarage': ('residential', 'SFH'),
    'parish_hall': ('civic', 'community'),
    'chapel': ('civic', 'religious'),
    'furneral_hall': ('civic', 'community'),
    'funeral_home': ('civic', 'community'),
    'crematorium': ('civic', 'community'),
    'mortuary': ('civic', 'community'),
    'place_of_mourning': ('civic', 'community'),
    'crypt': ('civic', 'religious'),
    'cheaple': ('civic', 'religious'),
    'altar': ('civic', 'religious'),
    'parish_office': ('civic', 'religious'),
    'parish_rooms': ('civic', 'religious'),
    'Pfarrzentrum': ('civic', 'community'),
    'vacarage': ('residential', 'SFH'),
    'cemetery_hall': ('civic', 'community'),
    'gravesite': ('filter', None),
    'urn_wall': ('filter', None),
    'masonic_lodge': ('civic', 'religious'),
    'sheepfold': ('agricultural', 'animal_keeping'),

    # ================================================================
    # CIVIC: CULTURE AND COMMUNITY
    # ================================================================
    'community_centre': ('civic', 'community'),
    'community_hall': ('civic', 'community'),
    'cultural_centre': ('civic', 'cultural'),
    'public_hall': ('civic', 'community'),
    'social_centre': ('civic', 'community'),
    'social_club': ('civic', 'community'),
    'club_home': ('civic', 'community'),
    'family_centre': ('civic', 'community'),
    'village_hall': ('civic', 'community'),
    'recreation_center': ('civic', 'recreation'),
    'clubhouse': ('civic', 'community'),
    'meeting_room': ('civic', 'community'),
    'fraternity': ('civic', 'community'),
    'scout_hut': ('civic', 'community'),
    'scout_hall': ('civic', 'community'),
    'charity': ('civic', 'community'),
    'youth_centre': ('civic', 'community'),
    'animal_shelter': ('civic', 'care_facility'),
    'arts_centre': ('civic', 'cultural'),
    'arts_centre;community_centre': ('civic', 'cultural'),
    'theatre': ('civic', 'cultural'),
    'museum': ('civic', 'cultural'),
    'gallery': ('civic', 'cultural'),
    'planetarium': ('civic', 'cultural'),
    'events_venue': ('civic', 'community'),
    'events_centre': ('civic', 'community'),
    'conference_centre': ('civic', 'community'),
    'convention_centre': ('civic', 'community'),
    'exhibition_centre': ('civic', 'cultural'),
    'exhibition_hall': ('civic', 'cultural'),
    'concert_hall': ('civic', 'cultural'),
    'opera': ('civic', 'cultural'),
    'music_venue': ('civic', 'cultural'),
    'bandstand': ('civic', 'cultural'),
    'stage': ('civic', 'cultural'),
    'rehearsal_studio': ('civic', 'cultural'),
    'community': ('civic', 'community'),
    'community_centre;fire station': ('civic', None),
    'community_centre;event_venue': ('civic', 'community'),
    'community_centre; Kindergarten': ('civic', None),
    'community_centre + arts_centre + restaurant': ('civic', 'cultural'),
    'social_center': ('civic', 'community'),
    'social_cetre': ('civic', 'community'),
    'social_facility;community_centre': ('civic', 'care_facility'),
    'club': ('civic', 'community'),
    'dojang': ('civic', 'recreation'),
    'culture_center': ('civic', 'cultural'),
    'museal': ('civic', 'cultural'),
    'cultural heritage monument': ('civic', 'cultural'),
    'space_centre': ('civic', 'cultural'),
    'festival_hall': ('civic', 'cultural'),
    'exhibition_centre;concert_hall': ('civic', 'cultural'),
    'conference_centre;events_venue': ('civic', 'community'),
    'events_venue;parking': ('civic', 'community'),
    'multi-purpose_hall': ('civic', None),
    'multi-porpose hall': ('civic', None),
    'multipurpose_hall': ('civic', None),
    'assembly hall': ('civic', None),
    'maker_space': ('civic', 'cultural'),
    'event management': ('commercial', 'office'),
    'event_rental': ('commercial', 'office'),
    'events_vemnue': ('civic', 'community'),
    'grandstand': ('civic', 'recreation'),
    'animal_shelter;animal_boarding': ('civic', 'care_facility'),
    'petting_zoo': ('filter', None),
    'zoo': ('civic', 'recreation'),
    'aquarium': ('civic', 'recreation'),
    'theme_park': ('civic', 'recreation'),
    'artwork': ('civic', 'cultural'),
    'shopping': ('commercial', 'retail'),

    # ================================================================
    # CIVIC: SPORT AND LEISURE
    # ================================================================
    'sports_centre': ('civic', 'recreation'),
    'sports_hall': ('civic', 'recreation'),
    'sport': ('civic', 'recreation'),
    'swimming_pool': ('civic', 'recreation'),
    'stadium': ('civic', 'recreation'),
    'dojo': ('civic', 'recreation'),
    'gym': ('civic', 'recreation'),
    'fitness_centre': ('civic', 'recreation'),
    'riding_school': ('agricultural', 'equestrian'),
    'dive_centre': ('civic', 'recreation'),
    'traffic_park': ('filter', None),
    'adult_gaming_centre': ('civic', 'recreation'),
    'gymnastics': ('civic', 'recreation'),
    'horse_riding': ('agricultural', 'equestrian'),
    'bull_riding': ('filter', None),
    'tanning_salon': ('commercial', 'other_service'),

    # ================================================================
    # TRANSPORTATION
    # ================================================================
    'bus_station': ('transportation', 'bus_station'),
    'ferry_terminal': ('transportation', None),
    'train_station': ('transportation', 'train_station'),
    'cruise_terminal': ('transportation', None),
    'bus_garage': ('transportation', 'maintenance'),


    # ================================================================
    # COMMERCIAL: FOOD AND DRINK
    # ================================================================
    'restaurant': ('commercial', 'food_drink'),
    'restaurant;cafe': ('commercial', 'food_drink'),
    'restaurant;pub': ('commercial', 'food_drink'),
    'pub;restaurant': ('commercial', 'food_drink'),
    'fast_food': ('commercial', 'food_drink'),
    'cafe': ('commercial', 'food_drink'),
    'internet_cafe': ('commercial', 'office'),
    'ice_cream': ('commercial', 'food_drink'),
    'pub': ('commercial', 'food_drink'),
    'bar': ('commercial', 'food_drink'),
    'hookah_lounge': ('commercial', 'food_drink'),
    'biergarten': ('commercial', 'food_drink'),
    'food_court': ('commercial', 'food_drink'),
    'bakery': ('commercial', 'food_drink'),
    'canteen': ('commercial', 'food_drink'),
    'cafeteria': ('commercial', 'food_drink'),
    'catering': ('commercial', 'food_drink'),
    'bistro': ('commercial', 'food_drink'),
    'wine_bar': ('commercial', 'food_drink'),
    'karaoke_bar': ('commercial', 'food_drink'),
    'hooka_lounge': ('commercial', 'food_drink'),
    'pup': ('commercial', 'food_drink'),
    'fast_food;biergarten': ('commercial', 'food_drink'),
    'restaurant;fast_food': ('commercial', 'food_drink'),
    'restaurant;bar;pub': ('commercial', 'food_drink'),
    'restaurant; biergarten': ('commercial', 'food_drink'),
    'canteen/cafe': ('commercial', 'food_drink'),
    'canteen_kitchen': ('commercial', 'food_drink'),
    'kanteen': ('commercial', 'food_drink'),
    'bakehouse': ('industrial', 'manufacturing'),
    'sale_of_drinks_and_food': ('commercial', 'food_drink'),
    'food': ('commercial', 'food_drink'),
    'bar; shelter': ('commercial', 'food_drink'),
    'kitchen': ('commercial', 'food_drink'),
    'Häckerstube': ('commercial', 'food_drink'),

    # ================================================================
    # COMMERCIAL: RETAIL
    # ================================================================
    'marketplace': ('commercial', 'retail'),
    'market': ('commercial', 'retail'),
    'supermarket': ('commercial', 'retail'),
    'shop': ('commercial', 'retail'),
    'kiosk': ('commercial', 'retail'),
    'vending_machine': ('filter', None),
    'payment_centre': ('commercial', 'office'),
    'showroom': ('commercial', 'retail'),
    'flower': ('commercial', 'retail'),
    'freeshop': ('commercial', 'retail'),
    'fair': ('commercial', 'retail'),
    'vending-station': ('filter', None),
    'payment_terminal': ('filter', None),

    # ================================================================
    # COMMERCIAL: FINANCIAL AND OFFICE
    # ================================================================
    'bank': ('commercial', 'office'),
    'bureau_de_change': ('commercial', 'office'),
    'building_society': ('commercial', 'office'),
    'office': ('commercial', 'office'),
    'coworking_space': ('commercial', 'office'),
    'travel_agency': ('commercial', 'office'),
    'insurance': ('commercial', 'office'),
    'estate_agent': ('commercial', 'office'),
    'accountant': ('commercial', 'office'),
    'lawyer': ('commercial', 'office'),
    'notary': ('commercial', 'office'),
    'employment_agency': ('commercial', 'office'),
    'publisher': ('commercial', 'office'),
    'drugs_firm': ('commercial', 'office'),
    'co-working': ('commercial', 'office'),
    'rental_offices': ('commercial', 'office'),
    'money_transfer': ('commercial', None),
    'bank;post_office': ('commercial', 'office'),
    'travel_company': ('commercial', 'office'),
    'reception_desk': ('commercial', 'office'),
    'reception_point': ('commercial', 'office'),
    'building_superintendent': ('commercial', 'office'),

    # ================================================================
    # COMMERCIAL: VEHICLE SERVICES
    # ================================================================
    'car_wash': ('commercial', 'retail'),
    'tank_wash': ('commercial', 'retail'),
    'fuel;car_wash': ('commercial', 'retail'),
    'car_rental': ('commercial', 'office'),
    'car_sharing': ('filter', None),
    'fuel': ('commercial', 'retail'),
    'vehicle_inspection': ('commercial', 'retail'),
    'bicycle_rental': ('commercial', 'office'),
    'boat_rental': ('filter', None),
    'boat_sharing': ('commercial', 'office'),
    'ski_rental': ('commercial', 'office'),
    'machine_rental': ('commercial', 'office'),
    'car_service': ('commercial', 'retail'),
    'car_repair': ('commercial', 'retail'),
    'car': ('commercial', 'retail'),
    'large_vehicle_wash': ('commercial', 'retail'),
    'hgv_wash': ('commercial', 'retail'),
    'motorcycle_wash': ('commercial', 'retail'),
    'car_wash;trailer_rental': ('commercial', 'retail'),
    'trailer_rental': ('commercial', 'office'),
    'truck_rental': ('commercial', 'office'),
    'tent_rental': ('commercial', 'office'),
    'handcart_rental': ('commercial', 'office'),
    'tool_hire': ('commercial', 'office'),
    'rental': ('commercial', 'office'),
    'construction_machinery_rental': ('commercial', 'office'),
    'trailer_inspection; trailer_rental': ('commercial', 'retail'),
    'railway:fuel': ('commercial', 'retail'),

    # ================================================================
    # COMMERCIAL: PERSONAL SERVICES
    # ================================================================
    'laundry': ('commercial', 'other_service'),
    'dry_cleaning': ('commercial', 'other_service'),
    'hairdresser': ('commercial', 'other_service'),
    'massage': ('commercial', 'other_service'),
    'tattoo': ('commercial', 'other_service'),
    'spa': ('commercial', 'other_service'),
    'studio': ('commercial', 'office'),
    'dog_wash': ('commercial', 'other_service'),
    'tanning': ('commercial', 'other_service'),
    'care_cosmetics': ('commercial', 'other_service'),
    'shoemaker': ('commercial', 'other_service'),
    'joinery': ('commercial', 'other_service'),
    'printing': ('commercial', 'other_service'),
    'painter': ('commercial', 'other_service'),
    'raumausstattung': ('commercial', 'office'),
    'moving_company': ('commercial', 'office'),

    # ================================================================
    # COMMERCIAL: ACCOMMODATION
    # ================================================================
    'hotel': ('commercial', 'accommodation'),
    'motel': ('commercial', 'accommodation'),
    'love_hotel': ('commercial', 'accommodation'),
    'hostel': ('commercial', 'accommodation'),
    'guest_house': ('commercial', 'accommodation'),
    'boathouse': ('filter', None),
    'boat_house': ('filter', None),
    'alpine_hut': ('commercial', 'accommodation'),
    'summerhouse': ('filter', None),

    # ================================================================
    # COMMERCIAL: ENTERTAINMENT AND NIGHTLIFE
    # ================================================================
    'nightclub': ('commercial', 'food_drink'),
    'casino': ('civic', 'recreation'),
    'gambling': ('civic', 'recreation'),
    'stripclub': ('commercial', 'food_drink'),
  

    # ================================================================
    # INDUSTRIAL: STORAGE AND LOGISTICS
    # ================================================================
    'warehouse':                    ('industrial', 'storage'),
    'cargo':                        ('filter', None),
    'loading_dock':                 ('filter', None),
    'boat_storage':                 ('filter', None),
    'waste_transfer_station':       ('industrial', 'utilities'),
    'disposal':                     ('filter', None),
    'works':                        ('industrial', 'manufacturing'),
    # --- newly added industrial ---
    'industry': ('industrial', None),
    'slaughterhouse': ('industrial', 'manufacturing'),
    'manufactur': ('industrial', 'manufacturing'),
    'apple-juice_factory': ('industrial', 'manufacturing'),
    'water_supply': ('industrial', 'utilities'),
    'pumpstation': ('industrial', 'utilities'),
    'wastewater_pump': ('industrial', 'utilities'),
    'heat_plant': ('industrial', 'utilities'),
    'energy_facility': ('industrial', 'utilities'),
    'waste_transfer_stagion': ('industrial', 'utilities'),
    'road_maintenance_staff': ('transportation', 'maintenance'),
    'cold_store': ('industrial', 'storage'),
    'public_works': ('industrial', None),
    'caravan_storage': ('filter', None),
    'snow_removal_station': ('filter', None),
    'plant_nursery': ('agricultural', 'greenhouse'),
    'graduation_tower':('industrial', None),
    'ski_jump': ('filter', None),

    # ================================================================
    # AGRICULTURAL
    # ================================================================
    'stables': ('agricultural', 'equestrian'),
    'stable': ('agricultural', 'equestrian'),
    'stablets': ('agricultural', 'equestrian'),
    'greenhouse': ('agricultural', 'greenhouse'),
    'animal_breeding': ('agricultural', 'animal_keeping'),
    'animal_boarding': ('agricultural', 'animal_keeping'),
    'animal_feeding': ('agricultural', 'animal_keeping'),
    'game_feeding': ('agricultural', 'animal_keeping'),
    'deer_feeding': ('agricultural', 'animal_keeping'),
    'feeding_place': ('agricultural', 'animal_keeping'),
    'manger': ('agricultural', 'animal_keeping'),
    'hunting_stand': ('filter', None),
    'hunting_lodge': ('commercial', 'accommodation'),
    'farmhouse': ('residential', 'SFH'),
    'animal_place': ('agricultural', 'animal_keeping'),
    'animal_station': ('agricultural', 'animal_keeping'),
    'animal_scales': ('filter', None),
    'agricultural_spray_pump': ('filter', None),
    'street_cabinet': ('filter', None),

    # ================================================================
    # RESIDENTIAL (directly tagged)
    # ================================================================
    'apartments':                   ('residential', 'MFH'),
    'apartment':                    ('residential', 'MFH'),
    'dwelling_house':               ('residential', None),

    # ================================================================
    # FILTER: NOT BUILDINGS OR TOO SMALL FOR ENERGY ANALYSIS
    # ================================================================
    'shelter': ('filter', None),
    'bird_hide': ('filter', None),
    'toilets': ('filter', None),
    'bicycle_parking': ('filter', None),
    'bicycle_parking;bicycle_rental;bicycle_repair_station': ('commercial', 'retail'),
    'workshop;bicycle_repair_station': ('commercial', 'retail'),
    'trolley_bay': ('filter', None),
    'bench': ('filter', None),
    'waste_basket': ('filter', None),
    'waste_disposal': ('filter', None),
    'telephone': ('filter', None),
    'post_box': ('filter', None),
    'atm': ('filter', None),
    'charging_station': ('filter', None),
    'bicycle_repair_station': ('commercial', 'retail'),
    'water_point': ('filter', None),
    'drinking_water': ('filter', None),
    'fountain': ('filter', None),
    'bbq': ('filter', None),
    'shower': ('filter', None),
    'dressing_room': ('filter', None),
    'changing_room': ('filter', None),
    'smoking_area': ('filter', None),
    'public_bookcase': ('filter', None),
    'parcel_locker': ('filter', None),
    'luggage_locker': ('filter', None),
    'locker': ('filter', None),
    'lockers': ('filter', None),
    'closed_box': ('filter', None),
    'vacuum_cleaner': ('filter', None),
    'compressed_air': ('filter', None),
    'sanitary_dump_station': ('filter', None),
    'kneipp_water_cure': ('filter', None),
    'lavoir': ('filter', None),
    'washing_machine': ('filter', None),
    'hitching_post': ('filter', None),
    'weighbridge': ('filter', None),
    'clock': ('filter', None),
    'bell': ('filter', None),
    'info': ('filter', None),
    'give_box': ('filter', None),
    'food_sharing': ('filter', None),
    'parking_space': ('filter', None),
    'parking_entrance': ('filter', None),
    'motorcycle_parking': ('filter', None),
    'disused': ('filter', 'disused'),
    'tree_house': ('filter', None, False),
    'disused:restaurant': ('commercial', 'food_drink'),
    'grave_yard': ('filter', None),
    'letter_box': ('filter', None),
    'bus_stop': ('filter', None),
    'stroller_parking': ('filter', None),
    'motorcycle_parking;bicycle_parking': ('filter', None),
    'shower;toilets;changing rooms': ('filter', None),
    'dressing_room;toilets': ('filter', None),
    'vacuum_cleaner;compressed_air': ('filter', None),
    'waste_disposal;recycling': ('filter', None),
    'left_luggage': ('filter', None),
    'locker_room': ('filter', None),
    'changing_cubicle': ('filter', None),
    'outdoor_seating': ('filter', None),
    'garden': ('filter', None),
    'picnic': ('filter', None),
    'grit_bin': ('filter', None),
    'elevator': ('filter', None),
    'roof': ('filter', None),
    'hut': ('filter', None),
    'shed': ('filter', None),
    'wildlife_hide': ('filter', None),
    'gas': ('filter', None),
    'boat': ('filter', None),
    'floating': ('filter', None),
    'pavilion': ('civic', 'recreation'),
    'po_box': ('filter', None),
    'toiletts': ('filter', None),
    'closed_toilets': ('filter', None),
    'weather_shelter': ('filter', None),
    'disused:pub': ('commercial', 'food_drink'),
    'disused:cafe': ('commercial', 'food_drink'),
    'disused:bank': ('commercial', 'office'),
    'abandoned:restaurant': ('commercial', 'food_drink'),
    
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
    'stairs': ('filter', None),
    'chimney': ('filter', None),
    'gate': ('filter', None),
    'sockel': ('filter', None),
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

    # Disused / abandoned
    'disused': ('filter', 'disused'),
    'deserted': ('filter', 'disused'),
    'unused': ('filter', 'disused'),
    'vacant': ('filter', 'disused'),
    'closed': ('filter', 'disused'),

    # Special case: kitchen → commercial.canteen
    'kitchen': ('commercial', 'food_drink'),

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
   'parking_entrance': ('filter', None),
    'elevator': ('filter', None),
    'annexe': ('filter', None),
    'vehicle_ramp': ('filter', None),
    'balcony': ('filter', None),

    # Common non-descriptive or temporary tags
    'collapsed': ('filter', None),


    # Ruins / demolished
    'ruins': ('filter', None),
    'ruin': ('filter', None),
    'demolished': ('filter', None),
    'abandoned': ('filter', 'disused'),
    'abandoned:yes': ('filter', 'disused'),
    'abandoned:building': ('filter', 'disused'),

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
    'stele': ('filter', None),

    # ── 1. Manufacturing (Includes food processing, heavy industry, construction materials) ──
    'factory':                 ('industrial', 'manufacturing'),
    'machine_shop':            ('industrial', 'manufacturing'),
    'machinery':               ('industrial', 'manufacturing'),
    'machine_building':        ('industrial', 'manufacturing'),
    'mechanical_engineering':  ('industrial', 'manufacturing'),
    'engineering':             ('industrial', 'manufacturing'),
    'automotive_industry':     ('industrial', 'manufacturing'),
    'mobile_equipment':        ('industrial', 'manufacturing'),
    'farm_machinery':          ('industrial', 'manufacturing'),
    'bicycle':                 ('industrial', 'manufacturing'),
    'shipyard':                ('industrial', 'manufacturing'),
    'robot':                   ('industrial', 'manufacturing'),
    'plastic':                 ('industrial', 'manufacturing'),
    'plastics':                ('industrial', 'manufacturing'),
    'plastic_processing':      ('industrial', 'manufacturing'),
    'furniture':               ('industrial', 'manufacturing'),
    'paper_mill':              ('industrial', 'manufacturing'),
    'paperboard_processing':   ('industrial', 'manufacturing'),
    'cardboard':               ('industrial', 'manufacturing'),
    'packaging':               ('industrial', 'manufacturing'),
    'printing':                ('industrial', 'manufacturing'),
    'textile':                 ('industrial', 'manufacturing'),
    'footware':                ('industrial', 'manufacturing'),
    'pharmaceutical':          ('industrial', 'manufacturing'),
    'pharmarceutical':         ('industrial', 'manufacturing'), # catching typo
    'medical':                 ('industrial', 'manufacturing'),
    'laboratory':              ('industrial', 'manufacturing'),
    'electrical':              ('industrial', 'manufacturing'),
    'telecommunication':       ('industrial', 'manufacturing'),
    'measurement_devices':     ('industrial', 'manufacturing'),
    'paint':                   ('industrial', 'manufacturing'),
    'coating':                 ('industrial', 'manufacturing'),
    'pipe_manufacturer':       ('industrial', 'manufacturing'),
    'slaughterhouse':          ('industrial', 'manufacturing'), # Food Processing
    'meat':                    ('industrial', 'manufacturing'),
    'bakery':                  ('industrial', 'manufacturing'),
    'brewery':                 ('industrial', 'manufacturing'),
    'distillery':              ('industrial', 'manufacturing'),
    'winery':                  ('industrial', 'manufacturing'),
    'beverages':               ('industrial', 'manufacturing'),
    'bottling':                ('industrial', 'manufacturing'),
    'confectionery':           ('industrial', 'manufacturing'),
    'dairy':                   ('industrial', 'manufacturing'),
    'food_industry':           ('industrial', 'manufacturing'),
    'food_processing':         ('industrial', 'manufacturing'),
    'chemical':                ('industrial', 'manufacturing'), # Heavy Industry
    'chemistery':              ('industrial', 'manufacturing'), # catching typo
    'metal_processing':        ('industrial', 'manufacturing'),
    'metal':                   ('industrial', 'manufacturing'),
    'steel':                   ('industrial', 'manufacturing'),
    'steel_construction':      ('industrial', 'manufacturing'),
    'aluminium_smelting':      ('industrial', 'manufacturing'),
    'oil':                     ('industrial', 'manufacturing'),
    'sawmill':                 ('industrial', 'manufacturing'), # Construction Materials
    'construction_company':    ('industrial', 'manufacturing'),
    'construction':            ('industrial', 'manufacturing'),
    'concrete_plant':          ('industrial', 'manufacturing'),
    'concrete':                ('industrial', 'manufacturing'),
    'asphalt_plant':           ('industrial', 'manufacturing'),
    'brickyard':               ('industrial', 'manufacturing'),
    'brick_kiln':              ('industrial', 'manufacturing'),
    'quarry':                  ('industrial', 'manufacturing'),
    'materials':               ('industrial', 'manufacturing'),
    'grinding_mill':           ('industrial', 'manufacturing'),
    'griding_mill':            ('industrial', 'manufacturing'), # catching typo

    # ── 2. Storage ──
    'warehouse':               ('industrial', 'storage'),

    # ── 3. Water & Waste Utilities ──
    'auto_wrecker':            ('industrial', 'utilities'),
    'scrap_yard':              ('industrial', 'utilities'),
    'waste_handling':          ('industrial', 'utilities'),
    'waste':                   ('industrial', 'utilities'),
    'water_treatment':         ('industrial', 'utilities'),
    'wastewater_plant':        ('industrial', 'utilities'),
    'laundry':                 ('industrial', 'manufacturing'),

    # ── 4. Energy Production ──
    'heating_station':         ('industrial', 'utilities'),
    'gas':                     ('industrial', 'utilities'),
    'power':                   ('industrial', 'utilities'),
    'energy':                  ('industrial', 'utilities'),
    'conservatory':            ('filter', None)


}


# ============================================================  
# TAG MAP FUNCTION
# ============================================================

# Normalise map once at module load — handles mixed-case keys in TAG_MAP
_TAG_MAP_NORM: dict = {
    re.sub(r'\s+', ' ', k.strip().lower()): v
    for k, v in TAG_MAP.items()
}




def _normalize(value) -> str:
    """Lowercase, collapse whitespace, strip trailing semicolons."""
    s = str(value).strip().lower()
    return re.sub(r'\s+', ' ', s).rstrip(';')


def apply_tag_map(use_value) -> tuple:
    """
    Map a raw OSM building tag value to (Level1_Type, Level2_Subtype).

    Parameters
    ----------
    use_value : str | float | None
        Raw value from the OSM 'building' tag (e.g. 'residential', 'retail;office').

    Returns
    -------
    tuple : (Level1_Type, Level2_Subtype, is_mixed)
        - Level1_Type  : top-level category string, or None if unmappable
        - Level2_Subtype : subtype string, or None

    Lookup strategy
    ---------------
    1. Normalise: lowercase, collapse whitespace, strip trailing semicolons.
    2. Direct lookup in _TAG_MAP_NORM (covers all explicit map entries,
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
    - Mixed-case keys in TAG_MAP (e.g. 'RESIDENTIAL', 'Wohnhaus')
      are normalised at import time. Where a normalised key collides with
      an existing lowercase key, last-write-wins (the lowercase entry).
    """
    if pd.isna(use_value):
        return (None, None)

    s = _normalize(use_value)

    # 1. Direct lookup
    if s in _TAG_MAP_NORM:
        return _TAG_MAP_NORM[s]

    

    #  Unmappable
    return (None, None)




# ============================================================
# VALIDATION BLOCK
# ============================================================
if __name__ == '__main__':
    total = len(TAG_MAP)
    counts = {}
    
    for v in TAG_MAP.values():
        counts[v[0]] = counts.get(v[0], 0) + 1
        
    # Safely handle mixed_c in case a tuple is accidentally too short
    mixed_c = sum(1 for v in TAG_MAP.values() if len(v) > 2 and v[2])

    print("TAG_MAP SUMMARY")
    print(f"  Total explicit mappings : {total}")
    print("-" * 30)
    
    # The Fix: key=lambda x: str(x) forces Python to sort None as "None"
    for cat in sorted(counts, key=lambda x: str(x)):
        print(f"  {str(cat):<20}: {counts[cat]}")
    print("-" * 30)
    print(f"  Mixed-use entries     : {mixed_c}\n")
    
    all_subtypes = sorted(set(v[1] for v in TAG_MAP.values() if len(v) > 1 and v[1] is not None))
    print(f"All Level 2 subtypes ({len(all_subtypes)} total):")
    for s in all_subtypes:
        print(f"  - {s}")
