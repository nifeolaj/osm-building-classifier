
"""
IND_MAP — Complete mapping of all OSM industrial tag values

"""

IND_MAP = {

    

    # Core industrial
    'manufacture': 'manufacturing',
    'plant': 'energy_generation',


    # Energy & utilities
    'power': 'energy_generation',
    'power_station': 'grid_infrastructure', # substation
    'powerstation': 'grid_infrastructure', # substation
    'powerhouse': 'energy_generation',
    'power_plant': 'energy_generation',
    'electricity': 'grid_infrastructure',
    'substation': 'grid_infrastructure',
    'sub_station': 'grid_infrastructure',
    'power_substation': 'grid_infrastructure',
    'transformer': 'grid_infrastructure',
    'transformer_tower': 'grid_infrastructure',
    'transformer_house': 'grid_infrastructure',
    'transformer_kiosk': 'grid_infrastructure',
    'tech_cab': 'grid_infrastructure',
    'transformer_building': 'grid_infrastructure',
    'Umspannwerk': 'grid_infrastructure',
    'digester': 'biogas',


    # Water & pumping
    'pumping_station': 'water_utilities',
    'sewage_pumping_station': 'water_utilities',
    'water_tower': 'water_utilities',
    'wastewater_plant': 'water_utilities',
    'water_tank': 'water_utilities',
    'water_storage': 'water_utilities',
    'pump': 'water_utilities',
    'tank': 'water_utilities',

    # Storage (Option C: always → industrial.storage)
    'warehouse': 'warehouse',
    'storage': 'storage',
    'storage_tank': 'water_utilities',
    'cold_store': 'cold_storage',
    'coldstore': 'cold_storage',
    'silo': 'silo',
    
    'storage_dome': 'storage',
    'industrial;warehouse': 'warehouse',
    'warehouse;garage': 'warehouse',
    'material_storage': 'warehouse',
    'distillates_storage': 'storage',
    'lager': 'storage',
    'gasometer': 'grid_infrastructure',

    # Production buildings
    'brewery': 'food_processing',
    'slaughterhouse': 'food_processing',
    'dairy': 'food_processing',
    'sawmill': 'wood_processing',
    'production_hall': 'engineering',
    'fermenter': 'biogas',
    'fermentation_plant': 'biogas',
    'reactor': 'energy_generation',

  

    
    
    # Manufacturing / production
    'work': 'manufacturing',
    'bottling': 'food_processing',
    'grist mill': 'food_processing',

    # Chemical / heavy industry
    'chemical': 'chemical_industry',
    'mineshaft': 'mining_quarry',
    'pumping_rig': 'petroleum_industry',
    'bunker_silo': 'silo',
    'distribution_station': 'grid_infrastructure',

    # Utilities / energy / water
    'Gasversorgung': 'grid_infrastructure',
    'Sauerstoffanlage': 'chemical_industry',
    'water treatment': 'water_utilities',
    'electrical installationl': 'grid_infrastructure',
    'transformer_station': 'grid_infrastructure',
    'power transformer': 'grid_infrastructure',

    'photovoltaik': 'energy_generation', 
    'hydrogen': 'energy_generation', 
    'heat': 'heating_supply', 
    'pipeline': 'grid_infrastructure', 
    'gas_cavern': 'grid_infrastructure',
    

    'Wasserhochbehälter': 'water_utilities',
    'water_well': 'water_utilities',
    'reservoir_covered': 'water_utilities',

    # Logistics / transport
    'loading_hall': 'logistics',
    'Anlieferung': 'logistics',
    

    'industrial;storage': 'storage',
    

 
    'bakehouse': 'food_processing',
    

    # ================================================================
    # INDUSTRIAL: STORAGE AND LOGISTICS
    # ================================================================
    'depot': 'logistics',
    'car_depot': 'logistics',
    'bus_depot': 'logistics',
    'logistics': 'logistics',
    'distribution': 'logistics',
    'distributor': 'logistics',
    'container_terminal': 'logistics',
    'port': 'logistics',
    'harbour': 'logistics',
    'harbor': 'logistics',
    'trucking': 'logistics',
    'transport': 'logistics',
    'road_transport': 'logistics',
    'reloading point': 'logistics',
    'truck_service': 'logistics',


    
    'waste_transfer_station':       'waste_management',
    'works':                        'manufacturing',
    'manufactur': 'manufacturing',
    'apple-juice_factory': 'food_processing',
    'water_supply': 'water_utilities',
    'pumpstation': 'water_utilities',
    'wastewater_pump': 'water_utilities',
    'heat_plant': 'heating_supply',
    'energy_facility': 'energy_generation',
    'waste_transfer_stagion': 'waste_management',
    'healthcare': 'pharmaceutical_industry',
    
    
    # ── 1. Manufacturing (Includes food processing, heavy industry, construction materials) ──
    'machine_shop':            'engineering',
    'machinery':               'engineering',
    'machine_building':        'engineering',
    'mechanical_engineering':  'engineering',
    'engineering':             'engineering',
    'automotive_industry':     'engineering',
    'aerospace':     'engineering',
    'mobile_equipment':        'engineering',
    'farm_machinery':          'engineering',
    'bicycle':                 'engineering',
    'shipyard':                'engineering',
    'robot':                   'engineering',
    'car': 'engineering',
    'car parts': 'engineering',
    'motorhomes': 'engineering',
    'tools': 'engineering',
    'pipes': 'engineering',

    # manufacturing - core/engineering
    'factory': 'manufacturing',  'manufacturing': 'manufacturing',
    'automotive_parts': 'engineering', 'automotive': 'engineering',
     'robotics': 'engineering',
    'plant_engineering': 'engineering', 'equipment_manufacturing': 'engineering',
    'apparatus_construction': 'engineering', 'industrial_machinery': 'engineering', 
    'farm': 'engineering',
    'maintenance_yard': 'engineering', 'road_maintenance': 'engineering', 'public_works': 'engineering',
    'proving_ground': 'engineering',

    'plastic':                 'chemical_industry',
    'plastics':                'chemical_industry',
    'plastic_processing':      'chemical_industry',
    'furniture':               'wood_processing',
    'ladders':               'wood_processing',
    'paper_mill':              'wood_processing',
    'paperboard_processing':   'wood_processing',
    'cardboard':               'wood_processing',
    'timber': 'wood_processing', 
    'paper': 'wood_processing', 
    'carpenter': 'wood_processing', 
    'wood_processing': 'wood_processing', 
    'wood': 'wood_processing',
    'woodworking': 'wood_processing', 
    'window_construction': 'wood_processing',

    'packaging':               'light_manufacturing',
    'printing':                'light_manufacturing',
    'textile':                 'light_manufacturing',
    'footware':                'light_manufacturing',
    'agriculture': 'light_manufacturing',
    'printing_factory': 'light_manufacturing', 
    'printing_house': 'light_manufacturing',
    'lamps': 'light_manufacturing', 
    'tires': 'light_manufacturing',
    'consumer_goods': 'light_manufacturing', 
    'electronics': 'hightech_manufacturing', 
    'glass': 'hightech_manufacturing',
    'solid_fuel': 'energy_generation', 
    'kunstwerkstätten': 'light_manufacturing',
    'pharmaceutical':          'pharmaceutical_industry',
    'pharmarceutical':         'pharmaceutical_industry', # catching typo
    'medical':                 'pharmaceutical_industry',
    'laboratory':              'pharmaceutical_industry',
    'electrical':              'hightech_manufacturing',
    'telecommunication':       'hightech_manufacturing',
     'communication': 'hightech_manufacturing',
    'data_centre': 'hightech_manufacturing',
    'measurement_devices':     'hightech_manufacturing',
    'MDF':     'hightech_manufacturing',
    'paint':                   'chemical_industry',
    'coating':                 'chemical_industry',
    'pipe_manufacturer':       'engineering',


    # food
    'food': 'food_processing', 
    'butcher': 'food_processing',
    'sugar_beet_syrup;sugar': 'food_processing', 
    'coffee': 'food_processing',
    'mineral_water': 'food_processing', 
    'grain_mill': 'food_processing', 'feed_mill': 'food_processing',
    'fruit pressing plant': 'food_processing', 'sweet': 'food_processing', 
    'ice_factory': 'food_processing',
    'oil_mill': 'food_processing',
    'meat':                    'food_processing',
    'bakery':                  'food_processing',
    'distillery':              'food_processing',
    'winery':                  'food_processing',
    'beverages':               'food_processing',
    'confectionery':           'food_processing',
    'food_industry':           'food_processing',
    'food_processing':         'food_processing',
    'eggs':               'food_processing',
    'strawberry':           'food_processing',
    'sweets':           'food_processing',
    'clothes':         'light_manufacturing',
    'food;milch': 'food_processing',


    'chemistery':              'chemical_industry',

    'steelmaking': 'metal_industry', 
    'steelworks': 'metal_industry', 
    'steel_mill': 'metal_industry', 
    'metal_construction': 'metal_industry', 
    'cast_iron': 'metal_industry',
    'metal_processing':        'metal_industry',
    'metal':                   'metal_industry',
    'steel':                   'metal_industry',
    'steel_construction':      'metal_industry',
    'aluminium_smelting':      'metal_industry',

    # chemical_industry / pharma
    'chemistry': 'chemical_industry', 
    'chemisty': 'chemical_industry', 
    'rubber_processing': 'chemical_industry', 
    'rubber': 'chemical_industry',
    'plastic_films': 'chemical_industry', 
    'plastic_packaging': 'chemical_industry', 
    'powder_coating': 'chemical_industry',
    'galvanising;powder_coating': 'chemical_industry', 
    
    'pharmacy': 'pharmaceutical_industry',
    'pharmaceuticals': 'pharmaceutical_industry', 
    'cosmetics': 'pharmaceutical_industry', 
    'research_facility': 'pharmaceutical_industry',

    'oil':                     'petroleum_industry',
    'gas_well':                     'petroleum_industry',
    'oil_well':                     'petroleum_industry',
    'petroleum_well':                     'petroleum_industry',
    'construction_company':    'construction_materials',
    'construction':            'construction_materials',
    'concrete_plant':          'construction_materials',
    'concrete':                'construction_materials',
    'asphalt_plant':           'construction_materials',
    'brickyard':               'construction_materials',
    'brick_kiln':              'construction_materials',
    'conrete_plant': 'construction_materials',
    'concrete_mixing_facility': 'construction_materials', 
    'precast_concrete': 'construction_materials', 
    'amo-debus_asphaltmischwerk_großheirath': 'construction_materials',
    'cement': 'construction_materials', 
    'brickworks': 'construction_materials',
    'sand_lime_brickworks': 'construction_materials', 
    'roofing_tile_factory': 'construction_materials',
    'roof_tile_production': 'construction_materials', 
    'building_materials': 'construction_materials',
    'gypsum': 'construction_materials', 
    'salt': 'food_processing', 
    'plastering': 'construction_materials', 
    'sanitary_ceramic': 'construction_materials',
    
    'gravel_pit': 'mining_quarry', 
    'gravel_plant': 'mining_quarry',
    'gravel plant': 'mining_quarry', 
    'gravel': 'mining_quarry', 
    'sand_pit': 'mining_quarry', 
    'coal': 'mining_quarry', 
    'mineral_processing': 'mining_quarry',
    'quarry':                  'mining_quarry',
    'mine':                    'mining_quarry',
    'salt_pond': 'mining_quarry',
    

    'materials':               'construction_materials',
    'grinding_mill':           'manufacturing',
    'griding_mill':            'manufacturing', # catching typo

    # ── 3. Water & Waste Utilities ──
    'auto_wrecker':            'waste_management',
    'scrap_yard':              'waste_management',
    'waste_handling':          'waste_management',
    'waste':                   'waste_management',
    'recycling':                   'waste_management',
    'composting_plant':                   'waste_management',
    'waste_processing_plant':                   'waste_management',
    'water_utilities':         'water_utilities',
    'laundry':                 'light_manufacturing',

    # ── 4. Energy Production ──
    'heating_station':         'heating_supply',
    'gas':                     'grid_infrastructure',
    'energy':                  'energy_generation',
    'wellsite': 'petroleum_industry', 'refinery': 'petroleum_industry',
    'oil_storage': 'storage',
    'oil_field': 'petroleum_industry', 
    'sugar_refinery': 'food_processing',
    'water': 'water_utilities', 
    'water_management': 'water_utilities', 
     'water_treatment': 'water_utilities',
    'wastewater': 'water_utilities', 
    'wastewater_pumping': 'water_utilities',
      'sewage_plant': 'water_utilities',
    'waste_water': 'water_utilities',
      'municipal_utilities': 'water_utilities',
    'waste_disposal': 'waste_management', 
    'compost': 'waste_management',

  'beer': 'food_processing', 'asphalt': 'construction_materials', 
    'sugar': 'food_processing', 
   'biogas': 'biogas', 
    'cars': 'engineering', 'chemicals': 'chemical_industry', 
    'lumber': 'wood_processing',
    'flour': 'food_processing',  
    'malt': 'food_processing',
    'car_parts': 'engineering', 
      'wine': 'food_processing',

}

from collections import Counter


# Extract the values and count them
value_counts = Counter(IND_MAP.values())
