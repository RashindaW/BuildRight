"""Deterministic generator for a large, realistic BuildRight AI catalog.

Produces ~1000+ products across 20 retail categories, each with a unique SKU
(BR-XXX-NNNNN), realistic name/description/keywords/price/stock and tags. Output
dicts match the MENU_DATA schema so the seed ingests them unchanged, plus 'sku'
and 'stock' fields.

Pure + deterministic (fixed RNG seed) so re-seeding is reproducible.
"""

from __future__ import annotations

import random
import re

# ---- Variant axes (label, price multiplier) -------------------------------

AXES = {
    "VOLT": [("12V", 0.70), ("18V", 1.00), ("20V MAX", 1.15), ("40V", 1.75), ("60V", 2.4)],
    "GRADE": [("", 1.00), ("Pro", 1.45), ("Heavy-Duty", 1.30), ("Compact", 0.85)],
    "SIZE_IN": [('1/4"', 0.80), ('3/8"', 1.00), ('1/2"', 1.30), ('3/4"', 1.65), ('1"', 2.0)],
    "PACK": [("10-Pack", 1.0), ("25-Pack", 2.0), ("50-Pack", 3.4), ("100-Pack", 5.8), ("250-Pack", 12.0)],
    "LEN_FT": [("25 ft", 1.0), ("50 ft", 1.7), ("100 ft", 2.8), ("150 ft", 3.9)],
    "CAP": [("5 L", 1.0), ("10 L", 1.6), ("20 L", 2.6), ("40 L", 4.2)],
    "GRIT": [("60-Grit", 1.0), ("80-Grit", 1.0), ("120-Grit", 1.0), ("220-Grit", 1.05)],
    "COLOUR": [("White", 1.0), ("Black", 1.0), ("Brushed Nickel", 1.15), ("Matte Grey", 1.05), ("Bronze", 1.2)],
    "AMP": [("3-Amp", 1.0), ("5-Amp", 1.3), ("7.5-Amp", 1.6), ("12-Amp", 2.0)],
    "SIZE_S": [("Compact", 0.8), ("Standard", 1.0), ("Large", 1.3), ("X-Large", 1.6)],
    "WATT": [("40W", 0.8), ("60W", 1.0), ("100W", 1.4), ("150W", 1.9)],
}

# Secondary "edition" dimension. Only used when scaling to a large target catalog;
# multiplies the SKU count while keeping names plausible across every category.
SERIES = [("", 1.0), ("Series 2", 1.05), ("Contractor", 1.20), ("Pro Series", 1.45)]

# ---- House + general brands by category flavour ---------------------------

TOOL_BRANDS = ["Mastercraft", "ProBuilt", "IronClad", "VoltEdge"]
HOME_BRANDS = ["BuildRight", "EverBrite", "Mastercraft", "TundraGuard"]
PLUMB_BRANDS = ["AquaFlow", "BuildRight", "ProBuilt"]
GARDEN_BRANDS = ["GreenThumb", "Mastercraft", "TundraGuard"]
AUTO_BRANDS = ["IronClad", "VoltEdge", "ProBuilt"]


def T(name, base, spec, kw, axis, tags=(), flags=()):
    return {"name": name, "base": base, "spec": spec, "kw": list(kw),
            "axis": axis, "tags": list(tags), "flags": list(flags)}


# ---- Category definitions: slug, label, sku code, brands, product types ----

CATEGORIES = [
    {"slug": "power-tools", "label": "Power Tools", "code": "PWR", "brands": TOOL_BRANDS, "types": [
        T("Cordless Drill/Driver", 79, "Brushless motor with 2-speed gearbox, keyless chuck and LED work light for drilling and driving.", ["drill", "driver", "cordless", "screwgun"], "VOLT", ["cordless", "battery-powered"], ["contains-battery", "power-tool"]),
        T("Hammer Drill", 119, "Hammer-and-drill modes for masonry, concrete and wood with variable-speed trigger.", ["hammer drill", "masonry", "concrete drill"], "VOLT", ["cordless"], ["contains-battery", "power-tool"]),
        T("Impact Driver", 99, "High-torque impact mechanism drives long fasteners and lag bolts without stripping.", ["impact driver", "impact", "fastening"], "VOLT", ["cordless"], ["contains-battery", "power-tool"]),
        T("Circular Saw", 89, "15-amp class motor for fast, accurate cross and rip cuts in lumber and plywood with bevel adjustment.", ["circular saw", "cutting", "lumber", "plywood"], "AMP", ["corded", "professional"], ["sharp-blade", "power-tool"]),
        T("Jigsaw", 69, "Orbital-action jigsaw for curved and plunge cuts in wood, metal and plastic; tool-free blade change.", ["jigsaw", "curved cuts", "scroll"], "AMP", ["corded"], ["sharp-blade", "power-tool"]),
        T("Reciprocating Saw", 109, "Demolition saw with tool-free blade changes for cutting wood, metal pipe and nail-embedded lumber.", ["reciprocating saw", "recip", "demolition", "sawzall"], "VOLT", ["cordless"], ["sharp-blade", "power-tool"]),
        T("Angle Grinder", 59, "Cuts, grinds and polishes metal and masonry; restart protection and guard adjustment.", ["angle grinder", "grinder", "metal cutting"], "AMP", ["corded"], ["sharp-blade", "power-tool"]),
        T("Random Orbital Sander", 49, "Hook-and-loop pad with dust collection and variable speed for swirl-free finish sanding.", ["sander", "orbital", "finishing"], "AMP", ["corded"], ["power-tool"]),
        T("Router", 129, "Plunge-and-fixed-base router for edge profiling, dadoes and joinery with micro depth adjust.", ["router", "woodworking", "edge", "trim"], "AMP", ["corded", "professional"], ["sharp-blade", "power-tool"]),
        T("Oscillating Multi-Tool", 79, "Sands, cuts, scrapes and grinds in tight spaces with quick-change accessory interface.", ["multi-tool", "oscillating", "flush cut"], "VOLT", ["cordless"], ["contains-battery", "power-tool"]),
        T("Heat Gun", 39, "Dual-temperature heat gun for paint stripping, shrink tubing and thawing pipes.", ["heat gun", "paint stripping", "shrink"], "WATT", ["corded"], ["power-tool", "flammable"]),
        T("Mitre Saw", 199, "Sliding compound mitre saw for precise crosscuts and angled cuts in trim and framing lumber.", ["mitre saw", "miter", "crosscut", "trim"], "AMP", ["corded", "professional"], ["sharp-blade", "power-tool", "heavy-item"]),
    ]},
    {"slug": "hand-tools", "label": "Hand Tools", "code": "HND", "brands": TOOL_BRANDS, "types": [
        T("Claw Hammer", 24, "Forged steel head with anti-vibration handle and balanced swing for driving and pulling nails.", ["hammer", "claw hammer", "nails"], "GRADE", [], ["sharp-blade"]),
        T("Screwdriver Set", 29, "Hardened tips in slotted and Phillips sizes with magnetic, cushion-grip handles.", ["screwdriver", "phillips", "slotted", "set"], "PACK", [], []),
        T("Adjustable Wrench", 19, "Wide-opening adjustable wrench with laser-etched jaw scale and corrosion-resistant finish.", ["wrench", "adjustable", "crescent"], "SIZE_IN", [], []),
        T("Tape Measure", 14, "Nylon-coated blade with standout and magnetic hook; impact-resistant case.", ["tape measure", "measuring", "layout"], "SIZE_S", [], []),
        T("Utility Knife", 12, "Retractable utility knife with quick-change blades and on-board blade storage.", ["utility knife", "box cutter", "blade"], "GRADE", [], ["sharp-blade"]),
        T("Pliers Set", 34, "Slip-joint, long-nose and diagonal pliers with hardened cutting edges and comfort grips.", ["pliers", "long nose", "cutters", "set"], "PACK", [], ["sharp-blade"]),
        T("Socket Set", 59, "Chrome-vanadium sockets with quick-release ratchet in metric and SAE sizes.", ["socket set", "ratchet", "metric", "sae"], "PACK", ["professional"], []),
        T("Hex Key Set", 11, "Long-arm hex (Allen) keys with ball ends and a folding holder.", ["hex key", "allen", "wrench set"], "PACK", [], []),
        T("Hand Saw", 22, "Sharp triple-ground teeth cut on the push and pull stroke for fast, clean cuts.", ["hand saw", "wood saw", "carpentry"], "SIZE_S", [], ["sharp-blade"]),
        T("Spirit Level", 27, "Shock-absorbing frame with high-visibility vials for level and plumb layout.", ["level", "spirit level", "layout"], "SIZE_S", [], []),
        T("Pry Bar", 17, "Heat-treated pry bar with nail-pulling slot for demolition and dismantling.", ["pry bar", "crowbar", "wrecking"], "SIZE_S", [], []),
        T("Tool Bag", 39, "Heavy-duty tool bag with reinforced base and multiple pockets for organized carry.", ["tool bag", "storage", "carry"], "SIZE_S", [], []),
    ]},
    {"slug": "fasteners", "label": "Fasteners & Hardware", "code": "FAS", "brands": HOME_BRANDS, "types": [
        T("Wood Screws", 8, "Zinc-plated wood screws with sharp points and deep threads for strong grip in softwood and hardwood.", ["screws", "wood screws", "fasteners"], "PACK", [], []),
        T("Deck Screws", 12, "Coated exterior deck screws resist corrosion for pressure-treated lumber and outdoor builds.", ["deck screws", "exterior", "coated"], "PACK", ["outdoor"], []),
        T("Drywall Screws", 9, "Bugle-head drywall screws with fine or coarse thread for board to stud or metal.", ["drywall screws", "wallboard"], "PACK", [], []),
        T("Hex Bolts", 11, "Grade-5 zinc hex bolts for structural and machinery fastening.", ["bolts", "hex bolts", "grade 5"], "PACK", [], []),
        T("Anchors", 10, "Wall anchors for drywall, masonry and concrete with matching screws included.", ["anchors", "wall anchors", "concrete"], "PACK", [], []),
        T("Nails", 7, "Bright common nails for framing and general construction.", ["nails", "common nails", "framing"], "PACK", [], ["sharp-blade"]),
        T("Cabinet Hinges", 14, "Soft-close concealed cabinet hinges with adjustable mounting plates.", ["hinges", "cabinet", "soft close"], "PACK", [], []),
        T("Door Hardware Set", 39, "Privacy and passage lockset with matching latch and strike plate.", ["door knob", "lockset", "handle"], "COLOUR", [], []),
        T("Picture Hanging Kit", 9, "Assorted hooks, wire and hardware for hanging frames and mirrors securely.", ["picture hooks", "hanging", "wall"], "PACK", [], []),
        T("Threaded Rod", 13, "Zinc all-thread rod for hanging, bracing and custom fastening.", ["threaded rod", "all thread"], "SIZE_IN", [], []),
        T("Washers Assortment", 8, "Flat and lock washers in common sizes in a sorted case.", ["washers", "flat", "lock"], "PACK", [], []),
    ]},
    {"slug": "automotive", "label": "Automotive", "code": "AUT", "brands": AUTO_BRANDS, "types": [
        T("Motor Oil", 32, "Full-synthetic motor oil for engine protection and extended drain intervals.", ["motor oil", "synthetic", "engine", "5w30"], "CAP", [], ["flammable"]),
        T("Wiper Blades", 19, "All-season beam wiper blades with aerodynamic, streak-free design.", ["wiper blades", "windshield"], "SIZE_S", [], []),
        T("Car Battery", 149, "Maintenance-free lead-acid car battery with high cold-cranking amps.", ["car battery", "12v", "cca"], "GRADE", [], ["contains-battery", "heavy-item"]),
        T("Jump Starter", 89, "Portable lithium jump starter with USB power bank and built-in light.", ["jump starter", "booster", "portable"], "GRADE", ["battery-powered"], ["contains-battery"]),
        T("Floor Jack", 99, "Hydraulic floor jack with quick-lift for cars and light trucks.", ["floor jack", "hydraulic", "lift"], "GRADE", [], ["heavy-item"]),
        T("Tire Inflator", 49, "12V digital tire inflator with auto-stop and pressure gauge.", ["tire inflator", "air compressor", "12v"], "GRADE", ["battery-powered"], []),
        T("Microfibre Towels", 14, "Lint-free microfibre detailing towels for wash, wax and interior.", ["microfibre", "detailing", "towels"], "PACK", [], []),
        T("Windshield Washer Fluid", 8, "All-season washer fluid with de-icer and bug remover.", ["washer fluid", "de-icer"], "CAP", [], ["flammable"]),
        T("Wrench Set (Metric)", 44, "Combination metric wrenches with chrome finish for automotive work.", ["wrench set", "metric", "combination"], "PACK", ["professional"], []),
        T("Car Cover", 59, "Breathable all-weather car cover with elastic hem and tie-downs.", ["car cover", "weatherproof"], "SIZE_S", ["outdoor"], []),
    ]},
    {"slug": "kitchen", "label": "Kitchen & Appliances", "code": "KIT", "brands": HOME_BRANDS, "types": [
        T("Cordless Kettle", 39, "Rapid-boil stainless kettle with auto shut-off and boil-dry protection.", ["kettle", "electric kettle", "boil"], "CAP", [], []),
        T("Toaster", 34, "Wide-slot toaster with browning control and reheat/defrost settings.", ["toaster", "bread"], "SIZE_S", [], []),
        T("Blender", 59, "High-power blender with pulse and crush-ice settings and dishwasher-safe jar.", ["blender", "smoothie", "crush ice"], "WATT", [], []),
        T("Cookware Set", 119, "Non-stick aluminum cookware set with tempered-glass lids and stay-cool handles.", ["cookware", "pots", "pans", "non-stick"], "PACK", [], []),
        T("Knife Block Set", 69, "Stainless knife set with hardwood block and built-in sharpener.", ["knife set", "kitchen knives", "block"], "PACK", [], ["sharp-blade"]),
        T("Food Storage Containers", 24, "Stackable airtight containers with leak-proof, snap-lock lids.", ["food storage", "containers", "airtight"], "PACK", [], []),
        T("Coffee Maker", 49, "Programmable drip coffee maker with reusable filter and keep-warm plate.", ["coffee maker", "drip", "programmable"], "SIZE_S", [], []),
        T("Air Fryer", 99, "Rapid-air fryer with digital presets for crispy results with less oil.", ["air fryer", "convection"], "CAP", [], []),
        T("Microwave Oven", 109, "Countertop microwave with sensor cooking and one-touch presets.", ["microwave", "countertop"], "WATT", [], ["heavy-item"]),
        T("Dish Rack", 19, "Rust-resistant dish rack with utensil holder and drainboard.", ["dish rack", "drying"], "SIZE_S", [], []),
    ]},
    {"slug": "outdoor", "label": "Outdoor Power Equipment", "code": "OUT", "brands": GARDEN_BRANDS, "types": [
        T("Lawn Mower", 329, "Self-propelled mower with mulch, bag and side-discharge and adjustable cutting height.", ["lawn mower", "mower", "grass"], "VOLT", ["cordless", "outdoor"], ["contains-battery", "heavy-item"]),
        T("String Trimmer", 119, "Brushless string trimmer with bump-feed head for edging and trimming.", ["string trimmer", "weed eater", "edger"], "VOLT", ["cordless", "outdoor"], ["contains-battery"]),
        T("Leaf Blower", 99, "Axial leaf blower with variable speed and turbo boost for fast cleanup.", ["leaf blower", "blower", "yard"], "VOLT", ["cordless", "outdoor"], ["contains-battery"]),
        T("Hedge Trimmer", 109, "Dual-action hedge trimmer with hardened steel blades for clean cuts.", ["hedge trimmer", "shrub", "pruning"], "VOLT", ["cordless", "outdoor"], ["contains-battery", "sharp-blade"]),
        T("Pressure Washer", 199, "High-pressure washer with multiple nozzles for decks, siding and driveways.", ["pressure washer", "power washer", "cleaning"], "GRADE", ["outdoor"], ["heavy-item"]),
        T("Chainsaw", 179, "Cordless chainsaw with tool-free chain tensioning and auto-oiler.", ["chainsaw", "cutting", "firewood"], "VOLT", ["cordless", "outdoor"], ["contains-battery", "sharp-blade"]),
        T("Wheelbarrow", 89, "Steel-tray wheelbarrow with pneumatic tire for hauling soil and debris.", ["wheelbarrow", "hauling", "yard cart"], "CAP", ["outdoor"], ["heavy-item"]),
        T("Garden Hose", 34, "Kink-resistant garden hose with crush-proof couplings.", ["garden hose", "watering"], "LEN_FT", ["outdoor"], []),
        T("Patio Heater", 199, "Propane patio heater with stainless burner and tip-over safety shut-off.", ["patio heater", "propane", "outdoor heat"], "GRADE", ["outdoor"], ["flammable", "heavy-item"]),
        T("Propane Tank", 59, "Refillable 20 lb propane tank for BBQs and patio heaters.", ["propane", "tank", "bbq fuel"], "GRADE", ["outdoor"], ["flammable", "heavy-item"]),
    ]},
    {"slug": "lawn-garden", "label": "Lawn & Garden", "code": "LWN", "brands": GARDEN_BRANDS, "types": [
        T("Garden Soil", 9, "Nutrient-rich garden soil for planting beds, vegetables and flowers.", ["garden soil", "potting", "planting"], "CAP", ["outdoor"], ["heavy-item"]),
        T("Mulch", 6, "Natural bark mulch retains moisture and suppresses weeds.", ["mulch", "bark", "landscaping"], "CAP", ["outdoor"], ["heavy-item"]),
        T("Garden Tool Set", 29, "Stainless hand tools — trowel, cultivator and transplanter — with ergonomic grips.", ["garden tools", "trowel", "hand tools"], "PACK", ["outdoor"], []),
        T("Pruning Shears", 22, "Bypass pruners with hardened blades and sap groove for clean cuts.", ["pruning shears", "secateurs", "pruners"], "GRADE", ["outdoor"], ["sharp-blade"]),
        T("Watering Can", 14, "Durable watering can with removable rose for gentle watering.", ["watering can", "watering"], "CAP", ["outdoor"], []),
        T("Plant Pots", 12, "Frost-resistant planter pots with drainage holes for indoor and patio.", ["plant pots", "planters", "containers"], "PACK", ["outdoor"], []),
        T("Lawn Fertilizer", 24, "Slow-release lawn fertilizer for greener, thicker turf.", ["fertilizer", "lawn food", "turf"], "CAP", ["outdoor"], []),
        T("Grass Seed", 19, "Hard-wearing grass seed blend for sun and shade lawns.", ["grass seed", "lawn seed", "overseeding"], "CAP", ["outdoor"], []),
        T("Garden Gloves", 9, "Breathable garden gloves with grippy palms and reinforced fingertips.", ["garden gloves", "gloves"], "SIZE_S", ["outdoor"], []),
        T("Raised Garden Bed", 79, "Modular raised garden bed kit for vegetables and herbs.", ["raised bed", "garden bed", "planter box"], "SIZE_S", ["outdoor"], ["requires-assembly"]),
    ]},
    {"slug": "cleaning", "label": "Cleaning", "code": "CLN", "brands": HOME_BRANDS, "types": [
        T("All-Purpose Cleaner", 7, "Concentrated all-purpose cleaner cuts grease and grime on most surfaces.", ["cleaner", "all purpose", "degreaser"], "CAP", [], ["flammable"]),
        T("Microfibre Mop", 24, "Spin mop with microfibre head and bucket wringer for streak-free floors.", ["mop", "microfibre", "floor"], "SIZE_S", [], []),
        T("Shop Vacuum", 79, "Wet/dry shop vac with blower port and reusable filter for the garage.", ["shop vac", "wet dry vacuum", "garage"], "CAP", [], []),
        T("Broom and Dustpan", 14, "Angled broom with clip-on dustpan for fine and coarse debris.", ["broom", "dustpan", "sweeping"], "SIZE_S", [], []),
        T("Disinfectant Wipes", 6, "Multi-surface disinfectant wipes kill common household germs.", ["wipes", "disinfectant", "sanitizing"], "PACK", [], []),
        T("Garbage Bags", 11, "Heavy-duty drawstring garbage bags resist tears and leaks.", ["garbage bags", "trash bags", "drawstring"], "PACK", [], []),
        T("Glass Cleaner", 6, "Ammonia-free glass cleaner for streak-free windows and mirrors.", ["glass cleaner", "window"], "CAP", [], []),
        T("Sponges and Scrubbers", 5, "Non-scratch scrub sponges for dishes and surfaces.", ["sponges", "scrubbers", "scouring"], "PACK", [], []),
        T("Pressure Washer Soap", 12, "Concentrated detergent for pressure washers and outdoor cleaning.", ["soap", "detergent", "pressure washer"], "CAP", ["outdoor"], ["flammable"]),
        T("Push Broom", 27, "Wide push broom with stiff bristles for garages, decks and driveways.", ["push broom", "yard broom"], "SIZE_S", ["outdoor"], []),
    ]},
    {"slug": "paint", "label": "Paint & Coatings", "code": "PNT", "brands": HOME_BRANDS, "types": [
        T("Interior Paint", 39, "Low-VOC interior latex paint with primer for a durable, washable finish.", ["paint", "interior", "latex", "primer"], "CAP", [], ["flammable"]),
        T("Exterior Paint", 49, "Weatherproof exterior acrylic paint resists fading, mildew and cracking.", ["exterior paint", "acrylic", "weatherproof"], "CAP", ["outdoor"], ["flammable"]),
        T("Primer", 29, "High-hide stain-blocking primer for drywall, wood and previously painted surfaces.", ["primer", "undercoat", "stain block"], "CAP", [], ["flammable"]),
        T("Paint Brush Set", 14, "Angled and flat synthetic-bristle brushes for cutting in and trim.", ["paint brush", "brushes", "trim"], "PACK", [], []),
        T("Paint Roller Kit", 16, "Roller frame, sleeves and tray kit for walls and ceilings.", ["roller", "paint roller", "kit"], "PACK", [], []),
        T("Wood Stain", 24, "Penetrating oil stain enriches grain and protects interior wood.", ["wood stain", "stain", "finish"], "CAP", [], ["flammable"]),
        T("Spray Paint", 8, "Fast-dry enamel spray paint with even coverage for metal, wood and plastic.", ["spray paint", "enamel", "aerosol"], "COLOUR", [], ["flammable"]),
        T("Painter's Tape", 7, "Clean-release painter's tape leaves sharp lines without residue.", ["painters tape", "masking", "tape"], "PACK", [], []),
        T("Drop Cloth", 12, "Heavy canvas drop cloth protects floors and furniture from spills.", ["drop cloth", "tarp", "protection"], "SIZE_S", [], []),
        T("Caulk", 6, "Paintable acrylic-latex caulk seals gaps around trim, windows and baseboards.", ["caulk", "sealant", "gaps"], "GRADE", [], ["flammable"]),
    ]},
    {"slug": "electrical", "label": "Electrical", "code": "ELE", "brands": ["VoltEdge", "BuildRight", "EverBrite"], "types": [
        T("Extension Cord", 24, "Heavy-duty grounded extension cord with weather-resistant jacket for indoor/outdoor use.", ["extension cord", "power cord", "outdoor"], "LEN_FT", ["outdoor"], []),
        T("Power Bar", 19, "Surge-protecting power bar with multiple outlets and USB charging ports.", ["power bar", "surge protector", "outlets"], "SIZE_S", [], []),
        T("Wall Outlets", 9, "Tamper-resistant receptacles for safe, code-compliant residential wiring.", ["outlets", "receptacle", "plug"], "PACK", [], []),
        T("Light Switch", 8, "Quiet rocker light switches with screw and push-in terminals.", ["light switch", "rocker", "switch"], "PACK", [], []),
        T("Electrical Wire", 39, "NMD90 building wire for residential branch circuits.", ["wire", "romex", "building wire"], "LEN_FT", [], []),
        T("Wire Connectors", 7, "Twist-on wire connectors in assorted sizes for secure splices.", ["wire connectors", "marrettes", "nuts"], "PACK", [], []),
        T("Voltage Tester", 17, "Non-contact voltage tester with audible and visual alerts.", ["voltage tester", "multimeter", "tester"], "GRADE", ["battery-powered"], ["contains-battery"]),
        T("Smoke Detector", 22, "Photoelectric smoke alarm with battery backup and test button.", ["smoke detector", "alarm", "safety"], "GRADE", ["battery-powered"], ["contains-battery"]),
        T("Doorbell", 29, "Wireless doorbell with multiple chimes and long range.", ["doorbell", "wireless", "chime"], "GRADE", ["battery-powered"], ["contains-battery"]),
        T("Electrical Tape", 5, "Vinyl electrical tape resists abrasion, moisture and heat.", ["electrical tape", "vinyl", "insulating"], "PACK", [], []),
    ]},
    {"slug": "plumbing", "label": "Plumbing", "code": "PLM", "brands": PLUMB_BRANDS, "types": [
        T("Kitchen Faucet", 119, "Pull-down kitchen faucet with spot-resist finish and ceramic-disc valve.", ["faucet", "kitchen tap", "pull down"], "COLOUR", [], []),
        T("Bathroom Faucet", 79, "Two-handle bathroom faucet with drain assembly and water-efficient flow.", ["faucet", "bathroom tap", "lavatory"], "COLOUR", [], []),
        T("Toilet", 159, "High-efficiency dual-flush toilet with elongated bowl and soft-close seat.", ["toilet", "dual flush", "bathroom"], "GRADE", [], ["heavy-item"]),
        T("Shower Head", 34, "Rain shower head with multiple spray settings and easy-clean nozzles.", ["shower head", "rain shower"], "COLOUR", [], []),
        T("Sump Pump", 129, "Submersible sump pump protects basements from flooding with automatic float switch.", ["sump pump", "submersible", "basement"], "GRADE", [], ["heavy-item"]),
        T("PEX Pipe", 29, "Flexible PEX water-supply tubing for hot and cold residential plumbing.", ["pex", "pipe", "tubing", "water supply"], "LEN_FT", [], []),
        T("Pipe Wrench", 27, "Heavy-duty pipe wrench with self-cleaning threads and hardened jaws.", ["pipe wrench", "plumbing tool"], "SIZE_IN", ["professional"], []),
        T("Plunger", 12, "Heavy-duty flange plunger clears toilet and drain clogs.", ["plunger", "drain", "clog"], "GRADE", [], []),
        T("Plumber's Tape", 4, "PTFE thread-seal tape prevents leaks on threaded pipe joints.", ["plumbers tape", "teflon", "thread seal"], "PACK", [], []),
        T("Water Heater", 449, "Energy-efficient tank water heater with fast recovery for whole-home hot water.", ["water heater", "hot water tank"], "CAP", [], ["heavy-item"]),
    ]},
    {"slug": "lighting", "label": "Lighting", "code": "LGT", "brands": ["VoltEdge", "EverBrite", "BuildRight"], "types": [
        T("LED Bulbs", 12, "Energy-efficient LED bulbs with warm or daylight colour and long rated life.", ["led bulbs", "light bulbs", "energy efficient"], "PACK", [], []),
        T("Shop Light", 34, "Linkable LED shop light for garages and workshops with bright, even output.", ["shop light", "led", "garage light"], "WATT", [], []),
        T("Flashlight", 24, "Rechargeable aluminum flashlight with high-lumen output and multiple modes.", ["flashlight", "torch", "rechargeable"], "GRADE", ["battery-powered"], ["contains-battery"]),
        T("Work Light", 49, "Portable LED work light on a stand for job sites and projects.", ["work light", "job site light", "led"], "WATT", [], []),
        T("Ceiling Fixture", 59, "Flush-mount LED ceiling fixture with frosted diffuser for rooms and hallways.", ["ceiling light", "fixture", "flush mount"], "COLOUR", [], []),
        T("Outdoor Security Light", 44, "Motion-activated LED security light with adjustable heads and dusk-to-dawn mode.", ["security light", "motion", "outdoor"], "WATT", ["outdoor"], []),
        T("Solar Path Lights", 29, "Solar-powered LED path lights charge by day and light walkways at night.", ["solar lights", "path lights", "landscape"], "PACK", ["outdoor", "battery-powered"], ["contains-battery"]),
        T("String Lights", 19, "Weatherproof LED string lights for patios, decks and events.", ["string lights", "patio lights"], "LEN_FT", ["outdoor"], []),
        T("Headlamp", 17, "Hands-free LED headlamp with adjustable beam and red night mode.", ["headlamp", "head torch"], "GRADE", ["battery-powered"], ["contains-battery"]),
        T("Smart Bulb", 16, "Wi-Fi smart LED bulb with app control, dimming and colour scenes.", ["smart bulb", "wifi", "smart home"], "PACK", [], []),
    ]},
    {"slug": "building-materials", "label": "Building Materials", "code": "BLD", "brands": ["BuildRight", "IronClad", "Mastercraft"], "types": [
        T("Lumber Stud", 6, "Kiln-dried SPF framing stud, straight and ready for walls and framing.", ["lumber", "stud", "2x4", "framing"], "SIZE_IN", [], ["heavy-item"]),
        T("Plywood Sheet", 49, "Sanded plywood sheet for sheathing, subfloor and projects.", ["plywood", "sheet", "sheathing"], "GRADE", [], ["heavy-item"]),
        T("Drywall Sheet", 16, "Lightweight drywall panel for walls and ceilings.", ["drywall", "gyprock", "wallboard"], "GRADE", [], ["heavy-item"]),
        T("Concrete Mix", 9, "High-strength concrete mix for footings, posts and repairs.", ["concrete", "cement", "mix"], "CAP", ["outdoor"], ["heavy-item"]),
        T("Insulation Roll", 44, "Fibreglass batt insulation improves comfort and energy efficiency.", ["insulation", "batt", "fibreglass"], "GRADE", [], ["heavy-item"]),
        T("Landscape Blocks", 4, "Interlocking landscape blocks for garden walls and borders.", ["landscape blocks", "retaining", "pavers"], "GRADE", ["outdoor"], ["heavy-item"]),
        T("Roofing Shingles", 39, "Architectural asphalt shingles with wind and weather resistance.", ["shingles", "roofing", "asphalt"], "GRADE", ["outdoor"], ["heavy-item"]),
        T("Construction Adhesive", 7, "Heavy-duty construction adhesive bonds wood, concrete and panel.", ["construction adhesive", "glue", "liquid nails"], "GRADE", [], ["flammable"]),
        T("Sandpaper Assortment", 11, "Aluminum-oxide sandpaper sheets in assorted grits for sanding and finishing.", ["sandpaper", "abrasive", "sanding"], "GRIT", [], []),
        T("Tarp", 14, "Reinforced poly tarp with rust-proof grommets for cover and protection.", ["tarp", "cover", "poly"], "SIZE_S", ["outdoor"], []),
    ]},
    {"slug": "storage", "label": "Storage & Organization", "code": "STG", "brands": ["BuildRight", "IronClad", "EverBrite"], "types": [
        T("Storage Tote", 14, "Stackable storage tote with secure-latch lid for garage and home.", ["storage bin", "tote", "container"], "CAP", [], []),
        T("Shelving Unit", 79, "Boltless steel shelving unit holds heavy garage and basement loads.", ["shelving", "shelf", "rack"], "SIZE_S", [], ["requires-assembly", "heavy-item"]),
        T("Tool Chest", 199, "Rolling tool chest and cabinet combo with ball-bearing drawers.", ["tool chest", "tool box", "cabinet"], "SIZE_S", ["professional"], ["heavy-item"]),
        T("Pegboard Kit", 24, "Pegboard with assorted hooks to organize tools on the wall.", ["pegboard", "tool organizer", "wall storage"], "PACK", [], []),
        T("Garage Hooks", 12, "Heavy-duty garage hooks for bikes, ladders and hoses.", ["garage hooks", "storage hooks"], "PACK", [], []),
        T("Closet Organizer", 49, "Adjustable closet organizer with shelves and hanging rods.", ["closet organizer", "wardrobe", "shelving"], "SIZE_S", [], ["requires-assembly"]),
        T("Plastic Drawers", 34, "Rolling plastic drawer cart for crafts, parts and supplies.", ["drawers", "organizer cart", "bins"], "SIZE_S", [], []),
        T("Hardware Organizer", 16, "Compartment organizer with removable bins for screws and small parts.", ["hardware organizer", "parts box", "compartments"], "SIZE_S", [], []),
        T("Wall Cabinet", 69, "Lockable steel wall cabinet for garage and workshop storage.", ["wall cabinet", "storage cabinet"], "SIZE_S", [], ["requires-assembly", "heavy-item"]),
        T("Bin Rack", 39, "Louvred bin rack with assorted parts bins for organized small storage.", ["bin rack", "parts bins", "louvre"], "SIZE_S", [], []),
    ]},
    {"slug": "safety", "label": "Safety & Workwear", "code": "SFT", "brands": ["IronClad", "BuildRight", "VoltEdge"], "types": [
        T("Safety Glasses", 8, "Anti-fog, scratch-resistant safety glasses meet impact standards.", ["safety glasses", "eye protection", "goggles"], "PACK", [], []),
        T("Work Gloves", 12, "Cut-resistant work gloves with grippy coated palms.", ["work gloves", "gloves", "cut resistant"], "PACK", [], []),
        T("Hearing Protection", 14, "Noise-reducing earmuffs for power tools and the workshop.", ["hearing protection", "earmuffs", "ear plugs"], "GRADE", [], []),
        T("Dust Masks", 11, "Disposable respirator dust masks filter fine particulates.", ["dust mask", "respirator", "n95"], "PACK", [], []),
        T("Hard Hat", 19, "Adjustable hard hat with suspension for job-site head protection.", ["hard hat", "helmet", "head protection"], "COLOUR", [], []),
        T("Knee Pads", 22, "Gel knee pads cushion and protect for flooring and ground work.", ["knee pads", "protection"], "GRADE", [], []),
        T("First Aid Kit", 29, "Comprehensive first aid kit for home, job site and vehicle.", ["first aid", "kit", "medical"], "SIZE_S", [], []),
        T("High-Vis Vest", 14, "ANSI high-visibility safety vest with reflective striping.", ["hi vis", "safety vest", "reflective"], "SIZE_S", [], []),
        T("Work Boots", 89, "Steel-toe work boots with slip-resistant soles and ankle support.", ["work boots", "steel toe", "safety boots"], "SIZE_S", [], []),
        T("Fire Extinguisher", 39, "Multi-purpose ABC fire extinguisher for home and garage.", ["fire extinguisher", "abc", "safety"], "GRADE", [], ["heavy-item"]),
    ]},
    {"slug": "heating-cooling", "label": "Heating & Cooling", "code": "HVC", "brands": ["TundraGuard", "EverBrite", "BuildRight"], "types": [
        T("Space Heater", 49, "Ceramic space heater with adjustable thermostat and tip-over protection.", ["space heater", "ceramic heater", "portable heat"], "WATT", [], []),
        T("Box Fan", 29, "Three-speed box fan moves air for whole-room cooling.", ["box fan", "fan", "cooling"], "SIZE_S", [], []),
        T("Tower Fan", 59, "Oscillating tower fan with remote and timer for quiet cooling.", ["tower fan", "oscillating", "remote"], "WATT", [], []),
        T("Dehumidifier", 199, "Energy-efficient dehumidifier removes excess moisture from basements.", ["dehumidifier", "moisture", "basement"], "CAP", [], ["heavy-item"]),
        T("Humidifier", 44, "Cool-mist humidifier improves air comfort in dry rooms.", ["humidifier", "cool mist", "air"], "CAP", [], []),
        T("Furnace Filter", 14, "Pleated furnace filter captures dust, pollen and allergens.", ["furnace filter", "hvac filter", "air filter"], "PACK", [], []),
        T("Programmable Thermostat", 69, "Smart programmable thermostat saves energy with schedules and app control.", ["thermostat", "smart", "programmable"], "GRADE", [], []),
        T("Garage Heater", 159, "Forced-air garage heater warms workshops quickly and safely.", ["garage heater", "forced air", "workshop heat"], "WATT", [], ["heavy-item"]),
        T("Air Conditioner", 299, "Portable air conditioner cools rooms with easy window venting.", ["air conditioner", "portable ac", "cooling"], "GRADE", [], ["heavy-item"]),
        T("Ceiling Fan", 89, "Reversible ceiling fan with integrated LED light and remote.", ["ceiling fan", "fan", "remote"], "COLOUR", [], ["requires-assembly"]),
    ]},
    {"slug": "flooring", "label": "Flooring & Tile", "code": "FLR", "brands": ["BuildRight", "EverBrite", "Mastercraft"], "types": [
        T("Laminate Flooring", 39, "Scratch-resistant laminate planks with realistic wood look and click-lock install.", ["laminate", "flooring", "planks"], "GRADE", [], ["heavy-item"]),
        T("Vinyl Plank", 44, "Waterproof luxury vinyl plank for kitchens, baths and basements.", ["vinyl plank", "lvp", "waterproof flooring"], "GRADE", [], ["heavy-item"]),
        T("Ceramic Tile", 19, "Durable glazed ceramic tile for floors and walls.", ["ceramic tile", "tile", "floor"], "PACK", [], ["heavy-item"]),
        T("Tile Adhesive", 16, "Premium thinset tile adhesive for strong, lasting tile bonds.", ["tile adhesive", "thinset", "mortar"], "CAP", [], ["heavy-item"]),
        T("Grout", 12, "Stain-resistant sanded grout fills tile joints for a clean finish.", ["grout", "tile grout", "joints"], "CAP", [], []),
        T("Underlayment", 24, "Acoustic foam underlayment cushions and quiets laminate and vinyl floors.", ["underlayment", "foam", "subfloor"], "GRADE", [], []),
        T("Area Rug", 59, "Stain-resistant area rug adds warmth and style to any room.", ["area rug", "rug", "carpet"], "SIZE_S", [], []),
        T("Floor Trim", 9, "Quarter-round and baseboard trim for a finished floor edge.", ["floor trim", "baseboard", "quarter round"], "GRADE", [], []),
        T("Tile Cutter", 49, "Manual tile cutter scores and snaps ceramic tile cleanly.", ["tile cutter", "tile saw", "scoring"], "SIZE_S", ["professional"], ["sharp-blade"]),
        T("Floor Mat", 19, "Anti-fatigue floor mat cushions standing work at the bench.", ["floor mat", "anti fatigue", "garage"], "SIZE_S", [], []),
    ]},
    {"slug": "seasonal", "label": "Seasonal", "code": "SSN", "brands": ["TundraGuard", "GreenThumb", "Mastercraft"], "types": [
        T("Snow Shovel", 24, "Ergonomic snow shovel with bent shaft reduces back strain.", ["snow shovel", "shovel", "winter"], "SIZE_S", ["outdoor"], []),
        T("Snow Brush", 14, "Extendable snow brush with ice scraper for clearing vehicles.", ["snow brush", "ice scraper", "winter"], "SIZE_S", ["outdoor"], []),
        T("Ice Melt", 12, "Fast-acting ice melt keeps walkways and driveways safe in winter.", ["ice melt", "salt", "de-icer"], "CAP", ["outdoor"], ["heavy-item"]),
        T("Snow Blower", 599, "Two-stage snow blower clears heavy snow with powerful auger and chute control.", ["snow blower", "snow thrower", "winter"], "VOLT", ["cordless", "outdoor"], ["contains-battery", "heavy-item"]),
        T("Patio Set", 399, "Weather-resistant patio dining set for outdoor entertaining.", ["patio set", "patio furniture", "outdoor"], "SIZE_S", ["outdoor"], ["requires-assembly", "heavy-item"]),
        T("BBQ Grill", 299, "Stainless propane BBQ grill with multiple burners and side shelves.", ["bbq", "grill", "propane", "barbecue"], "SIZE_S", ["outdoor"], ["requires-assembly", "flammable", "heavy-item"]),
        T("Christmas Lights", 19, "Weatherproof LED Christmas lights for indoor and outdoor decorating.", ["christmas lights", "holiday", "led"], "LEN_FT", ["outdoor"], []),
        T("Cooler", 49, "Insulated hard cooler keeps food and drinks cold for days.", ["cooler", "ice chest", "camping"], "CAP", ["outdoor"], []),
        T("Pool Chemicals", 24, "Pool maintenance chemical kit keeps water clean and balanced.", ["pool chemicals", "chlorine", "pool"], "CAP", ["outdoor"], ["flammable"]),
        T("Patio Umbrella", 79, "Tilting patio umbrella with UV-resistant canopy for shade.", ["patio umbrella", "shade", "outdoor"], "SIZE_S", ["outdoor"], []),
    ]},
    {"slug": "sporting", "label": "Sporting & Recreation", "code": "SPT", "brands": ["TundraGuard", "Mastercraft", "GreenThumb"], "types": [
        T("Camping Tent", 119, "Weatherproof dome tent with quick-pitch poles for family camping.", ["tent", "camping", "dome"], "SIZE_S", ["outdoor"], []),
        T("Sleeping Bag", 49, "Insulated mummy sleeping bag rated for three-season comfort.", ["sleeping bag", "camping", "mummy"], "GRADE", ["outdoor"], []),
        T("Camp Stove", 59, "Portable propane camp stove with wind guards for outdoor cooking.", ["camp stove", "propane stove", "camping"], "GRADE", ["outdoor"], ["flammable"]),
        T("Folding Chair", 24, "Compact folding camp chair with cup holder and carry bag.", ["folding chair", "camp chair", "outdoor"], "GRADE", ["outdoor"], []),
        T("Bike Pump", 19, "Floor bike pump with gauge inflates tires fast to exact pressure.", ["bike pump", "pump", "tire"], "GRADE", [], []),
        T("Fishing Rod Combo", 44, "Spinning rod and reel combo ready for lake and river fishing.", ["fishing rod", "reel", "combo"], "GRADE", ["outdoor"], []),
        T("Cooler Backpack", 39, "Insulated backpack cooler keeps drinks cold on the trail.", ["cooler backpack", "soft cooler", "camping"], "SIZE_S", ["outdoor"], []),
        T("Hiking Poles", 34, "Adjustable aluminum hiking poles with shock absorption.", ["hiking poles", "trekking", "poles"], "PACK", ["outdoor"], []),
        T("Life Jacket", 39, "Approved life jacket with adjustable straps for boating and paddling.", ["life jacket", "pfd", "boating"], "SIZE_S", ["outdoor"], []),
        T("Tarp Shelter", 29, "Lightweight tarp shelter with poles and stakes for camp shade.", ["tarp shelter", "canopy", "camping"], "SIZE_S", ["outdoor"], ["requires-assembly"]),
    ]},
]


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:90]


def _round_price(value: float, rng: random.Random) -> float:
    # Nudge to a .99 / .98 / .49 retail ending.
    ending = rng.choice([0.99, 0.99, 0.99, 0.98, 0.49, 0.95])
    whole = max(1, int(value))
    return round(whole - 1 + ending, 2) if value >= 2 else round(value, 2)


def generate_products(seed: int = 1337, target: int | None = None) -> list[dict]:
    """Generate the catalog.

    target=None  → the curated ~1.2k catalog (3 variants × 2 brands).
    target=N     → scale up (all variants × up to 3 brands × edition series),
                   deterministically truncated to N SKUs. Reaches 10k+.
    """
    from app.seed.image_provider import image_url_for

    rng = random.Random(seed)
    scaled = target is not None
    products: list[dict] = []
    used_slugs: set[str] = set()
    used_skus: set[str] = set()

    for cat in CATEGORIES:
        counter = 10000 + rng.randint(0, 500)
        for ptype in cat["types"]:
            axis_vals = AXES[ptype["axis"]]
            if scaled:
                variants = axis_vals                       # all axis values (up to 5)
                brands = cat["brands"][:3]
                series_list = SERIES                        # 4 editions
            else:
                variants = axis_vals[:3] if len(axis_vals) >= 3 else axis_vals
                brands = cat["brands"][:2]
                series_list = [("", 1.0)]
            for brand in brands:
                for vlabel, vmult in variants:
                    for slabel, smult in series_list:
                        counter += rng.randint(7, 23)
                        sku = f"BR-{cat['code']}-{counter:05d}"
                        if sku in used_skus:
                            continue
                        used_skus.add(sku)

                        vl = f"{vlabel} " if vlabel else ""
                        sfx = f" {slabel}" if slabel else ""
                        name = f"{brand} {vl}{ptype['name']}{sfx}".replace("  ", " ").strip()
                        slug = _slugify(name)
                        base_slug = slug
                        n = 2
                        while slug in used_slugs:
                            slug = f"{base_slug}-{n}"
                            n += 1
                        used_slugs.add(slug)

                        price = _round_price(
                            ptype["base"] * vmult * smult * rng.uniform(0.95, 1.12), rng
                        )

                        desc = ptype["spec"]
                        if vlabel:
                            desc = f"{vlabel} model. {desc}"
                        if slabel:
                            desc = f"{slabel} edition. {desc}"
                        desc = f"{desc} {brand} quality, backed by the BuildRight AI warranty."

                        kw = list(ptype["kw"]) + [brand.lower(), cat["slug"]]
                        if vlabel:
                            kw.append(vlabel.lower().replace('"', "").replace(" ", ""))

                        # stock distribution: ~8% out, ~17% low, rest healthy
                        roll = rng.random()
                        if roll < 0.08:
                            stock, available = 0, False
                        elif roll < 0.25:
                            stock, available = rng.randint(1, 15), True
                        else:
                            stock, available = rng.randint(16, 480), True

                        tags = list(ptype["tags"])
                        if "Pro" in vlabel or "Heavy-Duty" in vlabel or "Pro" in slabel:
                            tags.append("professional")
                        if rng.random() < 0.14:
                            tags.append("sale")
                        if rng.random() < 0.10:
                            tags.append("new-arrival")

                        # Modelled cost of goods (55-70% of price) for margin dashboards.
                        cost = round(price * rng.uniform(0.55, 0.70), 2)
                        products.append({
                            "id": slug,
                            "sku": sku,
                            "name": name,
                            "category": cat["slug"],
                            "description": desc,
                            "price": price,
                            "cost": cost,
                            "stock": stock,
                            "is_available": available,
                            "keywords": sorted(set(kw)),
                            "dietary_tags": sorted(set(tags)),
                            "allergens": sorted(set(ptype["flags"])),
                            "featured": rng.random() < 0.03,
                            "image_url": image_url_for(cat["slug"], ptype["name"], slug),
                        })

    if target is not None and len(products) > target:
        # Round-robin across categories so a smaller target still covers EVERY
        # category. A flat products[:target] builds in category order and drops
        # whole trailing categories (e.g. target=3000 kept only 6 of 19).
        from collections import OrderedDict

        by_cat: "OrderedDict[str, list[dict]]" = OrderedDict()
        for p in products:
            by_cat.setdefault(p["category"], []).append(p)

        selected: list[dict] = []
        idx = 0
        cols = list(by_cat.values())
        while len(selected) < target and any(idx < len(col) for col in cols):
            for col in cols:
                if idx < len(col):
                    selected.append(col[idx])
                    if len(selected) >= target:
                        break
            idx += 1
        products = selected
    return products


# Category labels for the seed (merged into CATEGORY_LABELS)
CATEGORY_LABELS = {c["slug"]: c["label"] for c in CATEGORIES}


if __name__ == "__main__":
    items = generate_products()
    from collections import Counter
    by_cat = Counter(p["category"] for p in items)
    print(f"Generated {len(items)} products across {len(by_cat)} categories")
    for slug, n in sorted(by_cat.items()):
        print(f"  {slug:22} {n}")
    print("Sample:", items[0]["sku"], "-", items[0]["name"], "-", f"${items[0]['price']}")
