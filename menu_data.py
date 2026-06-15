"""Product catalog for the Smart Handy Man store.

This file is the single source of truth for the catalog; the backend seed
(backend/app/seed/seed.py) loads it into the database.

Per-item schema (same structure as original — seed.py ingests unchanged):
  id, name, category, description, price (float CAD), dietary_tags, keywords
  + optional: allergens, calories, spice_level, featured, image_url, options

Controlled vocabularies (repurposed for retail):
  dietary_tags  : cordless, corded, battery-powered, outdoor, indoor,
                  professional, sale, new-arrival
  allergens     : requires-assembly, flammable, contains-battery,
                  heavy-item, sharp-blade, power-tool
  categories    : power-tools, hand-tools, hardware, automotive,
                  kitchen, outdoor, cleaning, paint, electrical,
                  plumbing, seasonal

NOTE: The original cafe data (the frozen lexical-retrieval regression baseline
      used by backend/tests/golden/) is preserved in menu_data_legacy_cafe.py.
      This file is the live retail catalog.
"""

MENU_DATA = [
    # ============================================================
    # Power Tools
    # ============================================================
    {
        "id": "mastercraft-drill",
        "name": "Mastercraft 20V Cordless Drill/Driver",
        "category": "power-tools",
        "description": "20-volt MAX lithium-ion drill/driver with keyless chuck, 2-speed gearbox, and LED work light. Includes 1.5Ah battery and charger.",
        "price": 49.99,
        "dietary_tags": ["cordless", "battery-powered"],
        "keywords": ["drill", "cordless", "mastercraft", "driver", "20v"],
        "allergens": ["contains-battery", "power-tool"],
        "featured": True,
        "options": [
            {"name": "Bundle", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "Bare Tool", "price_delta": 0, "is_default": True},
                {"name": "Kit (battery + charger)", "price_delta": 20.00},
            ]},
        ],
    },
    {
        "id": "circular-saw",
        "name": "7-1/4\" Corded Circular Saw",
        "category": "power-tools",
        "description": "15-amp motor with 5,500 RPM for fast, accurate cuts in lumber and plywood. Bevel capacity 0–56°.",
        "price": 79.99,
        "dietary_tags": ["corded", "professional"],
        "keywords": ["saw", "circular saw", "cutting", "lumber", "corded"],
        "allergens": ["sharp-blade", "power-tool"],
        "featured": True,
    },
    {
        "id": "orbital-sander",
        "name": "5\" Random Orbit Sander",
        "category": "power-tools",
        "description": "2.5-amp random orbit sander with dust bag, variable speed dial, and hook-and-loop pad.",
        "price": 39.99,
        "dietary_tags": ["corded"],
        "keywords": ["sander", "orbital", "finishing", "wood", "corded"],
        "allergens": ["power-tool"],
    },
    {
        "id": "cordless-jigsaw",
        "name": "20V Cordless Jigsaw",
        "category": "power-tools",
        "description": "Orbital-action jigsaw for curves and straight cuts. Blade clamp accepts T-shank blades. Tool-free shoe bevel 0–45°.",
        "price": 69.99,
        "dietary_tags": ["cordless", "battery-powered"],
        "keywords": ["jigsaw", "cordless", "cutting", "curved", "20v"],
        "allergens": ["contains-battery", "sharp-blade", "power-tool"],
    },
    {
        "id": "impact-driver",
        "name": "20V Cordless Impact Driver",
        "category": "power-tools",
        "description": "1,825 in-lbs of torque for driving long fasteners and lag screws. Compact head fits tight spaces.",
        "price": 59.99,
        "dietary_tags": ["cordless", "battery-powered", "professional"],
        "keywords": ["impact driver", "cordless", "fastener", "torque", "20v"],
        "allergens": ["contains-battery", "power-tool"],
    },

    # ============================================================
    # Hand Tools
    # ============================================================
    {
        "id": "claw-hammer",
        "name": "20 oz Steel Claw Hammer",
        "category": "hand-tools",
        "description": "Solid steel construction with a smooth face for nailing and a curved claw for pulling. Cushion-grip handle reduces vibration.",
        "price": 18.99,
        "dietary_tags": [],
        "keywords": ["hammer", "claw hammer", "nailing", "framing"],
        "allergens": [],
        "featured": True,
    },
    {
        "id": "pliers-set",
        "name": "3-Piece Pliers Set",
        "category": "hand-tools",
        "description": "Includes 8\" slip-joint, 6\" needle-nose, and 7\" diagonal-cutting pliers. Chrome-vanadium steel.",
        "price": 24.99,
        "dietary_tags": [],
        "keywords": ["pliers", "needle nose", "diagonal", "gripping"],
        "allergens": [],
    },
    {
        "id": "screwdriver-set",
        "name": "10-Piece Screwdriver Set",
        "category": "hand-tools",
        "description": "Magnetic tips for Phillips and flathead screws. Ergonomic tri-lobe handles. Sizes #1–#3 Phillips and 3/16\"–5/16\" slotted.",
        "price": 22.99,
        "dietary_tags": [],
        "keywords": ["screwdriver", "phillips", "flathead", "magnetic"],
        "allergens": [],
    },
    {
        "id": "tape-measure",
        "name": "25 ft Tape Measure",
        "category": "hand-tools",
        "description": "Nylon-coated 1\" wide blade with double-sided markings. Auto-lock and rubber overmould case.",
        "price": 12.99,
        "dietary_tags": [],
        "keywords": ["tape measure", "measuring", "ruler", "25ft"],
        "allergens": [],
    },

    # ============================================================
    # Hardware / Fasteners
    # ============================================================
    {
        "id": "wood-screws-assortment",
        "name": "200-Piece Wood Screw Assortment",
        "category": "hardware",
        "description": "Coarse-thread zinc-plated screws in eight sizes from #6 × 3/4\" to #10 × 2\". Reusable storage case.",
        "price": 14.99,
        "dietary_tags": [],
        "keywords": ["screws", "wood screws", "fastener", "zinc"],
        "allergens": [],
    },
    {
        "id": "picture-hanging-kit",
        "name": "50-Piece Picture Hanging Kit",
        "category": "hardware",
        "description": "Assortment of picture hooks, D-rings, wire, and wall anchors for frames up to 50 lbs.",
        "price": 12.99,
        "dietary_tags": [],
        "keywords": ["picture hanging", "wall hooks", "anchors", "frames"],
        "allergens": [],
    },
    {
        "id": "shelf-brackets",
        "name": "Heavy-Duty Shelf Brackets 2-Pack",
        "category": "hardware",
        "description": "Powder-coated steel L-brackets, 10\" × 8\", rated to 200 lbs per pair. Mounting hardware included.",
        "price": 16.99,
        "dietary_tags": [],
        "keywords": ["shelf brackets", "shelving", "wall mount", "brackets"],
        "allergens": ["heavy-item"],
    },

    # ============================================================
    # Automotive
    # ============================================================
    {
        "id": "motor-oil-5w30",
        "name": "5W-30 Full Synthetic Motor Oil 5L",
        "category": "automotive",
        "description": "API SP certified full synthetic oil for petrol engines. Extends engine life, improves fuel economy.",
        "price": 34.99,
        "dietary_tags": [],
        "keywords": ["motor oil", "synthetic oil", "engine oil", "5w30", "automotive"],
        "allergens": ["flammable"],
        "featured": True,
    },
    {
        "id": "jumper-cables",
        "name": "20 ft Heavy-Duty Jumper Cables",
        "category": "automotive",
        "description": "4-gauge copper-clad cables with fully insulated clamps. 20 ft reach for easy car-to-car jump starts.",
        "price": 29.99,
        "dietary_tags": [],
        "keywords": ["jumper cables", "booster cables", "battery", "automotive"],
        "allergens": [],
    },
    {
        "id": "tire-inflator",
        "name": "Digital Tire Inflator",
        "category": "automotive",
        "description": "Compact 12V inflator with digital pressure gauge, auto shutoff, and LED light. 150 PSI max.",
        "price": 39.99,
        "dietary_tags": [],
        "keywords": ["tire inflator", "air compressor", "tires", "pressure", "automotive"],
        "allergens": [],
    },
    {
        "id": "car-wax",
        "name": "Premium Spray Car Wax 500ml",
        "category": "automotive",
        "description": "Quick-detail spray wax with UV protection. Safe for all paint types. Buff-free application.",
        "price": 16.99,
        "dietary_tags": [],
        "keywords": ["car wax", "polish", "detailing", "protective", "automotive"],
        "allergens": ["flammable"],
    },

    # ============================================================
    # Kitchen Appliances
    # ============================================================
    {
        "id": "2-slice-toaster",
        "name": "2-Slice Toaster",
        "category": "kitchen",
        "description": "6 browning settings, extra-wide slots for bagels and thick bread. Removable crumb tray.",
        "price": 29.99,
        "dietary_tags": ["indoor"],
        "keywords": ["toaster", "bread", "bagel", "breakfast", "kitchen"],
        "allergens": [],
    },
    {
        "id": "drip-coffee-maker",
        "name": "12-Cup Drip Coffee Maker",
        "category": "kitchen",
        "description": "Programmable 24-hr timer, brew strength selector (regular/bold), and keep-warm plate. BPA-free carafe.",
        "price": 49.99,
        "dietary_tags": ["indoor"],
        "keywords": ["coffee maker", "drip coffee", "brewer", "programmable", "kitchen"],
        "allergens": [],
        "featured": True,
    },
    {
        "id": "hand-blender",
        "name": "Immersion Hand Blender",
        "category": "kitchen",
        "description": "400-watt stick blender for soups, smoothies, and sauces. Detachable shaft for easy cleaning.",
        "price": 34.99,
        "dietary_tags": ["indoor"],
        "keywords": ["blender", "hand blender", "immersion", "stick blender", "kitchen"],
        "allergens": [],
    },
    {
        "id": "air-fryer",
        "name": "4L Digital Air Fryer",
        "category": "kitchen",
        "description": "Digital touchscreen, 8 presets, 360° rapid-air circulation. Dishwasher-safe basket. Up to 220°C.",
        "price": 79.99,
        "dietary_tags": ["indoor"],
        "keywords": ["air fryer", "fryer", "oven", "cooking", "healthy", "kitchen"],
        "allergens": [],
        "featured": True,
    },

    # ============================================================
    # Outdoor / Garden
    # ============================================================
    {
        "id": "garden-hose",
        "name": "50 ft Expandable Garden Hose",
        "category": "outdoor",
        "description": "Latex-core hose expands from 17 ft to 50 ft under pressure. 8-pattern spray nozzle included.",
        "price": 34.99,
        "dietary_tags": ["outdoor"],
        "keywords": ["garden hose", "hose", "watering", "expandable", "outdoor"],
        "allergens": [],
    },
    {
        "id": "pruning-shears",
        "name": "Heavy-Duty Bypass Pruning Shears",
        "category": "outdoor",
        "description": "SK-5 steel blades cut branches up to 3/4\" diameter. Sap groove, safety lock, and non-slip handles.",
        "price": 19.99,
        "dietary_tags": ["outdoor"],
        "keywords": ["pruning shears", "secateurs", "garden", "cutting", "branches"],
        "allergens": ["sharp-blade"],
    },
    {
        "id": "patio-chair",
        "name": "Foldable Steel Patio Chair",
        "category": "outdoor",
        "description": "Powder-coated tubular steel frame with weather-resistant mesh seat and back. Folds flat for storage.",
        "price": 49.99,
        "dietary_tags": ["outdoor"],
        "keywords": ["patio chair", "outdoor chair", "folding", "garden furniture"],
        "allergens": [],
    },
    {
        "id": "bbq-propane-regulator",
        "name": "Universal BBQ Propane Regulator",
        "category": "outdoor",
        "description": "High-pressure regulator with 5 ft hose for propane BBQ grills. 10,000–40,000 BTU range.",
        "price": 29.99,
        "dietary_tags": ["outdoor"],
        "keywords": ["bbq", "propane", "regulator", "grill", "gas"],
        "allergens": ["flammable"],
    },

    # ============================================================
    # Cleaning
    # ============================================================
    {
        "id": "all-purpose-cleaner",
        "name": "All-Purpose Cleaner 1L (6-Pack)",
        "category": "cleaning",
        "description": "Ready-to-use spray degreaser for kitchens, bathrooms, and appliances. Biodegradable formula.",
        "price": 19.99,
        "dietary_tags": ["indoor"],
        "keywords": ["cleaner", "all purpose", "spray", "degreaser", "cleaning"],
        "allergens": ["flammable"],
    },
    {
        "id": "microfiber-cloths",
        "name": "Microfiber Cloths 12-Pack",
        "category": "cleaning",
        "description": "Ultra-soft, lint-free 300 GSM cloths. Machine washable. For glass, stainless steel, and surfaces.",
        "price": 14.99,
        "dietary_tags": [],
        "keywords": ["microfiber", "cleaning cloths", "rags", "polishing"],
        "allergens": [],
    },
    {
        "id": "vacuum-bags",
        "name": "Universal Vacuum Dust Bags 8-Pack",
        "category": "cleaning",
        "description": "Compatible with most upright and canister vacuums. HEPA-grade filtration. 4-layer dust lock.",
        "price": 9.99,
        "dietary_tags": [],
        "keywords": ["vacuum bags", "dust bags", "vacuum", "filter", "cleaning"],
        "allergens": [],
    },

    # ============================================================
    # Paint
    # ============================================================
    {
        "id": "interior-latex-paint",
        "name": "Interior Latex Paint 1 Gallon",
        "category": "paint",
        "description": "Low-VOC, washable interior paint with built-in primer. One-coat coverage on properly prepared surfaces.",
        "price": 39.99,
        "dietary_tags": [],
        "keywords": ["paint", "interior paint", "latex", "wall paint", "primer"],
        "allergens": ["flammable"],
        "options": [
            {"name": "Finish", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "Flat", "price_delta": 0, "is_default": True},
                {"name": "Eggshell", "price_delta": 0},
                {"name": "Semi-Gloss", "price_delta": 5.00},
            ]},
        ],
    },
    {
        "id": "multi-surface-primer",
        "name": "Multi-Surface Primer 1 Gallon",
        "category": "paint",
        "description": "Stain-blocking primer seals bare wood, drywall, and masonry. Reduces top-coat usage.",
        "price": 29.99,
        "dietary_tags": [],
        "keywords": ["primer", "paint primer", "stain block", "sealer"],
        "allergens": ["flammable"],
    },
    {
        "id": "paint-roller-set",
        "name": "9\" Paint Roller and Tray Set",
        "category": "paint",
        "description": "Includes 9\" frame, 3/8\" nap roller cover, and deep plastic tray. Suitable for smooth to medium surfaces.",
        "price": 12.99,
        "dietary_tags": [],
        "keywords": ["paint roller", "roller", "tray", "painting tools", "roller set"],
        "allergens": [],
    },

    # ============================================================
    # Electrical
    # ============================================================
    {
        "id": "extension-cord",
        "name": "25 ft Heavy-Duty Extension Cord",
        "category": "electrical",
        "description": "14-AWG, 15-amp grounded cord with lighted end. Jacket rated for indoor and outdoor use.",
        "price": 24.99,
        "dietary_tags": ["outdoor", "indoor"],
        "keywords": ["extension cord", "power cord", "heavy duty", "outdoor"],
        "allergens": [],
        "options": [
            {"name": "Length", "min_select": 1, "max_select": 1, "required": True, "choices": [
                {"name": "25 ft", "price_delta": 0, "is_default": True},
                {"name": "50 ft", "price_delta": 15.00},
            ]},
        ],
    },
    {
        "id": "led-bulb-pack",
        "name": "LED A19 Bulbs 60W Equiv 8-Pack",
        "category": "electrical",
        "description": "800-lumen, 2700K soft white LED bulbs. 10-year rated life (3 hrs/day). E26 medium base.",
        "price": 19.99,
        "dietary_tags": ["indoor", "sale"],
        "keywords": ["led bulbs", "light bulbs", "bulbs", "energy saving", "lighting"],
        "allergens": [],
        "featured": True,
    },
    {
        "id": "power-bar",
        "name": "6-Outlet Power Bar with Surge Protection",
        "category": "electrical",
        "description": "1875-joule surge protector with 6 outlets and two 2.4A USB charging ports. 6 ft power cord.",
        "price": 22.99,
        "dietary_tags": ["indoor"],
        "keywords": ["power bar", "surge protector", "power strip", "usb", "outlets"],
        "allergens": [],
    },

    # ============================================================
    # Plumbing
    # ============================================================
    {
        "id": "pipe-wrench",
        "name": "14\" Heavy-Duty Pipe Wrench",
        "category": "plumbing",
        "description": "Ductile iron body with hardened-steel jaw. Self-adjusting heel jaw for pipes 3/4\" to 2\". Drop-forged.",
        "price": 27.99,
        "dietary_tags": ["professional"],
        "keywords": ["pipe wrench", "wrench", "plumbing", "pipes", "plumber"],
        "allergens": ["heavy-item"],
    },
    {
        "id": "plumbers-tape",
        "name": "PTFE Plumber's Tape 3-Pack",
        "category": "plumbing",
        "description": "1/2\" × 520\" per roll thread-seal tape for pipe fittings. Resists most chemicals and temperatures.",
        "price": 7.99,
        "dietary_tags": [],
        "keywords": ["plumbers tape", "ptfe", "thread tape", "teflon tape", "sealing"],
        "allergens": [],
    },

    # ============================================================
    # Seasonal
    # ============================================================
    {
        "id": "snow-brush-scraper",
        "name": "48\" Snow Brush with Ice Scraper",
        "category": "seasonal",
        "description": "Foam-padded brush head won't scratch paint. Flip side ice scraper with brass blade. Telescoping handle.",
        "price": 16.99,
        "dietary_tags": ["outdoor", "sale"],
        "keywords": ["snow brush", "ice scraper", "winter", "car", "snow"],
        "allergens": [],
    },
    {
        "id": "outdoor-door-mat",
        "name": "Heavy-Duty Outdoor Door Mat 18\"×30\"",
        "category": "seasonal",
        "description": "Coir-and-rubber mat with anti-slip backing. Scrapes mud, dirt, and snow. UV-stable.",
        "price": 24.99,
        "dietary_tags": ["outdoor"],
        "keywords": ["door mat", "mat", "entrance", "outdoor", "coir"],
        "allergens": [],
    },
]
