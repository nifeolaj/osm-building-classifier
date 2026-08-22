"""
OSM landuse → (L1 category, L2 subtype) mapping for Germany buildings project.

L2 subtypes by L1:
  commercial   : accommodation, office, workshop, food_drink, retail,
                 personal_service, vehicle_service, rental_service, entertainment
  civic        : government_office, school, higher_ed, research, hospital, clinic,
                 sport, cultural, community, care_facility, religious,
                 emergency_service, kindergarten
 """

# Each value maps to (l1, l2)
# l2 = None means the zone confirms L1 but cannot determine subtype

POI_MAP = {
    
    # COMMERCIAL — office
    'bank'                           : ('commercial', 'office'),
    'bureau_de_change'               : ('commercial', 'office'),
    'post_office'                    : ('commercial', 'office'),
    'restaurant'                      : ('commercial', 'food_drink'),
    'cafe'                             : ('commercial', 'food_drink'),
    'bar'                              : ('commercial', 'food_drink'),
    'fast_food'                       : ('commercial', 'food_drink'),
    'pub'                               : ('commercial', 'food_drink'),
    'ice_cream'                       : ('commercial', None),
    'food_court'                      : ('commercial', 'food_drink'),
    'biergarten'                      : ('commercial', 'food_drink'),
    'bakery'                            : ('commercial', 'food_drink'),
    'cinema'                             : ('civic', 'cultural'),
    'gambling'                           : ('civic', 'recreation'),
    'nightclub'                          : ('commercial', 'food_drink'),
    'car_rental'                        : ('commercial', 'office'),
    'car_wash'                          : ('commercial', 'retail'),
    'car_repair'                         : ('commercial', 'retail'),
    'bicycle_rental'                    : ('commercial', 'office'),
    'travel_agency'                      : ('commercial', 'office'),
    'hotel'                             : ('commercial', 'accommodation'),
    'hostel'                            : ('commercial', 'accommodation'),
    'guest_house'                      : ('commercial', 'accommodation'),
    
    # ══════════════════════════════════════════
    # CIVIC
    # ══════════════════════════════════════════

    'arts_centre'                        : ('civic', 'cultural'),
    'library'                            : ('civic', 'cultural'),
    'museum'                            : ('civic', 'cultural'),
    'theatre'                           : ('civic', 'cultural'),
    'zoo'                                : ('civic', 'cultural'),
    'school'                            : ('civic', 'school'),
    'driving_school'                    : ('civic', 'school'),
    'music_school'                     : ('civic', 'school'),
    'university'                        : ('civic', 'higher_ed'),
    'college'                           : ('civic', 'higher_ed'),
    'police'                            : ('civic', 'emergency_service'),
    'social_facility'                    : ('civic', 'care_facility'),
    'social_centre'                     : ('civic', 'community'),
    'hospital'                          : ('civic', 'hospital'),
    'dentist'                        : ('civic', 'clinic'),
    'doctors'               : ('civic', 'clinic'),
    'clinic'                : ('civic', 'clinic'),
    'kindergarten'                      : ('civic', 'kindergarten'),
    'childcare'                         : ('civic', 'kindergarten'),
    
}