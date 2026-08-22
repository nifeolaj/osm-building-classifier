import re
import pandas as pd

"""
AMENITY_MAP — Complete mapping of all OSM amenity tag values
to (Level1_Type, Level2_Subtype)

Level 1 categories:
    Civic, Commercial, Industrial, Agricultural, Residential, Filter

Filter = not a building or too small to classify
   (bus shelters, bicycle stands, toilets etc)

Decision rules applied throughout:
   1. Physical building type takes priority over which tag
      field the value appears in
   2. Ambiguous values mapped to most likely physical type
   3. Non-building features mapped to Filter


Format: 'osm_value': ('Level1_Type', 'Level2_Subtype')
"""


AMENITY_MAP = {

    # ================================================================
    # CIVIC: EDUCATION
    # ================================================================
    'school': ('civic', 'school'),
    'university': ('civic', 'higher_ed'),
    'university/college': ('civic', 'higher_ed'),
    'college': ('civic', 'higher_ed'),
    'kindergarten': ('civic', 'kindergarten'),
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
    'sailing_school': ('civic', 'school'),
    'surf_school': ('civic', 'school'),
    'flight_school': ('civic', 'school'),
    'training': ('civic', 'school'),
    'education': ('civic', 'school'),
    'education_centre': ('civic', 'school'),
    'education_center': ('civic', 'school'),
    'religious_education': ('civic', 'school'),
    'academy': ('civic', 'school'),
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
    'healthcare': ('civic', 'clinic'),
    'medical_centre': ('civic', 'clinic'),
    'doctors': ('civic', 'clinic'),
    'dentist': ('civic', 'clinic'),
    'oculist;dentist': ('civic', 'clinic'),
    'pharmacy': ('commercial', 'retail'),
    'veterinary': ('civic', 'clinic'),
    'nursing_home': ('civic', 'care_facility'),
    'retirement_home': ('civic', 'care_facility'),
    'rest_home': ('civic', 'care_facility'),
    'social_facility': ('civic', 'care_facility'),
    'social_services': ('civic', 'care_facility'),
    'rehabilitation': ('civic', 'care_facility'),
    'blood_donation': ('civic', 'clinic'),
    'red_cross': ('civic', 'care_facility'),
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
    'wellness': ('commercial', 'other_service'),
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
    'embassy': ('civic', 'government_office'),
    'post_office': ('commercial', 'office'),
    'post_depot': ('commercial', 'office'),
    'register_office': ('civic', 'government_office'),
    'public_building': ('civic', None),
    'government': ('civic', 'government_office'),
    'public': ('civic', None),
    'immigration': ('civic', 'government_office'),
    'job_centre': ('civic', 'office'),
    'ranger_station': ('civic', 'government_office'),
    'forestry_office': ('civic', 'government_office'),
    'forester': ('commercial', 'office'),
    'customs': ('civic', 'government_office'),
    'prosecution': ('civic', 'government_office'),
    'ambulance_station': ('civic', 'emergency_service'),
    'refugee_housing': ('civic', 'care_facility'),
    'refugee_site': ('civic', 'care_facility'),
    'public_facility': ('civic', None),
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
    'funeral_hall': ('civic', 'community'),
    'furneral_hall': ('civic', 'community'),
    'funeral_home': ('civic', 'community'),
    'crematorium': ('civic', 'community'),
    'mortuary': ('civic', 'community'),
    'place_of_mourning': ('civic', 'community'),
    'crypt': ('civic', 'religious'),
    'cheaple': ('civic', 'religious'),
    'religious': ('civic', 'religious'),
    'bell_tower': ('filter', None),
    'altar': ('civic', 'religious'),
    'parish_office': ('civic', 'religious'),
    'parish_rooms': ('civic', 'religious'),
    'Pfarrzentrum': ('civic', 'community'),
    'vacarage': ('residential', 'SFH'),
    'cemetery_hall': ('civic', 'community'),
    'gravesite': ('filter', None),
    'urn_wall': ('filter', None),
    'masonic_lodge': ('civic', 'religious'),

    # ================================================================
    # CIVIC: CULTURE AND COMMUNITY
    # ================================================================
    'community_centre': ('civic', 'community'),
    'community_hall': ('civic', 'community'),
    'public_hall': ('civic', 'community'),
    'social_centre': ('civic', 'community'),
    'social_club': ('civic', 'community'),
    'club_home': ('civic', 'community'),
    'village_hall': ('civic', 'community'),
    'recreation_center': ('civic', 'community'),
    'clubhouse': ('civic', 'community'),
    'fraternity': ('civic', 'community'),
    'scout_hut': ('civic', 'community'),
    'scout_hall': ('civic', 'community'),
    'charity': ('civic', 'community'),
    'youth_centre': ('civic', 'community'),
    'animal_shelter': ('civic', 'care_facility'),
    'arts_centre': ('civic', 'cultural'),
    'arts_centre;community_centre': ('civic', 'cultural'),
    'theatre': ('civic', 'cultural'),
    'cinema': ('civic', 'cultural'),
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
    'auditorium': ('civic', None),
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
    'space_centre': ('civic', 'cultural'),
    'festival_hall': ('civic', 'cultural'),
    'exhibition_centre;concert_hall': ('civic', 'cultural'),
    'conference_centre;events_venue': ('civic', 'community'),
    'events_venue;parking': ('civic', 'community'),
    'multi-purpose_hall': ('civic', None),
    'multi-porpose hall': ('civic', None),
    'multipurpose_hall': ('civic', None),
    'assembly hall': ('civic', None),
    'event management': ('commercial', 'office'),
    'event_rental': ('commercial', 'office'),
    'events_vemnue': ('civic', 'community'),
    'grandstand': ('civic', 'recreation'),
    'animal_shelter;animal_boarding': ('civic', 'care_facility'),
    'petting_zoo': ('filter', None),

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
    'commercial': ('commercial', None),
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
    'boat_rental': ('commercial', 'office'),
    'boat_sharing': ('filter', None),
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
    'beauty': ('commercial', 'other_service'),
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
    'static_caravan': ('filter', None),

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
    'water_storage':                ('industrial', 'utilities'),
    'waste_transfer_station':       ('industrial', 'utilities'),
    'disposal':                     ('filter', None),
    'works':                        ('industrial', 'manufacturing'),
    # --- newly added industrial ---
    'industry': ('industrial', None),
    'slaughterhouse': ('industrial', 'manufacturing'),
    'manufactur': ('industrial', 'manufacturing'),
    'apple-juice_factory': ('industrial', 'manufacturing'),
    'water_works': ('industrial', 'utilities'),
    'water_supply': ('industrial', 'utilities'),
    'pumping_station': ('industrial', 'utilities'),
    'pumpstation': ('industrial', 'utilities'),
    'pump': ('industrial', 'utilities'),
    'wastewater_pump': ('industrial', 'utilities'),
    'heat_plant': ('industrial', 'utilities'),
    'energy_facility': ('industrial', 'utilities'),
    'waste_transfer_stagion': ('industrial', 'utilities'),
    'cold_store': ('industrial', 'storage'),
    'public_works': ('industrial', None),
    'caravan_storage': ('filter', None),
    'snow_removal_station': ('filter', None),
    'plant_nursery': ('agricultural', 'greenhouse'),

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
    
}



_AMENITY_MAP_NORM: dict = {
    re.sub(r'\s+', ' ', k.strip().lower()): v
    for k, v in AMENITY_MAP.items()
}


def apply_amenity_map(amenity_value) -> tuple:
    """
    Map a raw OSM amenity tag value to (Level1_Type, Level2_Subtype).

    Parameters
    ----------
    amenity_value : str | float | None
        Raw value from the OSM 'amenity' tag (e.g. 'hospital', 'school;clinic').

    Returns
    -------
    tuple : (Level1_Type, Level2_Subtype)
        Both elements are None if the value is unmappable.

    Lookup strategy
    ---------------
    1. Normalise: lowercase, collapse whitespace, strip trailing semicolons.
    2. Direct lookup in _AMENITY_MAP_NORM.
    3. Return (None, None) if unmappable.

    Notes
    -----
    - AMENITY_MAP returns 2-tuples (no is_mixed field); use apply_building_map
      or apply_building_use_map for mixed-use resolution.
    - Mixed-case keys in AMENITY_MAP are normalised at import time.
    """
    if pd.isna(amenity_value):
        return (None, None)

    s = re.sub(r'\s+', ' ', str(amenity_value).strip().lower()).rstrip(';')

    # Direct lookup
    if s in _AMENITY_MAP_NORM:
        return _AMENITY_MAP_NORM[s]

    # Unmappable
    return (None, None)


# ============================================================
# APPLY AND VALIDATE
# ============================================================


if __name__ == '__main__':
    print(f"Total AMENITY_MAP entries: {len(AMENITY_MAP)}")

    from collections import Counter
    type_counts = Counter(v[0] if v is not None else None for v in AMENITY_MAP.values())
    print(f"\nType breakdown:")
    for type_, count in sorted(type_counts.items(), key=lambda x: (-x[1], str(x[0]))):
        print(f"  {str(type_):<30} {count:>5} tag values mapped to this type")
    subtype_counts = Counter(v[1] if v is not None else None for v in AMENITY_MAP.values())
    print(f"\nSubtype breakdown:")
    for subtype, count in sorted(subtype_counts.items(), key=lambda x: (-x[1], str(x[0]))):
        print(f"  {str(subtype):<30} {count:>5} tag values mapped to this subtype")


    